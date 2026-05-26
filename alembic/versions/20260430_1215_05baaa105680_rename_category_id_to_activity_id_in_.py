"""rename_category_id_to_activity_id_in_activity_progress

Revision ID: 05baaa105680
Revises: b75d5dbdb278
Create Date: 2026-04-30 12:15:58.313737

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "05baaa105680"
down_revision: str | None = "b75d5dbdb278"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Rename category_id to activity_id in activity_progress table
    op.alter_column("activity_progress", "category_id", new_column_name="activity_id")


def downgrade() -> None:
    # Rename activity_id back to category_id
    op.alter_column("activity_progress", "activity_id", new_column_name="category_id")
