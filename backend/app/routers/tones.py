from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import StyleSample, Tone, User
from ..schemas import (
    OkOut,
    StyleSampleIn,
    StyleSampleOut,
    ToneCreateIn,
    ToneOut,
    ToneUpdateIn,
)
from ..security import get_current_user, require_admin

router = APIRouter(prefix="/api", tags=["tones"])


@router.get("/tones", response_model=list[ToneOut])
def get_tones(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[Tone]:
    return list(db.scalars(select(Tone).order_by(Tone.id)))


# ===== 账号/调性管理（admin）=====
@router.post("/tones", response_model=ToneOut, status_code=status.HTTP_201_CREATED)
def create_tone(body: ToneCreateIn, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> Tone:
    """新增账号/调性（admin）。"""
    if not body.name.strip() or not body.handle.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="账号名与 handle 不能为空")
    t = Tone(id="t_" + uuid4().hex[:8], handle=body.handle.strip(),
             name=body.name.strip(), desc=body.desc.strip())
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.put("/tones/{tone_id}", response_model=ToneOut)
def update_tone(
    tone_id: str, body: ToneUpdateIn, db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> Tone:
    """部分更新账号/调性（admin）。"""
    t = db.get(Tone, tone_id)
    if t is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号不存在")
    for field in ("handle", "name", "desc"):
        val = getattr(body, field)
        if val is not None:
            setattr(t, field, val)
    db.commit()
    db.refresh(t)
    return t


@router.delete("/tones/{tone_id}", response_model=OkOut)
def delete_tone(tone_id: str, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> OkOut:
    """删除账号/调性 + 其参考爆款样本（admin）。历史变体保留 tone_id 不动。"""
    t = db.get(Tone, tone_id)
    if t is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号不存在")
    for s in db.scalars(select(StyleSample).where(StyleSample.tone_id == tone_id)):
        db.delete(s)
    db.delete(t)
    db.commit()
    return OkOut(ok=True)


# ===== 账号风格样本（往期爆款，few-shot 锚）=====
@router.get("/tones/{tone_id}/samples", response_model=list[StyleSampleOut])
def list_samples(
    tone_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> list[StyleSample]:
    """列出某账号/调性的爆款样本（最新在前）。登录即可查看。"""
    return list(
        db.scalars(
            select(StyleSample)
            .where(StyleSample.tone_id == tone_id)
            .order_by(StyleSample.created_at.desc(), StyleSample.id.desc())
        )
    )


@router.post("/tones/{tone_id}/samples", response_model=StyleSampleOut)
def add_sample(
    tone_id: str,
    body: StyleSampleIn,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> StyleSample:
    """为某账号新增一条爆款样本（素材员即可，内部工具）。"""
    if db.get(Tone, tone_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="调性不存在")
    text = body.body.strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="样本正文不能为空")
    s = StyleSample(
        id="sm_" + uuid4().hex[:12],
        tone_id=tone_id,
        body=text,
        source=(body.source or None),
        enabled=True,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.delete("/samples/{sample_id}", response_model=OkOut)
def delete_sample(
    sample_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> OkOut:
    """删除一条爆款样本。"""
    s = db.get(StyleSample, sample_id)
    if s is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="样本不存在")
    db.delete(s)
    db.commit()
    return OkOut(ok=True)
