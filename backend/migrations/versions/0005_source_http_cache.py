"""crawl_source 增加 HTTP 条件请求缓存列（etag / last_modified）。

二次迭代 M1 优化：抓取带 If-None-Match / If-Modified-Since，命中 304 短路。
两列均 nullable、加列即用，对既有行无影响。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("crawl_source", sa.Column("etag", sa.String(), nullable=True))
    op.add_column("crawl_source", sa.Column("last_modified", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("crawl_source", "last_modified")
    op.drop_column("crawl_source", "etag")
