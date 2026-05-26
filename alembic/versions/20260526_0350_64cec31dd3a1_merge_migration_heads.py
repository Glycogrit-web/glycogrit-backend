"""Merge migration heads

Revision ID: 64cec31dd3a1
Revises: 20260517_remove_fields, add_audit_logging
Create Date: 2026-05-26 03:50:20.294759

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "64cec31dd3a1"
down_revision: str | None = ("20260517_remove_fields", "add_audit_logging")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
