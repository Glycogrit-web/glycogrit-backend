"""make_activities_global_templates

Revision ID: f20292e84906
Revises: 22f99d04baf4
Create Date: 2026-05-28 02:56:33.214845

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f20292e84906'
down_revision: Union[str, None] = '22f99d04baf4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Make activities global templates by:
    1. Clearing existing event-specific activities
    2. Dropping event_id foreign key and column
    3. Creating 10 global activity templates based on the design
    """
    # Step 1: Clear existing activities (they were event-specific)
    op.execute("DELETE FROM event_activities;")

    # Step 2: Drop foreign key constraint and event_id column
    # Note: PostgreSQL will automatically drop the constraint when we drop the column
    op.drop_column('event_activities', 'event_id')

    # Step 3: Insert 10 global activity templates
    # RUNNING / WALKING activities
    op.execute("""
        INSERT INTO event_activities (name, activity_type, distance, description) VALUES
        ('3 km', 'running', 3.00, 'Run or walk — your choice'),
        ('5 Km', 'running', 5.00, 'Run or walk — your choice'),
        ('10 Km', 'running', 10.00, 'Run or walk — your choice'),
        ('21 Km (Half Marathon)', 'running', 21.00, 'Run or walk — your choice');
    """)

    # CYCLING activities
    op.execute("""
        INSERT INTO event_activities (name, activity_type, distance, description) VALUES
        ('5 Km', 'cycling', 5.00, 'Outdoor or indoor bike'),
        ('10 Km', 'cycling', 10.00, 'Outdoor or indoor bike'),
        ('25 Km', 'cycling', 25.00, 'Outdoor or indoor bike'),
        ('50 Km', 'cycling', 50.00, 'Outdoor or indoor bike'),
        ('100 Km', 'cycling', 100.00, 'Outdoor or indoor bike');
    """)


def downgrade() -> None:
    """Restore event_id column and constraint"""
    # Add back event_id column
    op.add_column('event_activities',
        sa.Column('event_id', sa.Integer(), nullable=True)
    )

    # Clear the global templates
    op.execute("DELETE FROM event_activities;")

    # Add back the foreign key constraint
    op.create_foreign_key(
        'event_activities_event_id_fkey',
        'event_activities', 'events',
        ['event_id'], ['id'],
        ondelete='CASCADE'
    )
