"""budget period

Revision ID: 0003
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"


def upgrade() -> None:
    op.add_column("users", sa.Column("period_start", sa.Date, nullable=True))
    op.add_column("users", sa.Column("period_end", sa.Date, nullable=True))
    op.add_column("users", sa.Column("anchor_day", sa.SmallInteger, nullable=True))
    op.add_column(
        "users", sa.Column("auto_renew", sa.Boolean, nullable=False, server_default="true")
    )


def downgrade() -> None:
    for c in ("auto_renew", "anchor_day", "period_end", "period_start"):
        op.drop_column("users", c)
