"""add_how_it_works_field_to_events

Revision ID: 691b93cc90b3
Revises: 8a4c3d7f2e1b
Create Date: 2026-05-15 20:49:23.113420

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "691b93cc90b3"
down_revision: str | None = "8a4c3d7f2e1b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add how_it_works column to events table
    op.add_column(
        "events", sa.Column("how_it_works", postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )


def downgrade() -> None:
    # Remove how_it_works column from events table
    op.drop_column("events", "how_it_works")
