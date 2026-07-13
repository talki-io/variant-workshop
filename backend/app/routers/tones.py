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
from ..security import get_current_user

router = APIRouter(prefix="/api", tags=["tones"])


def _owned_tone(db: Session, tone_id: str, user: User) -> Tone:
    """取当前用户名下的账号；不存在或不属于本人一律 404（不泄露他人账号是否存在）。"""
    t = db.get(Tone, tone_id)
    if t is None or t.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号不存在")
    return t


# ===== 账号 / 调性管理（按创建者隔离：每个用户只看得到、管得了自己新增的）=====
@router.get("/tones", response_model=list[ToneOut])
def get_tones(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[Tone]:
    """列出当前用户自己的账号。用户之间互不可见、互不干扰。"""
    return list(db.scalars(select(Tone).where(Tone.owner_id == user.id).order_by(Tone.id)))


@router.post("/tones", response_model=ToneOut, status_code=status.HTTP_201_CREATED)
def create_tone(
    body: ToneCreateIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Tone:
    """新增账号/调性。管理员与素材员都可创建，归属创建者本人。"""
    if not body.name.strip() or not body.handle.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="账号名与 handle 不能为空")
    t = Tone(id="t_" + uuid4().hex[:8], handle=body.handle.strip(),
             name=body.name.strip(), desc=body.desc.strip(), owner_id=user.id)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.put("/tones/{tone_id}", response_model=ToneOut)
def update_tone(
    tone_id: str, body: ToneUpdateIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Tone:
    """部分更新自己的账号/调性。只能改本人名下账号。"""
    t = _owned_tone(db, tone_id, user)
    for field in ("handle", "name", "desc"):
        val = getattr(body, field)
        if val is not None:
            setattr(t, field, val)
    db.commit()
    db.refresh(t)
    return t


@router.delete("/tones/{tone_id}", response_model=OkOut)
def delete_tone(tone_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> OkOut:
    """删除自己的账号 + 其参考爆款样本。历史变体保留 tone_id 不动。只能删本人名下账号。"""
    t = _owned_tone(db, tone_id, user)
    for s in db.scalars(select(StyleSample).where(StyleSample.tone_id == tone_id)):
        db.delete(s)
    db.delete(t)
    db.commit()
    return OkOut(ok=True)


# ===== 账号风格样本（往期爆款，few-shot 锚）——随账号归属隔离 =====
@router.get("/tones/{tone_id}/samples", response_model=list[StyleSampleOut])
def list_samples(
    tone_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[StyleSample]:
    """列出自己某账号的爆款样本（最新在前）。仅本人名下账号可读。"""
    _owned_tone(db, tone_id, user)
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
    user: User = Depends(get_current_user),
) -> StyleSample:
    """为自己某账号新增一条爆款样本。仅本人名下账号可写。"""
    _owned_tone(db, tone_id, user)
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
    sample_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> OkOut:
    """删除一条爆款样本。仅能删自己名下账号的样本。"""
    s = db.get(StyleSample, sample_id)
    if s is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="样本不存在")
    # 样本归属由其所属账号决定：账号不属于本人则视同样本不存在
    _owned_tone(db, s.tone_id, user)
    db.delete(s)
    db.commit()
    return OkOut(ok=True)
