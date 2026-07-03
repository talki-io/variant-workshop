"""initial schema: extension vector + 9 tables

Revision ID: 0001
Revises:
Create Date: 2026-07-02
"""
from typing import Sequence, Union

import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # pgvector 扩展必须先建（style_vectors 依赖 vector 类型）
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("avatar", sa.String(), nullable=True),
    )
    op.create_table(
        "tones",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("handle", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("desc", sa.String(), nullable=False),
    )
    op.create_table(
        "news",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("headline", sa.Text(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("published_at", sa.String(), nullable=False),
        sa.Column("published_label", sa.String(), nullable=False),
        sa.Column("freshness", sa.String(), nullable=False),
        sa.Column("heat", sa.Integer(), nullable=False),
        sa.Column("key_facts", postgresql.JSONB(), nullable=False),
        sa.Column("tickers", postgresql.JSONB(), nullable=False),
        sa.Column("angle_hints", postgresql.JSONB(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
    )
    op.create_table(
        "variants",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tone_id", sa.String(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("dimensions", postgresql.JSONB(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("soft_flag_sentence", sa.Text(), nullable=True),
        sa.Column("compliance", sa.String(), nullable=False),
        sa.Column("soft_flag_count", sa.Integer(), nullable=True),
        sa.Column("ai_score", sa.Integer(), nullable=False),
        sa.Column("style_distance", sa.Float(), nullable=False),
        sa.Column("confirmed", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_variants_tone_id", "variants", ["tone_id"])
    op.create_table(
        "token_usage",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user", sa.String(), nullable=False),
        sa.Column("time", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("cost", sa.Float(), nullable=False),
        sa.Column("scene", sa.String(), nullable=False),
    )
    op.create_table(
        "crawl_source",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("frequency", sa.String(), nullable=False),
        sa.Column("last_crawl", sa.String(), nullable=False),
        sa.Column("health", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "quota_config",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("per_user_daily", sa.Integer(), nullable=False),
        sa.Column("over_threshold_pct", sa.Integer(), nullable=False),
        sa.Column("circuit_breaker", sa.Boolean(), nullable=False),
        sa.Column("breaker_condition", sa.String(), nullable=False),
        sa.Column("global_daily", sa.Integer(), nullable=False),
        sa.Column("global_used", sa.Integer(), nullable=False),
        sa.Column("global_used_pct", sa.Float(), nullable=False),
    )
    op.create_table(
        "user_quota",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("used", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("is_self", sa.Boolean(), nullable=False),
        sa.Column("sort", sa.Integer(), nullable=False),
    )
    op.create_table(
        "style_vectors",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tone_id", sa.String(), nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(1536), nullable=True),
    )
    op.create_index("ix_style_vectors_tone_id", "style_vectors", ["tone_id"])


def downgrade() -> None:
    op.drop_index("ix_style_vectors_tone_id", table_name="style_vectors")
    op.drop_table("style_vectors")
    op.drop_table("user_quota")
    op.drop_table("quota_config")
    op.drop_table("crawl_source")
    op.drop_table("token_usage")
    op.drop_index("ix_variants_tone_id", table_name="variants")
    op.drop_table("variants")
    op.drop_table("news")
    op.drop_table("tones")
    op.drop_table("users")
