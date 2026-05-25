"""remove irrelevant event fields

Revision ID: 20260517_remove_fields
Revises: 48a58288ab36
Create Date: 2026-05-17

Description:
    Removes irrelevant fields from events table:
    - difficulty_level (not needed for virtual events)
    - location fields (location, location_name, city, state, country) - all events are virtual
    - total_distance (not relevant at event level, tracked at activity level)
    - max_participants (exists at tier/activity level)
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic
revision = "20260517_remove_fields"
down_revision = "48a58288ab36"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Remove irrelevant columns from events table"""
    # Drop columns
    op.drop_column("events", "difficulty_level")
    op.drop_column("events", "total_distance")
    op.drop_column("events", "max_participants")
    op.drop_column("events", "location")
    op.drop_column("events", "location_name")
    op.drop_column("events", "city")
    op.drop_column("events", "state")
    op.drop_column("events", "country")


def downgrade() -> None:
    """Restore removed columns (for rollback)"""
    # Restore columns (with nullable=True for safety)
    op.add_column("events", sa.Column("country", sa.String(100), nullable=True))
    op.add_column("events", sa.Column("state", sa.String(100), nullable=True))
    op.add_column("events", sa.Column("city", sa.String(100), nullable=True))
    op.add_column("events", sa.Column("location_name", sa.String(255), nullable=True))
    op.add_column("events", sa.Column("location", sa.String(500), nullable=True))
    op.add_column("events", sa.Column("max_participants", sa.Integer, nullable=True))
    op.add_column("events", sa.Column("total_distance", sa.Numeric(10, 2), nullable=True))
    op.add_column("events", sa.Column("difficulty_level", sa.String(50), nullable=True))

    # Re-create indexes
    op.create_index("ix_events_city", "events", ["city"])
    op.create_index("ix_events_state", "events", ["state"])
    op.create_index("ix_events_country", "events", ["country"])
