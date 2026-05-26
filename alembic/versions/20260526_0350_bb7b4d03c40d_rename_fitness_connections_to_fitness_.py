"""Rename fitness_connections to fitness_tracker_connections

Revision ID: bb7b4d03c40d
Revises: 64cec31dd3a1
Create Date: 2026-05-26 03:50:34.046872

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bb7b4d03c40d"
down_revision: str | None = "64cec31dd3a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Rename fitness_connections table to fitness_tracker_connections.

    This migration ensures consistency between the codebase and database schema.
    The FitnessConnection model uses __tablename__ = "fitness_tracker_connections"
    but the production database currently has "fitness_connections".
    """
    # Check if the old table exists before renaming
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if "fitness_connections" in existing_tables:
        # Rename the table
        op.rename_table("fitness_connections", "fitness_tracker_connections")
        print("✅ Renamed fitness_connections -> fitness_tracker_connections")
    elif "fitness_tracker_connections" in existing_tables:
        print("⏭️  Table fitness_tracker_connections already exists, skipping rename")
    else:
        print("⚠️  Neither fitness_connections nor fitness_tracker_connections exists")


def downgrade() -> None:
    """
    Rollback: Rename fitness_tracker_connections back to fitness_connections.
    """
    # Check if the new table exists before renaming back
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if "fitness_tracker_connections" in existing_tables:
        # Rename back to original name
        op.rename_table("fitness_tracker_connections", "fitness_connections")
        print("✅ Rolled back: fitness_tracker_connections -> fitness_connections")
    else:
        print("⚠️  Table fitness_tracker_connections does not exist, cannot rollback")
