from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import QuotaConfig, User
from ..schemas import QuotaConfigIn, QuotaConfigOut, QuotaOut, UserQuotaOut
from ..security import require_admin
from ..usage import global_tokens_today, user_tokens_today

router = APIRouter(prefix="/api", tags=["quota"], dependencies=[Depends(require_admin)])


def _quota_view(db: Session, cfg: QuotaConfig, user: User) -> QuotaOut:
    """由 QuotaConfig 行 + 今日实时记账组装出参（GET/PUT 共用）。"""
    global_used = cfg.global_used + global_tokens_today(db)
    global_used_pct = round(min(global_used / cfg.global_daily * 100, 100), 2) if cfg.global_daily else 0.0
    config = QuotaConfigOut(
        per_user_daily=cfg.per_user_daily,
        over_threshold_pct=cfg.over_threshold_pct,
        circuit_breaker=cfg.circuit_breaker,
        breaker_condition=cfg.breaker_condition,
        global_daily=cfg.global_daily,
        global_used=global_used,
        global_used_pct=global_used_pct,
    )
    # 真实用户账号（admin/editor…）+ 各自今日真实用量；当前用户置顶标 isSelf，其余按用量降序
    rows: list[tuple[bool, int, UserQuotaOut]] = []
    for u in db.scalars(select(User).order_by(User.id)):
        is_self = u.name == user.name
        used = user_tokens_today(db, u.name)
        rows.append((
            is_self,
            used,
            UserQuotaOut(
                name=f"{u.name}（你）" if is_self else u.name,
                used=used,
                total=cfg.per_user_daily,
                is_self=is_self or None,
            ),
        ))
    rows.sort(key=lambda r: (not r[0], -r[1]))  # 自己优先，其余今日用量降序
    users = [r[2] for r in rows]
    return QuotaOut(config=config, users=users)


@router.get("/quota", response_model=QuotaOut)
def get_quota(db: Session = Depends(get_db), user: User = Depends(require_admin)) -> QuotaOut:
    cfg = db.get(QuotaConfig, 1)
    return _quota_view(db, cfg, user)


@router.put("/quota", response_model=QuotaOut)
def update_quota(
    body: QuotaConfigIn, db: Session = Depends(get_db), user: User = Depends(require_admin)
) -> QuotaOut:
    """保存配额/限流配置（admin）。globalUsed/globalUsedPct 为实时派生量，不接受写入。"""
    cfg = db.get(QuotaConfig, 1)
    cfg.per_user_daily = body.per_user_daily
    cfg.over_threshold_pct = body.over_threshold_pct
    cfg.circuit_breaker = body.circuit_breaker
    cfg.breaker_condition = body.breaker_condition
    cfg.global_daily = body.global_daily
    db.commit()
    db.refresh(cfg)
    return _quota_view(db, cfg, user)
