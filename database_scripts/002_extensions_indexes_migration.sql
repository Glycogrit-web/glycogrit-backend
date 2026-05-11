-- GlycoGrit Database - Extensions & Indexes Migration
-- Version: 1.1.0
-- Description: Add performance indexes and column migrations for installed extensions
-- Prerequisites: Extensions already installed (pg_trgm, pg_stat_statements, uuid-ossp, btree_gin, pgcrypto, hstore, citext, earthdistance, cube, unaccent)
--
-- IMPORTANT: This script uses CREATE INDEX CONCURRENTLY to avoid locking tables
-- CONCURRENTLY cannot run inside a transaction block, so run this script outside of transactions
--
-- Run with: psql -U your_user -d your_database -f 002_extensions_indexes_migration.sql

-- ====================
-- STEP 1: VERIFY EXTENSIONS ARE INSTALLED
-- ====================

DO $$
DECLARE
    missing_extensions TEXT[];
BEGIN
    SELECT ARRAY_AGG(ext) INTO missing_extensions
    FROM (VALUES
        ('pg_trgm'),
        ('pg_stat_statements'),
        ('uuid-ossp'),
        ('btree_gin'),
        ('pgcrypto'),
        ('citext')
    ) AS required(ext)
    WHERE NOT EXISTS (
        SELECT 1 FROM pg_extension WHERE extname = required.ext
    );

    IF missing_extensions IS NOT NULL THEN
        RAISE EXCEPTION 'Missing extensions: %. Please install them first.', missing_extensions;
    END IF;

    RAISE NOTICE 'All required extensions are installed ✓';
END $$;

-- ====================
-- STEP 2: ADD TRIGRAM INDEXES FOR TEXT SEARCH
-- ====================

-- User search indexes (for rewards.py user search and general user lookup)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_first_name_trgm
ON users USING gin(first_name gin_trgm_ops);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_last_name_trgm
ON users USING gin(last_name gin_trgm_ops);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email_trgm
ON users USING gin(email gin_trgm_ops);

-- Event search indexes (for homepage search, event discovery)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_events_name_trgm
ON events USING gin(name gin_trgm_ops);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_events_location_name_trgm
ON events USING gin(location_name gin_trgm_ops);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_events_city_trgm
ON events USING gin(city gin_trgm_ops);

-- Registration search (for admin searching registrations by participant name)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_registrations_participant_name_trgm
ON registrations USING gin(participant_name gin_trgm_ops);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_registrations_bib_number_trgm
ON registrations USING gin(bib_number gin_trgm_ops);

-- ====================
-- STEP 3: ADD COMPOSITE INDEXES FOR COMMON QUERIES
-- ====================

