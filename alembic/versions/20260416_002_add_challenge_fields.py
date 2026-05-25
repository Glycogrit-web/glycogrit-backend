"""add challenge fields and activity tracking

Revision ID: 002
Revises: 001
Create Date: 2026-04-16 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add challenge-related fields to events table
    op.add_column("events", sa.Column("difficulty_level", sa.String(length=50), nullable=True))
    op.add_column("events", sa.Column("goals", JSONB, nullable=True))
    op.add_column("events", sa.Column("rewards", JSONB, nullable=True))
    op.add_column("events", sa.Column("banner_image_url", sa.String(length=500), nullable=True))
    op.add_column("events", sa.Column("rules", sa.Text(), nullable=True))
    op.add_column("events", sa.Column("start_date", sa.Date(), nullable=True))
    op.add_column("events", sa.Column("end_date", sa.Date(), nullable=True))
    op.add_column("events", sa.Column("location", sa.String(length=500), nullable=True))

    # Create indexes for new date fields
    op.create_index("ix_events_start_date", "events", ["start_date"], unique=False)
    op.create_index("ix_events_end_date", "events", ["end_date"], unique=False)

    # Create event_activities table
    op.create_table(
        "event_activities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("registration_id", sa.Integer(), nullable=True),
        sa.Column("distance", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("duration", sa.Integer(), nullable=True),
        sa.Column("activity_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["events.id"],
        ),
        sa.ForeignKeyConstraint(
            ["registration_id"],
            ["registrations.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for event_activities
    op.create_index("ix_event_activities_id", "event_activities", ["id"], unique=False)
    op.create_index("ix_event_activities_user_id", "event_activities", ["user_id"], unique=False)
    op.create_index("ix_event_activities_event_id", "event_activities", ["event_id"], unique=False)
    op.create_index(
        "ix_event_activities_registration_id", "event_activities", ["registration_id"], unique=False
    )
    op.create_index(
        "ix_event_activities_activity_date", "event_activities", ["activity_date"], unique=False
    )


def downgrade() -> None:
    # Drop event_activities table and indexes
    op.drop_index("ix_event_activities_activity_date", table_name="event_activities")
    op.drop_index("ix_event_activities_registration_id", table_name="event_activities")
    op.drop_index("ix_event_activities_event_id", table_name="event_activities")
    op.drop_index("ix_event_activities_user_id", table_name="event_activities")
    op.drop_index("ix_event_activities_id", table_name="event_activities")
    op.drop_table("event_activities")

    # Remove indexes for date fields
    op.drop_index("ix_events_end_date", table_name="events")
    op.drop_index("ix_events_start_date", table_name="events")

    # Remove challenge-related fields from events table
    op.drop_column("events", "location")
    op.drop_column("events", "end_date")
    op.drop_column("events", "start_date")
    op.drop_column("events", "rules")
    op.drop_column("events", "banner_image_url")
    op.drop_column("events", "rewards")
    op.drop_column("events", "goals")
    op.drop_column("events", "difficulty_level")
