"""新闻契约端点（variant-migration 阶段 1）。

Java（yudao module-variant）通过 `GET /api/contract/news` 增量拉取采集器抓到的原始新闻，
自行富化后写入 yudao 的 MySQL。这是 Python 采集服务与 Java 主后端之间**唯一**的数据缝。

设计要点：
- 鉴权走服务令牌（X-Service-Token），非用户 JWT——这是服务间调用，与前端登录无关。
- 增量游标用 (ingested_at, id) 复合键，非 published_at（可回填历史时间，不单调）。
  Java 存上一页最后一条的 (ingestedAt, id) 为 watermark，下次以 since=<ts>&sinceId=<id> 拉取。
- 只返回原始事实 + summary（富化输入）；富化（相关性/摘要/key_facts）是 Java 的活，不在此。
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import and_, or_, select
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
        default=None, description="游标时刻；配合 sinceId 使用。不传=从头拉"
    ),
    since_id: str | None = Query(
        default=None,
        alias="sinceId",
        description="游标 id（上一页 nextId）。不传时退化为「ingestedAt 严格晚于 since」的旧语义",
    ),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> NewsFeedPage:
    """增量拉取新闻。按 (ingested_at, id) 升序，返回 <= limit 条 + 下一页复合 watermark。

    ⚠️ 游标必须是 (ingested_at, id) 复合键，不能只用 ingested_at：
    ingested_at **不唯一**——迁移 0015 给存量行统一盖了 now()，实测 356 行共享同一时间戳。
    只用时间戳 + 严格 `>` 时，第二页会把所有同刻行整体跳过（356 行只拉得到前 100 行，
    其余 256 行永久不可达），而调用方收到的是「成功、0 条新数据」，毫无异常迹象。
    复合游标下的续拉条件与排序键严格对应：ingested_at > since OR (= since AND id > since_id)。
    """
    stmt = select(News)
    if since is not None:
        if since_id is not None:
            # 与 ORDER BY (ingested_at, id) 严格对应的行式比较
            stmt = stmt.where(
                or_(
                    News.ingested_at > since,
                    and_(News.ingested_at == since, News.id > since_id),
                )
            )
        else:
            # 兼容旧调用方（只传 since）：保持原严格 `>` 语义
            stmt = stmt.where(News.ingested_at > since)
    stmt = stmt.order_by(News.ingested_at.asc(), News.id.asc()).limit(limit)
    rows = list(db.scalars(stmt))
    items = [NewsFeedItem.model_validate(n, from_attributes=True) for n in rows]
    next_since = rows[-1].ingested_at if rows else None
    next_id = rows[-1].id if rows else None
    return NewsFeedPage(items=items, next_since=next_since, next_id=next_id)
