"""initial

Revision ID: 0001
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

from app.config import get_settings

revision = "0001"
down_revision = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("monthly_budget", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.BigInteger, sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("name", sa.String(40), nullable=False),
        sa.Column("monthly_limit", sa.BigInteger),
        sa.UniqueConstraint("user_id", "name"),
    )
    op.create_index("ix_categories_user_id", "categories", ["user_id"])
    op.create_table(
        "expenses",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.BigInteger, sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("category_id", sa.Integer, sa.ForeignKey("categories.id", ondelete="RESTRICT")),
        sa.Column("amount", sa.BigInteger, nullable=False),
        sa.Column("note", sa.String(200), nullable=False, server_default=""),
        sa.Column("spent_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_expenses_user_id", "expenses", ["user_id"])
    op.create_index("ix_expenses_spent_at", "expenses", ["spent_at"])
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source", sa.String(200), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("embedding", Vector(get_settings().embedding_dim), nullable=False),
    )


def downgrade() -> None:
    for t in ("knowledge_chunks", "expenses", "categories", "users"):
        op.drop_table(t)
