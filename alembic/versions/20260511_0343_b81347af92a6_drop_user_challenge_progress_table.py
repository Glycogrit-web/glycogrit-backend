"""drop_user_challenge_progress_table

Phase 3 of database cleanup: Remove legacy user_challenge_progress table

This table has been fully replaced by:
- registrations table (user enrollment)
- activity_progress table (progress tracking with per-source data)

The user_challenge_progress table was a legacy aggregation table that duplicated
data now properly normalized in activity_progress.

Note: ChallengeEvaluationService has been deprecated and marked for refactoring.

Revision ID: b81347af92a6
Revises: e3fc025475e9
Create Date: 2026-05-11 03:43:57.240497

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b81347af92a6'
down_revision: Union[str, None] = 'e3fc025475e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop legacy user_challenge_progress table
    op.execute("DROP TABLE IF EXISTS user_challenge_progress CASCADE")


def downgrade() -> None:
    # Cannot restore - data migration required
    # Use activity_progress data to restore if needed
    raise NotImplementedError(
        "Downgrade not supported. The user_challenge_progress table has been removed. "
        "Data must be migrated from activity_progress if restoration is required."
    )
