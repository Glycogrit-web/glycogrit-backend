"""Add comprehensive audit logging system

Revision ID: add_audit_logging
Revises: add_coupon_system
Create Date: 2026-05-23

This migration adds comprehensive audit logging infrastructure:
1. audit_logs table - Immutable audit trail for all critical operations
2. Database rules to prevent updates/deletes (immutability)
3. Indexes for efficient querying by entity, actor, time, security events
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_audit_logging"
down_revision = "add_coupon_system"
branch_labels = None
depends_on = None


def upgrade():
    """
    Add audit logging table and constraints.

    SECURITY FEATURES:
    - Immutable audit trail (rules prevent UPDATE/DELETE)
    - Comprehensive metadata capture (IP, user agent, request ID)
    - Security event flagging for special attention
    - JSONB fields for flexible context storage
    """

    # ========================================
    # 1. CREATE AUDIT_LOGS TABLE
    # ========================================
    op.create_table(
        "audit_logs",
        sa.Column(
            "id", sa.BigInteger(), nullable=False, primary_key=True
        ),  # Use BIGSERIAL for high volume
        # Audit Context
        sa.Column(
            "entity_type", sa.String(length=50), nullable=False
        ),  # 'registration', 'payment', 'tier', 'coupon', 'event'
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "action", sa.String(length=50), nullable=False
        ),  # 'create', 'update', 'delete', 'status_change', 'price_change'
        # Actor Information
        sa.Column(
            "actor_type", sa.String(length=20), nullable=False
        ),  # 'user', 'admin', 'system', 'webhook'
        sa.Column(
            "actor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column(
            "actor_email", sa.String(length=255), nullable=True
        ),  # Denormalized for audit trail
        # Change Details
        sa.Column("old_values", JSONB, nullable=True),  # Previous state (for updates)
        sa.Column("new_values", JSONB, nullable=True),  # New state
        sa.Column("changes_summary", sa.Text(), nullable=True),  # Human-readable summary
        # Security Events
        sa.Column(
            "severity", sa.String(length=20), nullable=False, server_default="info"
        ),  # 'info', 'warning', 'error', 'critical'
        sa.Column("is_security_event", sa.Boolean(), nullable=False, server_default="false"),
        # Request Context
        sa.Column("ip_address", sa.String(length=45), nullable=True),  # IPv6 compatible
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("request_id", sa.String(length=100), nullable=True),
        # Metadata
        sa.Column("metadata", JSONB, nullable=True),  # Additional context
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("NOW()")),
        # Constraints
        sa.CheckConstraint(
            "actor_type IN ('user', 'admin', 'system', 'webhook')",
            name="ck_audit_log_actor_type_valid",
        ),
        sa.CheckConstraint(
            "severity IN ('info', 'warning', 'error', 'critical')",
            name="ck_audit_log_severity_valid",
        ),
    )

    # ========================================
    # 2. CREATE INDEXES FOR EFFICIENT QUERYING
    # ========================================

    # Composite index for entity lookups (most common query pattern)
    op.create_index("idx_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])

    # Index for actor queries
    op.create_index("idx_audit_logs_actor_id", "audit_logs", ["actor_id"])

    # Index for time-based queries (descending for recent-first queries)
    op.create_index("idx_audit_logs_created_at", "audit_logs", [sa.text("created_at DESC")])

    # Partial index for security events only (efficient security monitoring)
    op.execute("""
        CREATE INDEX idx_audit_logs_security_events
        ON audit_logs (is_security_event, severity, created_at DESC)
        WHERE is_security_event = true;
    """)

    # Index for action type queries
    op.create_index("idx_audit_logs_action", "audit_logs", ["action"])

    # Composite index for actor type and time (admin activity monitoring)
    op.create_index(
        "idx_audit_logs_actor_type_time", "audit_logs", ["actor_type", sa.text("created_at DESC")]
    )

    # Index for request ID (debugging and tracing)
    op.create_index("idx_audit_logs_request_id", "audit_logs", ["request_id"])

    # ========================================
    # 3. CREATE RULES TO PREVENT UPDATES/DELETES
    # ========================================
    # This makes the audit log immutable - records can only be inserted, never modified or deleted

    op.execute("""
        CREATE RULE audit_logs_no_update AS
        ON UPDATE TO audit_logs
        DO INSTEAD NOTHING;
    """)

    op.execute("""
        CREATE RULE audit_logs_no_delete AS
        ON DELETE TO audit_logs
        DO INSTEAD NOTHING;
    """)

    # ========================================
    # 4. ADD TRIGGER FOR UPDATED_AT (if needed in future)
    # ========================================
    # Note: Since audit logs are immutable, we don't need updated_at
    # But keeping this pattern for consistency if business requirements change

    # Create function for updating timestamps (reusable)
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)


def downgrade():
    """
    Remove audit logging system.

    WARNING: This will delete all audit log data. Use with extreme caution.
    Only run in development/staging environments.
    """

    # Drop rules first
    op.execute("DROP RULE IF EXISTS audit_logs_no_delete ON audit_logs;")
    op.execute("DROP RULE IF EXISTS audit_logs_no_update ON audit_logs;")

    # Drop indexes
    op.drop_index("idx_audit_logs_request_id", "audit_logs")
    op.drop_index("idx_audit_logs_actor_type_time", "audit_logs")
    op.drop_index("idx_audit_logs_action", "audit_logs")
    op.execute("DROP INDEX IF EXISTS idx_audit_logs_security_events;")  # Partial index
    op.drop_index("idx_audit_logs_created_at", "audit_logs")
    op.drop_index("idx_audit_logs_actor_id", "audit_logs")
    op.drop_index("idx_audit_logs_entity", "audit_logs")

    # Drop table
    op.drop_table("audit_logs")

    # Drop function (if not used elsewhere)
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")
