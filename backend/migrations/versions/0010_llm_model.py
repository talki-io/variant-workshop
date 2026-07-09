"""新增 llm_model 模型库（多厂商），model_config.model_id 改为引用其主键。

模型管理升级：从「场景存裸模型串」→「模型库(可 CRUD 多厂商) + 场景绑定」两层。
迁移灌 3 个默认 Anthropic 模型，并把既有 model_config 的裸串映射到对应库 id。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DEFAULTS = [
    ("mdl_haiku", "Haiku 4.5（快·省）", "claude-haiku-4-5"),
    ("mdl_sonnet", "Sonnet 5（均衡·主力）", "claude-sonnet-5"),
    ("mdl_opus", "Opus 4.8（最强·贵）", "claude-opus-4-8"),
]


def upgrade() -> None:
    op.create_table(
        "llm_model",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("model_id", sa.String(), nullable=False),
        sa.Column("base_url", sa.String(), nullable=True),
        sa.Column("api_key", sa.String(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.String(), nullable=False),
    )
    # 灌 3 个默认 Anthropic 模型（幂等：仅当表空）
    llm_model = sa.table(
        "llm_model",
        sa.column("id", sa.String), sa.column("name", sa.String), sa.column("provider", sa.String),
        sa.column("model_id", sa.String), sa.column("base_url", sa.String),
        sa.column("api_key", sa.String), sa.column("enabled", sa.Boolean), sa.column("created_at", sa.String),
    )
    op.bulk_insert(llm_model, [
        {"id": mid, "name": name, "provider": "anthropic", "model_id": bare,
         "base_url": None, "api_key": None, "enabled": True, "created_at": "2026-01-01 00:00:00"}
        for mid, name, bare in _DEFAULTS
    ])
    # 既有 model_config.model_id（裸串）→ 库 id 引用
    for mid, _name, bare in _DEFAULTS:
        op.execute(
            sa.text("UPDATE model_config SET model_id = :mid WHERE model_id = :bare").bindparams(mid=mid, bare=bare)
        )


def downgrade() -> None:
    # 还原引用为裸串
    for mid, _name, bare in _DEFAULTS:
        op.execute(
            sa.text("UPDATE model_config SET model_id = :bare WHERE model_id = :mid").bindparams(mid=mid, bare=bare)
        )
    op.drop_table("llm_model")
