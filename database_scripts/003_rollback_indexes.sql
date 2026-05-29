-- GlycoGrit Database - Rollback Indexes Migration
-- Version: 1.1.0
-- Description: Rollback script to remove indexes if needed (e.g., if they cause issues)
--
-- WARNING: Only run this if you need to rollback the index creation
-- This will NOT rollback the citext column type change (you need a separate migration for that)

-- ====================
-- DROP TRIGRAM INDEXES
-- ====================

DROP INDEX CONCURRENTLY IF EXISTS idx_users_first_name_trgm;
DROP INDEX CONCURRENTLY IF EXISTS idx_users_last_name_trgm;
DROP INDEX CONCURRENTLY IF EXISTS idx_users_email_trgm;
DROP INDEX CONCURRENTLY IF EXISTS idx_events_name_trgm;
DROP INDEX CONCURRENTLY IF EXISTS idx_events_location_name_trgm;
DROP INDEX CONCURRENTLY IF EXISTS idx_events_city_trgm;
DROP INDEX CONCURRENTLY IF EXISTS idx_registrations_participant_name_trgm;
DROP INDEX CONCURRENTLY IF EXISTS idx_registrations_bib_number_trgm;

-- ====================
-- DROP COMPOSITE INDEXES
-- ====================

DROP INDEX CONCURRENTLY IF EXISTS idx_registrations_user_event_status;
DROP INDEX CONCURRENTLY IF EXISTS idx_registrations_event_status;
DROP INDEX CONCURRENTLY IF EXISTS idx_activity_progress_event_distance;
DROP INDEX CONCURRENTLY IF EXISTS idx_activity_progress_reg_user;
DROP INDEX CONCURRENTLY IF EXISTS idx_activity_progress_user_event;
DROP INDEX CONCURRENTLY IF EXISTS idx_user_rewards_type_awarded;
DROP INDEX CONCURRENTLY IF EXISTS idx_user_rewards_user_awarded;
DROP INDEX CONCURRENTLY IF EXISTS idx_events_status_date;
DROP INDEX CONCURRENTLY IF EXISTS idx_events_is_virtual_status;
DROP INDEX CONCURRENTLY IF EXISTS idx_payments_user_status;

-- ====================
-- DROP JSONB INDEXES
-- ====================

DROP INDEX CONCURRENTLY IF EXISTS idx_events_prize_details_gin;
DROP INDEX CONCURRENTLY IF EXISTS idx_events_category_support_gin;
DROP INDEX CONCURRENTLY IF EXISTS idx_event_results_splits_gin;
DROP INDEX CONCURRENTLY IF EXISTS idx_activity_progress_distance_by_source_gin;

-- ====================
-- DROP GEOSPATIAL INDEXES
-- ====================

DROP INDEX CONCURRENTLY IF EXISTS idx_events_lat_long;
DROP INDEX CONCURRENTLY IF EXISTS idx_checkpoints_lat_long;

-- ====================
-- DROP FITNESS TRACKER INDEXES
-- ====================

DROP INDEX CONCURRENTLY IF EXISTS idx_strava_connection_user;
DROP INDEX CONCURRENTLY IF EXISTS idx_fitbit_connection_user;
DROP INDEX CONCURRENTLY IF EXISTS idx_user_activity_logs_user_date;
DROP INDEX CONCURRENTLY IF EXISTS idx_user_activity_logs_event_date;

-- ====================
-- DROP CERTIFICATE INDEXES
-- ====================

DROP INDEX CONCURRENTLY IF EXISTS idx_certificates_verification_code;
DROP INDEX CONCURRENTLY IF EXISTS idx_certificates_user_issued;

-- ====================
-- ROLLBACK CITEXT (if needed - run separately)
-- ====================

-- Uncomment these lines if you need to rollback the citext migration
-- WARNING: This requires testing in staging first

-- ALTER TABLE users ALTER COLUMN email TYPE VARCHAR(255);
-- ALTER TABLE events ALTER COLUMN organizer_contact_email TYPE VARCHAR(255);

-- ====================
-- VERIFICATION
-- ====================

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Rollback completed';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'All indexes have been dropped.';
    RAISE NOTICE 'Note: citext columns were NOT reverted (uncomment lines if needed)';
    RAISE NOTICE '========================================';
END $$;
