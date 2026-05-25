"""add_proof_image_and_stats_to_activity_progress

Revision ID: e9f4a2b1c5d3
Revises: 05baaa105680
Create Date: 2026-04-30 13:20:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e9f4a2b1c5d3'
down_revision: str | None = '05baaa105680'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Add fields to activity_progress that were previously in user_challenge_progress:
    - proof_image_url: User's uploaded proof image
    - total_activities: Count of activities (will be calculated from user_activity_logs)
    - total_duration_minutes: Total time spent (will be calculated from user_activity_logs)
    """
    # Add proof_image_url column
    op.add_column('activity_progress', sa.Column('proof_image_url', sa.String(500), nullable=True))

    # Add stats columns (to be populated from user_activity_logs)
    op.add_column('activity_progress', sa.Column('total_activities', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('activity_progress', sa.Column('total_duration_minutes', sa.Integer(), nullable=False, server_default='0'))

    # Migrate existing proof_image_url data from user_challenge_progress
    # Match on user_id and event_id (challenge_id in old table)
    op.execute("""
        UPDATE activity_progress ap
        SET proof_image_url = ucp.proof_image_url
        FROM user_challenge_progress ucp
        WHERE ap.user_id = ucp.user_id
          AND ap.event_id = ucp.challenge_id
          AND ucp.proof_image_url IS NOT NULL
    """)

    # Calculate and populate total_activities from user_activity_logs
    op.execute("""
        UPDATE activity_progress ap
        SET total_activities = (
            SELECT COUNT(*)
            FROM user_activity_logs ual
            WHERE ual.user_id = ap.user_id
              AND ual.event_id = ap.event_id
        )
    """)

    # Calculate and populate total_duration_minutes from user_activity_logs
    # Note: Skipping duration calculation as column may not exist yet
    # Will be calculated when activities are logged
    # op.execute("""
    #     UPDATE activity_progress ap
    #     SET total_duration_minutes = COALESCE((
    #         SELECT SUM(duration_minutes)
    #         FROM user_activity_logs ual
    #         WHERE ual.user_id = ap.user_id
    #           AND ual.event_id = ap.event_id
    #     ), 0)
    # """)


def downgrade() -> None:
    """Remove added columns"""
    op.drop_column('activity_progress', 'total_duration_minutes')
    op.drop_column('activity_progress', 'total_activities')
    op.drop_column('activity_progress', 'proof_image_url')
