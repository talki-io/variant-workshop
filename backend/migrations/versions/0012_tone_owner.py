"""tones 增加 owner_id（账号归属用户）。

账号（Tone）与其参考爆款样本（StyleSample）改为按创建者隔离：每个用户只管理自己
新增的账号与参考文案，彼此不可见、互不干扰。存量账号回填给内置管理员 u_admin，
保证既有样本/变体归属不丢。列 nullable + 建索引（按 owner 过滤是热路径）。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tones", sa.Column("owner_id", sa.String(), nullable=True))
    # 存量账号（种子 t1-t4 等）归属内置管理员，避免既有样本/变体失去归属主
    op.execute("UPDATE tones SET owner_id = 'u_admin' WHERE owner_id IS NULL")
    op.create_index("ix_tones_owner_id", "tones", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_tones_owner_id", table_name="tones")
    op.drop_column("tones", "owner_id")
