"""Add Wahoo integration tables

Revision ID: 20260510_add_wahoo_integration
Revises: 20260510_add_garmin_integration
Create Date: 2026-05-10

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260510_add_wahoo_integration"
down_revision = "20260510_add_fitbit_integration"  # Points to add_fitbit_integration
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create wahoo_connections table"""
    op.create_table(
        "wahoo_connections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("token_type", sa.String(length=50), nullable=False, server_default="Bearer"),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column("wahoo_user_id", sa.String(length=255), nullable=False),
        sa.Column("user_data", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
        sa.UniqueConstraint("wahoo_user_id"),
    )

    # Create indexes for performance
    op.create_index("ix_wahoo_connections_user_id", "wahoo_connections", ["user_id"])
    op.create_index("ix_wahoo_connections_wahoo_user_id", "wahoo_connections", ["wahoo_user_id"])


def downgrade() -> None:
    """Drop wahoo_connections table"""
    op.drop_index("ix_wahoo_connections_wahoo_user_id", table_name="wahoo_connections")
    op.drop_index("ix_wahoo_connections_user_id", table_name="wahoo_connections")
    op.drop_table("wahoo_connections")
