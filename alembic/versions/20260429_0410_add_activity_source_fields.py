"""add_activity_source_fields

Revision ID: add_activity_source
Revises: add_sync_metadata
Create Date: 2026-04-29 04:10:00

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_activity_source"
down_revision = "add_sync_metadata"
branch_labels = None
depends_on = None


def upgrade():
    # Add source tracking fields to challenge_activities table
    op.add_column(
        "challenge_activities",
        sa.Column(
            "source_provider",
            sa.String(length=50),
            nullable=True,
            comment="Source of the activity: strava, google_fit, apple_health, etc.",
        ),
    )

    op.add_column(
        "challenge_activities",
        sa.Column(
            "external_activity_id",
            sa.String(length=255),
            nullable=True,
            comment="Provider-specific activity ID",
        ),
    )


def downgrade():
    # Drop columns
    op.drop_column("challenge_activities", "external_activity_id")
    op.drop_column("challenge_activities", "source_provider")
