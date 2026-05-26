"""add oauth fields to users

Revision ID: 003
Revises: 002
Create Date: 2026-04-17

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    """Add OAuth fields to users table"""
    # Make password_hash nullable for OAuth users
    op.alter_column("users", "password_hash", existing_type=sa.String(length=255), nullable=True)

    # Add OAuth provider field
    op.add_column("users", sa.Column("oauth_provider", sa.String(length=50), nullable=True))

    # Add OAuth ID field with index
    op.add_column("users", sa.Column("oauth_id", sa.String(length=255), nullable=True))
    op.create_index("ix_users_oauth_id", "users", ["oauth_id"])

    # Add profile picture URL field
    op.add_column("users", sa.Column("profile_picture_url", sa.String(length=500), nullable=True))


def downgrade():
    """Remove OAuth fields from users table"""
    # Remove profile picture URL
    op.drop_column("users", "profile_picture_url")

    # Remove OAuth ID and its index
    op.drop_index("ix_users_oauth_id", table_name="users")
    op.drop_column("users", "oauth_id")

    # Remove OAuth provider
    op.drop_column("users", "oauth_provider")

    # Make password_hash non-nullable again
    op.alter_column("users", "password_hash", existing_type=sa.String(length=255), nullable=False)
