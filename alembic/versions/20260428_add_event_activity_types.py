"""add event activity types many-to-many

Revision ID: 20260428_activity_types
Revises: 23c59d68f2e7
Create Date: 2026-04-28

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260428_activity_types"
down_revision = "23c59d68f2e7"
branch_labels = None
depends_on = None


def upgrade():
    # Create event_activity_types junction table
    op.create_table(
        "event_activity_types",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("activity_type", sa.String(length=50), nullable=False),
        sa.Column("is_primary", sa.Boolean(), default=False, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "activity_type", name="uq_event_activity_type"),
    )

    # Create indexes for better query performance
    op.create_index("ix_event_activity_types_event_id", "event_activity_types", ["event_id"])
    op.create_index(
        "ix_event_activity_types_activity_type", "event_activity_types", ["activity_type"]
    )

    # Migrate existing event_type data to new table
    # This will take each event's single event_type and create a record in the junction table
    op.execute("""
        INSERT INTO event_activity_types (event_id, activity_type, is_primary, created_at)
        SELECT id, event_type, true, created_at
        FROM events
        WHERE event_type IS NOT NULL
    """)

    # Note: We're keeping the event_type column for now to maintain backward compatibility
    # It can be removed in a future migration after verifying the new system works


def downgrade():
    # Drop indexes
    op.drop_index("ix_event_activity_types_activity_type", table_name="event_activity_types")
    op.drop_index("ix_event_activity_types_event_id", table_name="event_activity_types")

    # Drop table
    op.drop_table("event_activity_types")
