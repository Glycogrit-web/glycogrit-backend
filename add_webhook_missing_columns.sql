-- Add missing columns to webhook_events table
-- This migration fixes the schema mismatch between the WebhookEvent model and database

-- Add missing columns
ALTER TABLE webhook_events
  ADD COLUMN IF NOT EXISTS source VARCHAR(50),
  ADD COLUMN IF NOT EXISTS headers TEXT,
  ADD COLUMN IF NOT EXISTS signature_verified BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS received_at TIMESTAMP WITHOUT TIME ZONE,
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITHOUT TIME ZONE;

-- Create enum type for webhook source
DO $$ BEGIN
  CREATE TYPE webhook_source AS ENUM (
    'razorpay',
    'shiprocket',
    'strava',
    'garmin',
    'fitbit',
    'google_fit'
  );
EXCEPTION
  WHEN duplicate_object THEN null;
END $$;

-- Set default value for existing rows before converting to enum
UPDATE webhook_events SET source = 'razorpay' WHERE source IS NULL;

-- Convert source column to enum type
ALTER TABLE webhook_events
  ALTER COLUMN source TYPE webhook_source USING source::webhook_source,
  ALTER COLUMN source SET NOT NULL;

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS ix_webhook_events_source ON webhook_events(source);
CREATE INDEX IF NOT EXISTS ix_webhook_events_received_at ON webhook_events(received_at);

-- Set timestamps for existing rows
UPDATE webhook_events
SET received_at = created_at WHERE received_at IS NULL;

UPDATE webhook_events
SET updated_at = created_at WHERE updated_at IS NULL;

-- Add NOT NULL constraints after populating data
ALTER TABLE webhook_events
  ALTER COLUMN received_at SET NOT NULL;

-- Verification: Show final schema
\d webhook_events
