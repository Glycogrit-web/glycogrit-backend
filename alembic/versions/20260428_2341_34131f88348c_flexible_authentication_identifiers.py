"""flexible_authentication_identifiers

Revision ID: 34131f88348c
Revises: fix_tier_payment
Create Date: 2026-04-28 23:41:48.793030

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '34131f88348c'
down_revision: str | None = 'fix_tier_payment'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Step 1: Make email column nullable
    # This allows users to register with only phone number
    op.alter_column('users', 'email',
                    existing_type=sa.String(255),
                    nullable=True,
                    existing_nullable=False)

    # Step 2: Add CHECK constraint to ensure at least one identifier exists
    # This prevents users from having neither email nor phone
    op.execute("""
        ALTER TABLE users
        ADD CONSTRAINT check_has_identifier
        CHECK (email IS NOT NULL OR phone IS NOT NULL)
    """)

    # Step 3: Safety check - ensure no existing users have null email
    # (All existing users should have email, this is just a safety measure)
    # If any users somehow have null email without phone, give them placeholder email
    op.execute("""
        UPDATE users
        SET email = CONCAT('placeholder_', id, '@glycogrit.internal')
        WHERE email IS NULL AND phone IS NULL
    """)


def downgrade() -> None:
    # Step 1: Remove CHECK constraint
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS check_has_identifier")

    # Step 2: Ensure all users have email before making it non-nullable
    # Give placeholder email to any phone-only users
    op.execute("""
        UPDATE users
        SET email = CONCAT('phone_', phone, '@glycogrit.internal')
        WHERE email IS NULL
    """)

    # Step 3: Make email non-nullable again
    op.alter_column('users', 'email',
                    existing_type=sa.String(255),
                    nullable=False,
                    existing_nullable=True)
