"""新增 style_sample 表（账号往期爆款样本，few-shot 风格锚）。

「引用新闻文案像标题不像文案」根因之一是缺风格锚——用户提供真实爆款后，
把它作为该账号的风格样本入库，生成时抽取若干条做 few-shot 注入。
DESIGN「离线校准层」的最小可用形态。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "style_sample",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tone_id", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.String(), nullable=False),
    )
    op.create_index("ix_style_sample_tone_id", "style_sample", ["tone_id"])


def downgrade() -> None:
    op.drop_index("ix_style_sample_tone_id", table_name="style_sample")
    op.drop_table("style_sample")
