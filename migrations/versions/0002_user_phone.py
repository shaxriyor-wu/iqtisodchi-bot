"""user phone

Revision ID: 0002
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"


def upgrade() -> None:
    op.add_column("users", sa.Column("phone", sa.String(20), nullable=True))
    op.create_unique_constraint("uq_users_phone", "users", ["phone"])


def downgrade() -> None:
    op.drop_constraint("uq_users_phone", "users")
    op.drop_column("users", "phone")
