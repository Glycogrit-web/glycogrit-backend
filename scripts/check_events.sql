-- Diagnostic queries to check what's happening

-- 1. Check total events
SELECT COUNT(*) as total_events FROM events;

-- 2. Check all event slugs
SELECT id, name, slug FROM events ORDER BY created_at DESC;

-- 3. Check if slug column has UNIQUE constraint
SELECT
    tc.constraint_name,
    tc.constraint_type,
    kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
WHERE tc.table_name = 'events'
    AND kcu.column_name = 'slug';

-- 4. Test inserting one event manually (without ON CONFLICT)
INSERT INTO events (
    name, slug, description, event_type, status,
    start_date, end_date, location, total_distance,
    max_participants, current_participants, registration_fee,
    currency, difficulty_level, goals, rewards, rules,
    is_virtual, is_featured, created_at, updated_at
) VALUES (
    'Test Event',
    'test-event-' || EXTRACT(EPOCH FROM NOW())::TEXT,
    'Test description',
    'running',
    'registration_open',
    CURRENT_DATE,
    CURRENT_DATE + INTERVAL '7 days',
    'Test Location',
    10.0,
    100,
    0,
    0.0,
    'INR',
    'beginner',
    '["Test goal"]'::jsonb,
    '["Test reward"]'::jsonb,
    'Test rules',
    true,
    false,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
) RETURNING id, name, slug;
