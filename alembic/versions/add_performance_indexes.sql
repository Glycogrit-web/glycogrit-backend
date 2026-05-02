-- Performance Indexes for Shiprocket Integration
-- Run these manually or create an Alembic migration

-- Indexes on user_rewards table
CREATE INDEX IF NOT EXISTS idx_user_rewards_status
    ON user_rewards(status);

CREATE INDEX IF NOT EXISTS idx_user_rewards_user_event
    ON user_rewards(user_id, event_id);

CREATE INDEX IF NOT EXISTS idx_user_rewards_tracking_number
    ON user_rewards(tracking_number)
    WHERE tracking_number IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_user_rewards_requires_shipping
    ON user_rewards(requires_shipping, status)
    WHERE requires_shipping = TRUE;

CREATE INDEX IF NOT EXISTS idx_user_rewards_last_update
    ON user_rewards(last_tracking_update DESC NULLS LAST)
    WHERE requires_shipping = TRUE;

-- Indexes on shiprocket_orders table
CREATE INDEX IF NOT EXISTS idx_shiprocket_orders_awb
    ON shiprocket_orders(shiprocket_awb)
    WHERE shiprocket_awb IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_shiprocket_orders_shipment_id
    ON shiprocket_orders(shiprocket_shipment_id)
    WHERE shiprocket_shipment_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_shiprocket_orders_status
    ON shiprocket_orders(status);

CREATE INDEX IF NOT EXISTS idx_shiprocket_orders_created
    ON shiprocket_orders(created_at DESC);

-- Index for webhook lookups (common query pattern)
CREATE INDEX IF NOT EXISTS idx_user_rewards_awb_lookup
    ON user_rewards(tracking_number, status)
    WHERE tracking_number IS NOT NULL AND requires_shipping = TRUE;

-- Analyze tables for query planner
ANALYZE user_rewards;
ANALYZE shiprocket_orders;
