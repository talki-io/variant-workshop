"""删除废弃的 user_quota 表（孤儿假数据表）。

历史遗留：早期配额页「按用户」用 user_quota 表灌假用户（张三/李四…）。
自 routers/quota.py 改为从真实 users 表 + 今日实时 token 记账组装出参后，
该表已无任何代码读写，live 库中也早已清空（0 行）。此处把这张空的孤儿表
从 schema 中彻底移除，消除「残留假数据表」。downgrade 可原样重建（无数据）。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("user_quota")


def downgrade() -> None:
    op.create_table(
        "user_quota",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("used", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("is_self", sa.Boolean(), nullable=False),
        sa.Column("sort", sa.Integer(), nullable=False),
    )
