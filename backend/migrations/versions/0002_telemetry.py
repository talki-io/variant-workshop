"""telemetry_event table

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-02
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "telemetry_event",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("variant_id", sa.String(), nullable=True),
        sa.Column("news_id", sa.String(), nullable=True),
        sa.Column("tone_id", sa.String(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.Column("edited_sentences", postgresql.JSONB(), nullable=True),
        sa.Column("meta", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=False),
    )
    op.create_index("ix_telemetry_event_event_type", "telemetry_event", ["event_type"])
    op.create_index("ix_telemetry_event_variant_id", "telemetry_event", ["variant_id"])


def downgrade() -> None:
    op.drop_index("ix_telemetry_event_variant_id", table_name="telemetry_event")
    op.drop_index("ix_telemetry_event_event_type", table_name="telemetry_event")
    op.drop_table("telemetry_event")
