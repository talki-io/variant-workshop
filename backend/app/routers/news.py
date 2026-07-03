from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import News, User
from ..schemas import NewsLabelIn, NewsOut
from ..security import get_current_user
from ..telemetry import record_event

router = APIRouter(prefix="/api", tags=["news"])

_LABELS = {"none", "relevant", "irrelevant"}


@router.get("/news", response_model=list[NewsOut])
def get_news(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[News]:
    return list(db.scalars(select(News).order_by(News.id)))


@router.put("/news/{news_id}/label", response_model=NewsOut)
def label_news(
    news_id: str,
    body: NewsLabelIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> News:
    """新闻打标（相关/不相关/取消）落库。editor/admin 均可。同时记 M7 relevance 信号。"""
    if body.label not in _LABELS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"label 必须是 {sorted(_LABELS)} 之一",
        )
    news = db.get(News, news_id)
    if news is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="新闻不存在")
    news.label = body.label
    # M7 隐式信号：打标反映相关性判断，供下一轮召回/排序学习（record_event 内部 commit）
    record_event(db, user=user.name, event_type="relevance", news_id=news_id, meta={"label": body.label})
    db.refresh(news)
    return news
