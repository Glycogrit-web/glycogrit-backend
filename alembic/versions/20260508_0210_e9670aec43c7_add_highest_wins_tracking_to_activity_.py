"""add highest wins tracking to activity progress

Revision ID: e9670aec43c7
Revises: 11835e0ff1de
Create Date: 2026-05-08 02:10:17.997703

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e9670aec43c7"
down_revision: str | None = "2f33178a700f"  # Points to add_proof_image_viewed_flag (production)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add new columns for highest-wins tracking
    op.add_column(
        "activity_progress", sa.Column("highest_distance_source", sa.String(50), nullable=True)
    )
    op.add_column(
        "activity_progress", sa.Column("highest_distance_set_at", sa.TIMESTAMP(), nullable=True)
    )
    op.add_column(
        "activity_progress",
        sa.Column(
            "distance_by_source",
            sa.dialects.postgresql.JSONB(),
            nullable=False,
            server_default="{}",
        ),
    )

    # Backfill existing records with current data
    # Set highest_distance_source from sync_source
    # Set highest_distance_set_at from last_sync_at
    op.execute("""
        UPDATE activity_progress
        SET
            highest_distance_source = COALESCE(sync_source, 'unknown'),
            highest_distance_set_at = COALESCE(last_sync_at, updated_at),
            distance_by_source = jsonb_build_object(
                COALESCE(sync_source, 'unknown'),
                jsonb_build_object(
                    'distance_km', distance_completed::float,
                    'last_updated', COALESCE(last_sync_at, updated_at)::text,
                    'activity_count', total_activities
                )
            )
        WHERE highest_distance_source IS NULL
    """)


def downgrade() -> None:
    # Drop the columns
    op.drop_column("activity_progress", "distance_by_source")
    op.drop_column("activity_progress", "highest_distance_set_at")
    op.drop_column("activity_progress", "highest_distance_source")
