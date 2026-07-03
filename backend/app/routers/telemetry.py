"""行为埋点端点（M7 反馈闭环地基）：隐式信号入库 + 管理员汇总。

前端「采用/导出/复制/重新生成/划走/编辑/展开」等动作 fire-and-forget 打到 /api/telemetry；
下一轮 bandit 权重表消费本表（reward = 采用信号 − λ·合规命中）。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import TelemetryEvent, User
from ..schemas import AckOut, EventTypeCount, TelemetryIn, TelemetrySummaryOut, VariantAdoptCount
from ..security import get_current_user, require_admin
from ..telemetry import ALLOWED_EVENTS, record_event

router = APIRouter(prefix="/api", tags=["telemetry"])


@router.post("/telemetry", response_model=AckOut)
def ingest(body: TelemetryIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> AckOut:
    if body.event_type not in ALLOWED_EVENTS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"未知事件类型：{body.event_type}")
    ev = record_event(
        db,
        user=user.name,
        event_type=body.event_type,
        variant_id=body.variant_id,
        news_id=body.news_id,
        tone_id=body.tone_id,
        position=body.position,
        edited_sentences=body.edited_sentences,
        meta=body.meta,
    )
    return AckOut(ok=True, event_id=ev.id)


@router.get("/telemetry/summary", response_model=TelemetrySummaryOut, dependencies=[Depends(require_admin)])
def summary(db: Session = Depends(get_db)) -> TelemetrySummaryOut:
    total = int(db.scalar(select(func.count()).select_from(TelemetryEvent)) or 0)
    by_type = [
        EventTypeCount(event_type=t, count=int(c))
        for t, c in db.execute(
            select(TelemetryEvent.event_type, func.count())
            .group_by(TelemetryEvent.event_type)
            .order_by(func.count().desc())
        ).all()
    ]
    top_adopted = [
        VariantAdoptCount(variant_id=v, count=int(c))
        for v, c in db.execute(
            select(TelemetryEvent.variant_id, func.count())
            .where(TelemetryEvent.event_type == "adopt", TelemetryEvent.variant_id.isnot(None))
            .group_by(TelemetryEvent.variant_id)
            .order_by(func.count().desc())
            .limit(10)
        ).all()
    ]
    return TelemetrySummaryOut(total=total, by_type=by_type, top_adopted=top_adopted)
