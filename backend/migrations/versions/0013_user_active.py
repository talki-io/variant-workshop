"""users 增加 active（启用/停用，软删）。

用户管理支持"停用"作为删除的安全替代：停用后不能登录、现存 token 立即失效，
但保留其历史与归属，可随时恢复。存量用户回填 active=true。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    op.drop_column("users", "active")
