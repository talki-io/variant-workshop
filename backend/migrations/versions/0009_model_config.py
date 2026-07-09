"""新增 model_config 表：按管线场景动态配置模型 + 参数。

生成/清洗/合规各阶段用哪个模型、max_tokens、temperature 均可在「模型管理」页动态改，
无需改代码。表为空时 llm 回退到内置默认（Sonnet/Haiku）。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "model_config",
        sa.Column("scene", sa.String(), primary_key=True),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("model_id", sa.String(), nullable=False),
        sa.Column("max_tokens", sa.Integer(), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.String(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("model_config")
