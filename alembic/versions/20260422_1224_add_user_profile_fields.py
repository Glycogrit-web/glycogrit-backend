"""add_user_profile_fields

Revision ID: a1b2c3d4e5f6
Revises: 99b3f79156bf
Create Date: 2026-04-22 12:24:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "99b3f79156bf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add age and t_shirt_size columns to users table
    op.add_column("users", sa.Column("age", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("t_shirt_size", sa.String(length=10), nullable=True))


def downgrade() -> None:
    # Remove age and t_shirt_size columns from users table
    op.drop_column("users", "t_shirt_size")
    op.drop_column("users", "age")
