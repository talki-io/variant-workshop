"""模型管理（admin）：模型库 CRUD（多厂商）+ 管线场景绑定。保存后即刷新进程缓存，下次调用生效。"""

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..llm import PROVIDERS, ModelSpec, refresh_model_config, verify_model
from ..models import LlmModel, ModelConfig, User
from ..schemas import (
    LlmModelCreateIn,
    LlmModelOut,
    LlmModelUpdateIn,
    ModelConfigOut,
    ModelConfigUpdateIn,
    ModelVerifyOut,
)
from ..security import require_admin

router = APIRouter(prefix="/api", tags=["models"], dependencies=[Depends(require_admin)])


def _out(m: LlmModel) -> LlmModelOut:
    """出参脱敏：不回显 api_key，只给 has_key 标志。"""
    return LlmModelOut(
        id=m.id, name=m.name, provider=m.provider, model_id=m.model_id,
        base_url=m.base_url, has_key=bool(m.api_key), enabled=m.enabled, created_at=m.created_at,
    )


# ===== 模型库 =====
@router.get("/llm-models", response_model=list[LlmModelOut])
def list_llm_models(db: Session = Depends(get_db)) -> list[LlmModelOut]:
    return [_out(m) for m in db.scalars(select(LlmModel).order_by(LlmModel.created_at, LlmModel.id))]


@router.post("/llm-models", response_model=LlmModelOut, status_code=status.HTTP_201_CREATED)
def create_llm_model(body: LlmModelCreateIn, db: Session = Depends(get_db)) -> LlmModelOut:
    if body.provider not in PROVIDERS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"provider 需为 {PROVIDERS}")
    if not body.name.strip() or not body.model_id.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="名称与 model_id 不能为空")
    if body.provider == "openai" and not (body.base_url or "").strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="OpenAI 兼容模型需填 base_url")
    m = LlmModel(
        id="mdl_" + uuid4().hex[:8], name=body.name.strip(), provider=body.provider,
        model_id=body.model_id.strip(), base_url=(body.base_url or None),
        api_key=(body.api_key or None), enabled=True,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return _out(m)


@router.put("/llm-models/{model_id}", response_model=LlmModelOut)
def update_llm_model(model_id: str, body: LlmModelUpdateIn, db: Session = Depends(get_db)) -> LlmModelOut:
    m = db.get(LlmModel, model_id)
    if m is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型不存在")
    if body.provider is not None:
        if body.provider not in PROVIDERS:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"provider 需为 {PROVIDERS}")
        m.provider = body.provider
    for field in ("name", "model_id", "base_url"):
        val = getattr(body, field)
        if val is not None:
            setattr(m, field, val.strip() or None if field == "base_url" else val.strip())
    if "api_key" in body.model_fields_set:  # 传则更新（空串=清空）
        m.api_key = (body.api_key or None)
    if body.enabled is not None:
        m.enabled = body.enabled
    db.commit()
    db.refresh(m)
    refresh_model_config(db)  # 库改动可能影响已绑定场景
    return _out(m)


@router.delete("/llm-models/{model_id}", response_model=ModelVerifyOut)
def delete_llm_model(model_id: str, db: Session = Depends(get_db)) -> ModelVerifyOut:
    m = db.get(LlmModel, model_id)
    if m is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型不存在")
    bound = db.scalars(select(ModelConfig.scene).where(ModelConfig.model_id == model_id)).all()
    if bound:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"该模型正被场景 {bound} 绑定，请先在场景里改绑其他模型再删除",
        )
    db.delete(m)
    db.commit()
    return ModelVerifyOut(ok=True)


@router.post("/llm-models/{model_id}/verify", response_model=ModelVerifyOut)
def verify_llm_model(model_id: str, db: Session = Depends(get_db)) -> ModelVerifyOut:
    """对某模型发极小请求做连通性自检（验证 provider/base_url/key/model_id 是否可用）。"""
    m = db.get(LlmModel, model_id)
    if m is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型不存在")
    spec = ModelSpec(m.provider, m.model_id, m.base_url, m.api_key, m.name)
    return ModelVerifyOut(**verify_model(spec))


# ===== 场景绑定 =====
@router.get("/models", response_model=list[ModelConfigOut])
def list_models(db: Session = Depends(get_db)) -> list[ModelConfig]:
    """各管线场景绑定的模型 + 参数（生成/清洗/合规）。"""
    return list(db.scalars(select(ModelConfig).order_by(ModelConfig.scene)))


@router.put("/models/{scene}", response_model=ModelConfigOut)
def update_model(scene: str, body: ModelConfigUpdateIn, db: Session = Depends(get_db)) -> ModelConfig:
    """更新某场景绑定的模型/参数（admin），保存后刷新进程缓存立即生效。"""
    cfg = db.get(ModelConfig, scene)
    if cfg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="场景不存在")
    if body.model_id is not None:
        if db.get(LlmModel, body.model_id) is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="所选模型不在模型库中")
        cfg.model_id = body.model_id
    if body.max_tokens is not None:
        if body.max_tokens < 1 or body.max_tokens > 64000:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="max_tokens 需在 1–64000")
        cfg.max_tokens = body.max_tokens
    if "temperature" in body.model_fields_set:
        if body.temperature is not None and not (0.0 <= body.temperature <= 1.0):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="temperature 需在 0–1")
        cfg.temperature = body.temperature
    if body.enabled is not None:
        cfg.enabled = body.enabled
    cfg.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.commit()
    db.refresh(cfg)
    refresh_model_config(db)
    return cfg
