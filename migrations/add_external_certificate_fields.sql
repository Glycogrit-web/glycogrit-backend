-- Add external certificate fields to registrations table
-- For bulk certificate distribution via Google Drive
-- Run this manually if Alembic migrations have issues

-- Add new columns
ALTER TABLE registrations
ADD COLUMN IF NOT EXISTS external_certificate_url TEXT NULL;

ALTER TABLE registrations
ADD COLUMN IF NOT EXISTS external_certificate_unlocked BOOLEAN DEFAULT FALSE NOT NULL;

ALTER TABLE registrations
ADD COLUMN IF NOT EXISTS external_certificate_uploaded_at TIMESTAMP NULL;

ALTER TABLE registrations
ADD COLUMN IF NOT EXISTS external_certificate_uploaded_by INTEGER NULL;

-- Add foreign key constraint for admin who uploaded
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_registrations_external_cert_uploaded_by'
    ) THEN
        ALTER TABLE registrations
        ADD CONSTRAINT fk_registrations_external_cert_uploaded_by
        FOREIGN KEY (external_certificate_uploaded_by)
        REFERENCES users(id)
        ON DELETE SET NULL;
    END IF;
END$$;

-- Add index for faster lookups of unlocked certificates
CREATE INDEX IF NOT EXISTS idx_registrations_external_cert_unlocked
ON registrations(external_certificate_unlocked);

-- Add composite index for event + unlocked status queries
CREATE INDEX IF NOT EXISTS idx_registrations_event_external_cert
ON registrations(event_id, external_certificate_unlocked);

-- Verify changes
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'registrations'
AND column_name LIKE 'external_certificate%'
ORDER BY column_name;
