"""行为埋点记录（DESIGN §4 M7）。record_event 供 telemetry 端点与「采用」端点共用。"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from .models import TelemetryEvent

ALLOWED_EVENTS: set[str] = {
    "adopt", "export", "copy",          # 强正信号
    "regenerate", "dismiss",            # 弱负信号
    "edit",                             # 采用前编辑句子
    "relevance",                        # 新闻相关性打标（召回/排序信号）
    "generate", "generate_from_news",   # 生成来源
    "expand", "dwell",                  # 弱兴趣
}


def record_event(
    db: Session,
    *,
    user: str,
    event_type: str,
    variant_id: str | None = None,
    news_id: str | None = None,
    tone_id: str | None = None,
    position: int | None = None,
    edited_sentences: list[str] | None = None,
    meta: dict | None = None,
) -> TelemetryEvent:
    ev = TelemetryEvent(
        id="e_" + uuid4().hex[:12],
        user=user,
        event_type=event_type,
        variant_id=variant_id,
        news_id=news_id,
        tone_id=tone_id,
        position=position,
        edited_sentences=edited_sentences,
        meta=meta,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    db.add(ev)
    db.commit()
    return ev
