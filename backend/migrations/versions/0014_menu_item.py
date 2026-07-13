"""建 menu_item 表：数据驱动的侧栏导航注册表。

侧栏与面包屑从此表渲染，管理员可增删改现有页面的菜单项（名称/图标/排序/启用/按角色可见）。
默认菜单项由 seed_system 幂等灌入（所有环境都需要，故不放 demo 段）。
locked=true 的核心项（用户管理/菜单管理）禁止删除，防管理员误配自锁。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "menu_item",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("icon", sa.String(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("visible_roles", JSONB(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("locked", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_unique_constraint("uq_menu_item_path", "menu_item", ["path"])


def downgrade() -> None:
    op.drop_table("menu_item")
