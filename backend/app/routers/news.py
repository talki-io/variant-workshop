from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import News, User
from ..schemas import NewsLabelIn, NewsOut, NewsPageOut
from ..security import get_current_user
from ..telemetry import record_event

router = APIRouter(prefix="/api", tags=["news"])

_LABELS = {"none", "relevant", "irrelevant"}


@router.get("/news", response_model=NewsPageOut)
def get_news(
    q: str | None = None,
    source: list[str] = Query(default=[]),
    sort: str = "time",  # time（最新在前）| heat（热度优先）
    only_unlabeled: bool = Query(False, alias="onlyUnlabeled"),
    include_irrelevant: bool = Query(False, alias="includeIrrelevant"),  # 默认隐藏「不相关」
    date_from: str | None = Query(None, alias="dateFrom"),  # YYYY-MM-DD，按发布日期（含）
    date_to: str | None = Query(None, alias="dateTo"),  # YYYY-MM-DD（含）
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> NewsPageOut:
    """分页 + 服务端检索/筛选/排序。供新闻库下滑加载。

    搜索走 headline ILIKE；来源多选；仅未打标=label='none'；日期按 published_at 的日期段过滤。
    返回 items（当前页）+ total（命中总数，供前端判断 hasMore）+ sources（全表来源，供下拉，与分页无关）。
    """
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    conds = []
    if not include_irrelevant:  # 默认排除已判/已标为「不相关」的新闻
        conds.append(News.label != "irrelevant")
    if q and q.strip():
        conds.append(News.headline.ilike(f"%{q.strip()}%"))
    if source:
        conds.append(News.source.in_(source))
    if only_unlabeled:
        conds.append(News.label == "none")
    if date_from:  # published_at 形如 2026-07-08T15:04:42+07:00，取前 10 位日期比较
        conds.append(func.substr(News.published_at, 1, 10) >= date_from)
    if date_to:
        conds.append(func.substr(News.published_at, 1, 10) <= date_to)

    total = db.scalar(select(func.count()).select_from(News).where(*conds)) or 0
    order = (
        [News.heat.desc(), News.published_at.desc(), News.id.desc()]
        if sort == "heat"
        else [News.published_at.desc(), News.id.desc()]
    )
    rows = list(db.scalars(select(News).where(*conds).order_by(*order).limit(limit).offset(offset)))
    all_sources = list(db.scalars(select(News.source).distinct().order_by(News.source)))
    return NewsPageOut(
        items=[NewsOut.model_validate(n, from_attributes=True) for n in rows],
        total=total,
        sources=all_sources,
    )


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