-- Critical: challenges.py queries (user's challenges, progress lookups)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_registrations_user_event_status
ON registrations(user_id, event_id, status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_registrations_event_status
ON registrations(event_id, status);

-- Activity progress indexes (leaderboards, challenge tracking)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_activity_progress_event_distance
ON activity_progress(event_id, distance_completed DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_activity_progress_reg_user
ON activity_progress(registration_id, user_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_activity_progress_user_event
ON activity_progress(user_id, event_id);

-- User rewards (rewards.py filtering and sorting)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_rewards_type_awarded
ON user_rewards(reward_type, awarded_at DESC)
WHERE reward_type IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_rewards_user_awarded
ON user_rewards(user_id, awarded_at DESC);

-- Event filtering (homepage, event listing by status + date)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_events_status_date
ON events(status, event_date)
WHERE status IN ('published', 'registration_open');

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_events_is_virtual_status
ON events(is_virtual, status, event_date);

-- Payment queries (user payment history, transaction lookup)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_payments_user_status
ON payments(user_id, status, created_at DESC);

-- ====================
-- STEP 4: ADD JSONB INDEXES (using btree_gin)
-- ====================

-- Events with JSONB columns (prize_details, category_support)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_events_prize_details_gin
ON events USING gin(prize_details jsonb_path_ops);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_events_category_support_gin
ON events USING gin(category_support jsonb_path_ops);

-- Event results splits (checkpoint timings)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_event_results_splits_gin
ON event_results USING gin(splits jsonb_path_ops);

-- Activity progress distance tracking by source
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_activity_progress_distance_by_source_gin
ON activity_progress USING gin(distance_by_source jsonb_path_ops);

-- ====================
-- STEP 5: MIGRATE EMAIL COLUMN TO CITEXT (Case-insensitive)
-- ====================

-- WARNING: This step modifies the column type. Test in staging first!
-- This allows case-insensitive comparisons without LOWER()

-- Users email
ALTER TABLE users ALTER COLUMN email TYPE citext;

-- Events organizer contact email
ALTER TABLE events ALTER COLUMN organizer_contact_email TYPE citext;

-- ====================
-- STEP 6: ADD GEOSPATIAL INDEXES (if earthdistance/cube installed)
-- ====================

-- Only create if extensions are available
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'cube')
       AND EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'earthdistance') THEN

        -- Index for finding nearby events
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_events_lat_long
        ON events(latitude, longitude)
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL;

        -- Index for checkpoint locations
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_checkpoints_lat_long
        ON event_checkpoints(latitude, longitude)
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL;

        RAISE NOTICE 'Geospatial indexes created ✓';
    ELSE
        RAISE NOTICE 'Skipping geospatial indexes (earthdistance/cube not installed)';
    END IF;
END $$;

-- ====================
-- STEP 7: ADD INDEXES FOR FITNESS TRACKER CONNECTIONS
-- ====================

-- Strava connection lookup
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_strava_connection_user
ON strava_connections(user_id)
WHERE is_active = true;

-- Garmin connection lookup
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_garmin_connection_user
ON garmin_connections(user_id)
WHERE is_active = true;

-- Fitbit connection lookup
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fitbit_connection_user
ON fitbit_connections(user_id)
WHERE is_active = true;

-- Wahoo connection lookup
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_wahoo_connection_user
ON wahoo_connections(user_id)
WHERE is_active = true;

-- User activity logs (for syncing and stats)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_activity_logs_user_date
ON user_activity_logs(user_id, activity_date DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_activity_logs_event_date
ON user_activity_logs(event_id, activity_date DESC);

-- ====================
-- STEP 8: ADD INDEXES FOR CERTIFICATES
-- ====================

-- Certificate verification (public verification by code)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_certificates_verification_code
ON certificates(verification_code)
WHERE is_verified = true;

-- User certificates lookup
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_certificates_user_issued
ON certificates(user_id, issued_at DESC);

-- ====================
-- STEP 9: ANALYZE TABLES AFTER INDEX CREATION
-- ====================

-- Update statistics so PostgreSQL can use new indexes effectively
ANALYZE users;
ANALYZE events;
ANALYZE registrations;
ANALYZE activity_progress;
ANALYZE user_rewards;
ANALYZE payments;
ANALYZE event_results;
ANALYZE user_activity_logs;
ANALYZE certificates;
ANALYZE strava_connections;
ANALYZE garmin_connections;
ANALYZE fitbit_connections;
ANALYZE wahoo_connections;

-- ====================
-- STEP 10: VERIFICATION QUERIES
-- ====================

-- List all new indexes created
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND (
      indexname LIKE '%_trgm%'
      OR indexname LIKE '%_gin%'
      OR indexname LIKE '%_lat_long%'
      OR indexname ~ 'idx_(registrations|activity_progress|user_rewards|payments)_'
  )
ORDER BY tablename, indexname;

-- Check index usage (run this after a few days of production traffic)
-- SELECT
--     schemaname,
--     tablename,
--     indexname,
--     idx_scan AS scans,
--     idx_tup_read AS tuples_read,
--     idx_tup_fetch AS tuples_fetched,
--     pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
-- FROM pg_stat_user_indexes
-- WHERE schemaname = 'public'
-- ORDER BY idx_scan DESC;

-- ====================
-- COMPLETION MESSAGE
-- ====================

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Migration completed successfully! ✓';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '1. Test queries in staging environment';
    RAISE NOTICE '2. Monitor pg_stat_statements for slow queries';
    RAISE NOTICE '3. Check index usage after 24-48 hours';
    RAISE NOTICE '========================================';
END $$;
