"""news 表加 summary + ingested_at：支撑「Java 拉取新闻 + 富化移交 Java」契约。

迁移背景（variant-migration 阶段 1）：
- summary：采集时 RSS 原文摘要此前仅作富化入参、用完即丢，News 未持久化。富化移交 Java 后，
  Java 需要原文才能富化 → 补此列，采集入库时一并写入。
- ingested_at：机器游标。Java 增量拉取以此为 watermark，与 published_at（可回填历史时间）解耦。
  存量行由 server_default now() 统一回填为迁移时刻（Java 首次同步会全量拉一遍）。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("news", sa.Column("summary", sa.Text(), nullable=False, server_default=""))
    op.add_column(
        "news",
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    # 增量拉取按 ingested_at 排序 + 过滤，建索引避免全表扫。
    op.create_index("ix_news_ingested_at", "news", ["ingested_at"])


def downgrade() -> None:
    op.drop_index("ix_news_ingested_at", table_name="news")
    op.drop_column("news", "ingested_at")
    op.drop_column("news", "summary")
