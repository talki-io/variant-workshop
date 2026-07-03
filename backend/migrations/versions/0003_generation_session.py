"""generation_session table + variants.session_id

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-02
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "generation_session",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user", sa.String(), nullable=False),
        sa.Column("tone_id", sa.String(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("source_headline", sa.Text(), nullable=True),
        sa.Column("diversity", sa.Float(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
    )
    op.create_index("ix_generation_session_user", "generation_session", ["user"])
    op.add_column("variants", sa.Column("session_id", sa.String(), nullable=True))
    op.create_index("ix_variants_session_id", "variants", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_variants_session_id", table_name="variants")
    op.drop_column("variants", "session_id")
    op.drop_index("ix_generation_session_user", table_name="generation_session")
    op.drop_table("generation_session")
