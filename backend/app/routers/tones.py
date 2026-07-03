from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import StyleSample, Tone, User
from ..schemas import OkOut, StyleSampleIn, StyleSampleOut, ToneOut
from ..security import get_current_user

router = APIRouter(prefix="/api", tags=["tones"])


@router.get("/tones", response_model=list[ToneOut])
def get_tones(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[Tone]:
    return list(db.scalars(select(Tone).order_by(Tone.id)))


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
