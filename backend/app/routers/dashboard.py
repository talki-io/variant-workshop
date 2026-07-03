"""消耗看板：全部由真实 token_usage 聚合（KPI / 趋势 / Top用户 / 明细）。

数据来源是实际生成/清洗/抓取的记账行（usage.record_usage）；系统真实用户为
admin/editor/system。真实数据可能稀疏（只有近期有用量），这是如实反映，不再灌假数据。
"""

from collections import defaultdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import QuotaConfig, TokenUsage
from ..schemas import DailyUsageOut, DashboardOut, KpiOut, TopUserOut, UsageDetailOut
from ..security import require_admin

router = APIRouter(prefix="/api", tags=["dashboard"], dependencies=[Depends(require_admin)])

_MODEL_ORDER = ("Haiku", "Sonnet", "Opus")


def _model_label(m: str) -> str:
    ml = m.lower()
    if "haiku" in ml:
        return "Haiku"
    if "opus" in ml:
        return "Opus"
    return "Sonnet"


def _fmt_tokens(n: int) -> str:
    if n >= 1_000_000_000:
        return f"{n / 1e9:.1f}B"
    if n >= 1_000_000:
        return f"{n / 1e6:.1f}M"
    if n >= 1_000:
        return f"{n / 1e3:.1f}K"
    return str(n)


def _trend(cur: float, prev: float) -> float:
    return round((cur - prev) / prev * 100, 2) if prev else 0.0


@router.get("/dashboard", response_model=DashboardOut)
def get_dashboard(db: Session = Depends(get_db)) -> DashboardOut:
    rows = list(db.scalars(select(TokenUsage)))
    today = date.today().strftime("%Y-%m-%d")
    yday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")

    # —— KPI（今日 vs 昨日）——
    def tok(r: TokenUsage) -> int:
        return r.input_tokens + r.output_tokens

    today_rows = [r for r in rows if r.time[:10] == today]
    yday_rows = [r for r in rows if r.time[:10] == yday]
    today_tokens = sum(tok(r) for r in today_rows)
    today_cost = round(sum(r.cost for r in today_rows), 2)
    active_today = len({r.user for r in today_rows})

    cfg = db.get(QuotaConfig, 1)
    global_daily = cfg.global_daily if cfg else 0
    global_used = (cfg.global_used if cfg else 0) + today_tokens
    quota_pct = round(min(global_used / global_daily * 100, 100), 2) if global_daily else 0.0

    kpi = KpiOut(
        today_tokens=today_tokens,
        today_cost=today_cost,
        active_users=active_today,
        quota_used_pct=quota_pct,
        quota_used=_fmt_tokens(global_used),
        quota_total=_fmt_tokens(global_daily),
        tokens_trend=_trend(today_tokens, sum(tok(r) for r in yday_rows)),
        cost_trend=_trend(today_cost, round(sum(r.cost for r in yday_rows), 2)),
        users_trend=_trend(active_today, len({r.user for r in yday_rows})),
    )

    # —— 近 30 天按模型聚合（真实；无用量的日期不出现，图会如实稀疏）——
    by_day_model: dict[tuple[str, str], int] = defaultdict(int)
    for r in rows:
        by_day_model[(r.time[:10], _model_label(r.model))] += tok(r)
    keep_dates = sorted({d for (d, _) in by_day_model})[-30:]
    daily = [
        DailyUsageOut(date=d[5:], model=m, tokens=by_day_model.get((d, m), 0))
        for d in keep_dates
        for m in _MODEL_ORDER
    ]

    # —— Top 用户（真实，按累计 token 降序）——
    by_user: dict[str, int] = defaultdict(int)
    for r in rows:
        by_user[r.user] += tok(r)
    top = sorted(by_user.items(), key=lambda kv: kv[1], reverse=True)[:10]
    top_users = [TopUserOut(rank=i + 1, name=n, tokens=t) for i, (n, t) in enumerate(top)]

    # —— 明细（真实，最新在前）——
    details = [
        UsageDetailOut.model_validate(r, from_attributes=True)
        for r in sorted(rows, key=lambda r: r.time, reverse=True)
    ]

    return DashboardOut(kpi=kpi, daily=daily, top_users=top_users, details=details)
