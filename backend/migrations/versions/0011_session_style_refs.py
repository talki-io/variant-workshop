"""generation_session 增加 style_refs（本次临时仿写范本）。

「贴一段爆款让 AI 仿写变体」：临时范本走 few-shot（不入样本库），随会话持久化以便
刷新/切模块后恢复 + 重新生成仍参照。列 nullable、加列即用，对既有会话无影响。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("generation_session", sa.Column("style_refs", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("generation_session", "style_refs")
