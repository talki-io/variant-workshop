"""Token 记账与用量统计（DESIGN §6 成本护栏）。

- estimate_tokens：本轮无真实模型调用，用确定性估算（prompt 长度 + 固定上下文开销 + 产出正文长度）。
  接真实 Anthropic 后，改成用返回的 usage.input_tokens/output_tokens 记真值即可，其余不变。
- record_usage：每次生成落一行 token_usage（§6 要求：user/模型/输入输出 token/成本）。
- user_tokens_today / global_tokens_today：按「今日」聚合，供配额校验与看板。
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import TokenUsage

# ¥ / 1k tokens —— 占位计价，接真实 Anthropic 时替换为实际单价。
RATES: dict[str, dict[str, float]] = {
    "Haiku": {"in": 0.006, "out": 0.03},
    "Sonnet": {"in": 0.022, "out": 0.11},
    "Opus": {"in": 0.11, "out": 0.55},
}
# 模板 + 语感指纹 + 热点卡等固定上下文的估算开销（tokens）。
SYSTEM_OVERHEAD_TOKENS = 800


def estimate_tokens(prompt: str, variant_bodies: list[str], model: str = "Sonnet") -> tuple[int, int, float]:
    input_tokens = SYSTEM_OVERHEAD_TOKENS + max(1, len(prompt) // 4)
    output_tokens = sum(max(1, len(b) // 4) for b in variant_bodies) or 1
    rate = RATES.get(model, RATES["Sonnet"])
    cost = round(input_tokens / 1000 * rate["in"] + output_tokens / 1000 * rate["out"], 4)
    return input_tokens, output_tokens, cost


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def record_usage(
    db: Session, user: str, model: str, input_tokens: int, output_tokens: int, cost: float, scene: str
) -> TokenUsage:
    row = TokenUsage(
        id="u_" + uuid4().hex[:12],
        user=user,
        time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost=cost,
        scene=scene,
    )
    db.add(row)
    db.commit()
    return row


def _sum_today(db: Session, *conditions) -> int:
    stmt = select(func.coalesce(func.sum(TokenUsage.input_tokens + TokenUsage.output_tokens), 0)).where(
        TokenUsage.time.like(f"{today_str()}%"), *conditions
    )
    return int(db.scalar(stmt) or 0)


def user_tokens_today(db: Session, user: str) -> int:
    return _sum_today(db, TokenUsage.user == user)


def global_tokens_today(db: Session) -> int:
    return _sum_today(db)
