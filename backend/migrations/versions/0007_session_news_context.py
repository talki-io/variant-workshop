"""generation_session 增加 news_context（引用新闻的事实底稿快照）。

「引用新闻生成」二次迭代：把新闻的结构化素材（标题/关键事实/标的/角度）随会话持久化，
用于生成 grounding，并让会话恢复后的「重新生成」仍贴合原新闻事实。
列 nullable、加列即用，对既有行（未引用新闻的会话）无影响。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("generation_session", sa.Column("news_context", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("generation_session", "news_context")
