"""新闻契约端点（variant-migration 阶段 1）。

Java（yudao module-variant）通过 `GET /api/contract/news` 增量拉取采集器抓到的原始新闻，
自行富化后写入 yudao 的 MySQL。这是 Python 采集服务与 Java 主后端之间**唯一**的数据缝。

设计要点：
- 鉴权走服务令牌（X-Service-Token），非用户 JWT——这是服务间调用，与前端登录无关。
- 增量游标用 ingested_at（入库时间），非 published_at（可回填历史时间，不单调）。
  Java 存上一页最后一条的 ingestedAt 为 watermark，下次以 since=<watermark> 拉取。
- 只返回原始事实 + summary（富化输入）；富化（相关性/摘要/key_facts）是 Java 的活，不在此。
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import News
from ..schemas import NewsFeedItem, NewsFeedPage

router = APIRouter(prefix="/api/contract", tags=["contract"])


def require_service_token(x_service_token: str = Header(default="")) -> None:
    """服务令牌校验。未配置 SERVICE_TOKEN 时一律 503，杜绝「空令牌匹配空配置」的后门。"""
    if not settings.service_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="新闻契约未启用：服务端未配置 SERVICE_TOKEN",
        )
    if x_service_token != settings.service_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="服务令牌无效")


@router.get("/news", response_model=NewsFeedPage, dependencies=[Depends(require_service_token)])
def pull_news(
    since: datetime | None = Query(
        default=None, description="只返回 ingestedAt 严格晚于此时刻的新闻；不传=从头拉"
    ),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> NewsFeedPage:
    """增量拉取新闻。按 ingested_at 升序，返回 <= limit 条 + 下一页 watermark。"""
    stmt = select(News)
    if since is not None:
        stmt = stmt.where(News.ingested_at > since)
    # (ingested_at, id) 双键排序：同一时刻多条时顺序稳定，避免翻页错位。
    stmt = stmt.order_by(News.ingested_at.asc(), News.id.asc()).limit(limit)
    rows = list(db.scalars(stmt))
    items = [NewsFeedItem.model_validate(n, from_attributes=True) for n in rows]
    next_since = rows[-1].ingested_at if rows else None
    return NewsFeedPage(items=items, next_since=next_since)
