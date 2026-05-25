"""add_shiprocket_integration

Revision ID: 20260502_shiprocket
Revises: 0d45922d16b5
Create Date: 2026-05-02 02:30:00.000000

This migration:
1. Renames user_goodies table to user_rewards
2. Updates all enum types and columns
3. Adds new Shiprocket tracking fields
4. Creates shiprocket_orders table
5. Creates shiprocket_config table
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260502_shiprocket"
down_revision: str | None = "0d45922d16b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Upgrade database schema for Shiprocket integration.
    """

    # Step 1: Create new enum types for rewards (only if they don't exist)
    op.execute(
        "DO $$ BEGIN CREATE TYPE rewardstatus AS ENUM ('pending_details', 'pending_shipment', 'label_generated', 'pickup_scheduled', 'shipped', 'in_transit', 'out_for_delivery', 'delivered', 'cancelled', 'rto_initiated', 'rto_delivered'); EXCEPTION WHEN duplicate_object THEN null; END $$;"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE rewardtype AS ENUM ('medal', 'tshirt', 'certificate', 'trophy', 'custom'); EXCEPTION WHEN duplicate_object THEN null; END $$;"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE shiprocketorderstatus AS ENUM ('pending', 'created', 'label_generated', 'pickup_scheduled', 'manifested', 'failed'); EXCEPTION WHEN duplicate_object THEN null; END $$;"
    )

    # Step 2: Rename user_goodies table to user_rewards
    op.rename_table("user_goodies", "user_rewards")

    # Step 3: Update columns in user_rewards table

    # Rename columns
    op.alter_column("user_rewards", "challenge_id", new_column_name="event_id")
    op.alter_column("user_rewards", "goodie_id", new_column_name="reward_id")
    op.alter_column("user_rewards", "goodie_name", new_column_name="reward_name")
    op.alter_column("user_rewards", "goodie_description", new_column_name="reward_description")
    op.alter_column("user_rewards", "goodie_type", new_column_name="reward_type")
    op.alter_column("user_rewards", "goodie_image_url", new_column_name="reward_image_url")

    # Add registration_id column
    op.add_column("user_rewards", sa.Column("registration_id", sa.Integer(), nullable=True))
    op.create_index(
        op.f("ix_user_rewards_registration_id"), "user_rewards", ["registration_id"], unique=False
    )
    op.create_foreign_key(
        "fk_user_rewards_registration_id",
        "user_rewards",
        "registrations",
        ["registration_id"],
        ["id"],
    )

    # Convert boolean enums to proper Boolean type
    # First, add temporary boolean columns
    op.add_column("user_rewards", sa.Column("requires_shipping_temp", sa.Boolean(), nullable=True))
    op.add_column("user_rewards", sa.Column("is_unlocked_temp", sa.Boolean(), nullable=True))
    op.add_column("user_rewards", sa.Column("is_verified_temp", sa.Boolean(), nullable=True))

    # Copy data with conversion
    op.execute("""
        UPDATE user_rewards
        SET requires_shipping_temp = CASE WHEN requires_shipping::text = 'true' THEN TRUE ELSE FALSE END,
            is_unlocked_temp = CASE WHEN is_unlocked::text = 'true' THEN TRUE ELSE FALSE END,
            is_verified_temp = CASE WHEN is_verified::text = 'true' THEN TRUE ELSE FALSE END
    """)

    # Drop old enum columns
    op.drop_column("user_rewards", "requires_shipping")
    op.drop_column("user_rewards", "is_unlocked")
    op.drop_column("user_rewards", "is_verified")

    # Rename temp columns to original names
    op.alter_column("user_rewards", "requires_shipping_temp", new_column_name="requires_shipping")
    op.alter_column("user_rewards", "is_unlocked_temp", new_column_name="is_unlocked")
    op.alter_column("user_rewards", "is_verified_temp", new_column_name="is_verified")

    # Set defaults and not null
    op.alter_column("user_rewards", "requires_shipping", server_default="true")
    op.alter_column("user_rewards", "is_unlocked", server_default="false")
    op.alter_column("user_rewards", "is_verified", server_default="false")

    # Update status column to use new enum
    op.execute(
        "ALTER TABLE user_rewards ALTER COLUMN status TYPE rewardstatus USING status::text::rewardstatus"
    )
    op.execute(
        "ALTER TABLE user_rewards ALTER COLUMN reward_type TYPE rewardtype USING reward_type::text::rewardtype"
    )

    # Step 4: Add new Shiprocket tracking fields
    op.add_column(
        "user_rewards", sa.Column("item_weight", sa.Numeric(precision=10, scale=2), nullable=True)
    )
    op.add_column(
        "user_rewards", sa.Column("item_length", sa.Numeric(precision=10, scale=2), nullable=True)
    )
    op.add_column(
        "user_rewards", sa.Column("item_breadth", sa.Numeric(precision=10, scale=2), nullable=True)
    )
    op.add_column(
        "user_rewards", sa.Column("item_height", sa.Numeric(precision=10, scale=2), nullable=True)
    )
    op.add_column("user_rewards", sa.Column("item_sku", sa.String(length=100), nullable=True))
    op.add_column("user_rewards", sa.Column("item_hsn", sa.String(length=50), nullable=True))

    # Update shiprocket fields to use String instead of Integer
    op.alter_column("user_rewards", "shiprocket_order_id", type_=sa.String(100))
    op.alter_column("user_rewards", "shiprocket_shipment_id", type_=sa.String(100))

    op.add_column("user_rewards", sa.Column("shiprocket_awb", sa.String(length=100), nullable=True))
    op.add_column("user_rewards", sa.Column("shiprocket_status_code", sa.Integer(), nullable=True))
    op.add_column("user_rewards", sa.Column("tracking_url", sa.String(length=500), nullable=True))
    op.add_column(
        "user_rewards", sa.Column("current_location", sa.String(length=200), nullable=True)
    )
    op.add_column(
        "user_rewards", sa.Column("last_tracking_update", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("user_rewards", sa.Column("pickup_scheduled_date", sa.Date(), nullable=True))
    op.add_column("user_rewards", sa.Column("actual_delivery_date", sa.Date(), nullable=True))
    op.add_column(
        "user_rewards",
        sa.Column("status_history", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column("user_rewards", sa.Column("fulfillment_error", sa.Text(), nullable=True))

    # Update estimated_delivery_date from DateTime to Date
    op.alter_column("user_rewards", "estimated_delivery_date", type_=sa.Date())

    # Create indexes for new fields
    op.create_index(
        op.f("ix_user_rewards_shiprocket_awb"), "user_rewards", ["shiprocket_awb"], unique=False
    )

    # Step 5: Create shiprocket_orders table
    op.execute("""
        CREATE TABLE shiprocket_orders (
            id SERIAL PRIMARY KEY,
            user_reward_id UUID NOT NULL,
            event_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            shiprocket_order_id VARCHAR(100),
            shiprocket_shipment_id VARCHAR(100),
            shiprocket_awb VARCHAR(100),
            order_reference VARCHAR(200) NOT NULL,
            courier_id INTEGER,
            courier_name VARCHAR(100),
            status shiprocketorderstatus NOT NULL DEFAULT 'pending',
            label_url VARCHAR(500),
            manifest_url VARCHAR(500),
            tracking_url VARCHAR(500),
            pickup_location VARCHAR(200),
            pickup_scheduled_date DATE,
            pickup_token_number VARCHAR(100),
            shiprocket_request JSONB,
            shiprocket_response JSONB,
            error_message TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            order_sent_at TIMESTAMP WITH TIME ZONE,
            label_generated_at TIMESTAMP WITH TIME ZONE,
            pickup_scheduled_at TIMESTAMP WITH TIME ZONE,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            FOREIGN KEY (event_id) REFERENCES events(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (user_reward_id) REFERENCES user_rewards(id)
        )
    """)
    op.create_index(
        op.f("ix_shiprocket_orders_event_id"), "shiprocket_orders", ["event_id"], unique=False
    )
    op.create_index(
        op.f("ix_shiprocket_orders_order_reference"),
        "shiprocket_orders",
        ["order_reference"],
        unique=True,
    )
    op.create_index(
        op.f("ix_shiprocket_orders_shiprocket_awb"),
        "shiprocket_orders",
        ["shiprocket_awb"],
        unique=False,
    )
    op.create_index(
        op.f("ix_shiprocket_orders_shiprocket_order_id"),
        "shiprocket_orders",
        ["shiprocket_order_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_shiprocket_orders_shiprocket_shipment_id"),
        "shiprocket_orders",
        ["shiprocket_shipment_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_shiprocket_orders_status"), "shiprocket_orders", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_shiprocket_orders_user_id"), "shiprocket_orders", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_shiprocket_orders_user_reward_id"),
        "shiprocket_orders",
        ["user_reward_id"],
        unique=True,
    )

    # Step 6: Create shiprocket_config table
    op.create_table(
        "shiprocket_config",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("encrypted_password", sa.Text(), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "default_pickup_location",
            sa.String(length=200),
            nullable=False,
            server_default="Primary",
        ),
        sa.Column(
            "default_length",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default="15.0",
        ),
        sa.Column(
            "default_breadth",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default="15.0",
        ),
        sa.Column(
            "default_height",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default="10.0",
        ),
        sa.Column(
            "default_weight",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default="0.5",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("auto_schedule_pickup", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("auto_generate_label", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("webhook_url", sa.String(length=500), nullable=True),
        sa.Column("webhook_secret", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Drop old enum types that are no longer needed
    op.execute("DROP TYPE IF EXISTS goodiestatus CASCADE")
    op.execute("DROP TYPE IF EXISTS goodietype CASCADE")
    op.execute("DROP TYPE IF EXISTS boolean_enum CASCADE")
    op.execute("DROP TYPE IF EXISTS boolean_enum_unlocked CASCADE")
    op.execute("DROP TYPE IF EXISTS boolean_enum_verified CASCADE")


def downgrade() -> None:
    """
    Downgrade database schema (revert Shiprocket integration).
    """

    # Drop new tables
    op.drop_table("shiprocket_config")
    op.drop_index(op.f("ix_shiprocket_orders_user_reward_id"), table_name="shiprocket_orders")
    op.drop_index(op.f("ix_shiprocket_orders_user_id"), table_name="shiprocket_orders")
    op.drop_index(op.f("ix_shiprocket_orders_status"), table_name="shiprocket_orders")
    op.drop_index(
        op.f("ix_shiprocket_orders_shiprocket_shipment_id"), table_name="shiprocket_orders"
    )
    op.drop_index(op.f("ix_shiprocket_orders_shiprocket_order_id"), table_name="shiprocket_orders")
    op.drop_index(op.f("ix_shiprocket_orders_shiprocket_awb"), table_name="shiprocket_orders")
    op.drop_index(op.f("ix_shiprocket_orders_order_reference"), table_name="shiprocket_orders")
    op.drop_index(op.f("ix_shiprocket_orders_event_id"), table_name="shiprocket_orders")
    op.drop_table("shiprocket_orders")

    # Remove new columns from user_rewards
    op.drop_column("user_rewards", "fulfillment_error")
    op.drop_column("user_rewards", "status_history")
    op.drop_column("user_rewards", "actual_delivery_date")
    op.drop_column("user_rewards", "pickup_scheduled_date")
    op.drop_column("user_rewards", "last_tracking_update")
    op.drop_column("user_rewards", "current_location")
    op.drop_column("user_rewards", "tracking_url")
    op.drop_column("user_rewards", "shiprocket_status_code")
    op.drop_column("user_rewards", "shiprocket_awb")
    op.drop_column("user_rewards", "item_hsn")
    op.drop_column("user_rewards", "item_sku")
    op.drop_column("user_rewards", "item_height")
    op.drop_column("user_rewards", "item_breadth")
    op.drop_column("user_rewards", "item_length")
    op.drop_column("user_rewards", "item_weight")

    # Revert shiprocket_order_id and shiprocket_shipment_id back to Integer
    op.alter_column("user_rewards", "shiprocket_order_id", type_=sa.Integer())
    op.alter_column("user_rewards", "shiprocket_shipment_id", type_=sa.Integer())

    # Remove registration_id
    op.drop_constraint("fk_user_rewards_registration_id", "user_rewards", type_="foreignkey")
    op.drop_index(op.f("ix_user_rewards_registration_id"), table_name="user_rewards")
    op.drop_column("user_rewards", "registration_id")

    # Recreate old enum types
    op.execute(
        "CREATE TYPE goodiestatus AS ENUM ('pending_details', 'pending_shipment', 'shipped', 'delivered', 'cancelled')"
    )
    op.execute(
        "CREATE TYPE goodietype AS ENUM ('medal', 'tshirt', 'certificate', 'trophy', 'custom')"
    )
    op.execute("CREATE TYPE boolean_enum AS ENUM ('true', 'false')")
    op.execute("CREATE TYPE boolean_enum_unlocked AS ENUM ('true', 'false')")
    op.execute("CREATE TYPE boolean_enum_verified AS ENUM ('true', 'false')")

    # Revert column types and names
    op.alter_column(
        "user_rewards",
        "reward_type",
        new_column_name="goodie_type",
        type_=sa.Enum("medal", "tshirt", "certificate", "trophy", "custom", name="goodietype"),
    )
    op.alter_column("user_rewards", "reward_image_url", new_column_name="goodie_image_url")
    op.alter_column("user_rewards", "reward_description", new_column_name="goodie_description")
    op.alter_column("user_rewards", "reward_name", new_column_name="goodie_name")
    op.alter_column("user_rewards", "reward_id", new_column_name="goodie_id")
    op.alter_column("user_rewards", "event_id", new_column_name="challenge_id")

    # Revert boolean columns back to enum
    op.add_column(
        "user_rewards",
        sa.Column(
            "requires_shipping_enum", sa.Enum("true", "false", name="boolean_enum"), nullable=True
        ),
    )
    op.add_column(
        "user_rewards",
        sa.Column(
            "is_unlocked_enum",
            sa.Enum("true", "false", name="boolean_enum_unlocked"),
            nullable=True,
        ),
    )
    op.add_column(
        "user_rewards",
        sa.Column(
            "is_verified_enum",
            sa.Enum("true", "false", name="boolean_enum_verified"),
            nullable=True,
        ),
    )

    op.execute("""
        UPDATE user_rewards
        SET requires_shipping_enum = CASE WHEN requires_shipping THEN 'true'::boolean_enum ELSE 'false'::boolean_enum END,
            is_unlocked_enum = CASE WHEN is_unlocked THEN 'true'::boolean_enum_unlocked ELSE 'false'::boolean_enum_unlocked END,
            is_verified_enum = CASE WHEN is_verified THEN 'true'::boolean_enum_verified ELSE 'false'::boolean_enum_verified END
    """)

    op.drop_column("user_rewards", "requires_shipping")
    op.drop_column("user_rewards", "is_unlocked")
    op.drop_column("user_rewards", "is_verified")

    op.alter_column("user_rewards", "requires_shipping_enum", new_column_name="requires_shipping")
    op.alter_column("user_rewards", "is_unlocked_enum", new_column_name="is_unlocked")
    op.alter_column("user_rewards", "is_verified_enum", new_column_name="is_verified")

    # Revert status column
    op.execute(
        "ALTER TABLE user_rewards ALTER COLUMN status TYPE goodiestatus USING status::text::goodiestatus"
    )

    # Rename table back
    op.rename_table("user_rewards", "user_goodies")

    # Drop new enum types
    op.execute("DROP TYPE IF EXISTS shiprocketorderstatus CASCADE")
    op.execute("DROP TYPE IF EXISTS rewardtype CASCADE")
    op.execute("DROP TYPE IF EXISTS rewardstatus CASCADE")
