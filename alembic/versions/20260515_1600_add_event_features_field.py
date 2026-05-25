"""Add event_features JSONB field to events table

Revision ID: 8a4c3d7f2e1b
Revises: bf01db9d3676
Create Date: 2026-05-15 16:00:00.000000

"""

import json

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision = "8a4c3d7f2e1b"
down_revision = "bf01db9d3676"
branch_labels = None
depends_on = None

# Default event features - 3 symbols shown on PedalPulse-style event cards
DEFAULT_FEATURES = {
    "default_symbols": [
        {"type": "activity", "icon": "running", "label": "Run / Walk / Ride", "enabled": True},
        {"type": "reward", "icon": "medal", "label": "Medal", "enabled": True},
        {"type": "shipping", "icon": "truck", "label": "Free ship", "enabled": True},
    ],
    "custom_symbols": [],
}


def upgrade():
    """Add event_features JSONB column and populate with defaults."""
    # Add column as nullable first
    op.add_column(
        "events",
        sa.Column(
            "event_features",
            JSONB,
            nullable=True,
            comment="Event features/symbols to display on cards (activity types, rewards, shipping)",
        ),
    )

    # Set default features for all existing events
    # Use parameterized query to prevent SQL injection
    from sqlalchemy import text

    features_json = json.dumps(DEFAULT_FEATURES)
    op.execute(
        text("UPDATE events SET event_features = :features::jsonb"), {"features": features_json}
    )

    print("✓ Added event_features column and set defaults for all events")


def downgrade():
    """Remove event_features column."""
    op.drop_column("events", "event_features")
    print("✓ Removed event_features column")
