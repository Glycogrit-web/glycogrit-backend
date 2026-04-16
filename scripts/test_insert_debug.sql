-- Debug script to understand why inserts are failing
-- Run this step by step in Railway console

-- Step 1: Check current events and their slugs
SELECT id, slug, name, organizer_id FROM events ORDER BY id;

-- Step 2: Check if we have any users (for organizer_id)
SELECT id, email, first_name, last_name FROM users LIMIT 5;

-- Step 3: Try inserting ONE event WITHOUT the ON CONFLICT clause
-- This will show us the actual error
INSERT INTO events (
    name, slug, description, event_type, status,
    start_date, end_date, event_date, registration_start_date, registration_end_date,
    location, location_name, city, state, country,
    total_distance, max_participants, current_participants,
    registration_fee, currency, difficulty_level, goals, rewards, rules,
    is_virtual, is_featured, organizer_id,
    created_at, updated_at
) VALUES (
    'Test Event Debug',
    'test-event-debug-' || EXTRACT(EPOCH FROM NOW())::TEXT,  -- Unique slug
    'Test description to debug insertion',
    'running',
    'registration_open',
    CURRENT_DATE,
    CURRENT_DATE + INTERVAL '7 days',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP + INTERVAL '14 days',
    'Virtual',
    'Virtual',
    'Online',
    'Virtual',
    'India',
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
    1,  -- Using organizer_id = 1
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- Step 4: Check if it was inserted
SELECT COUNT(*) as total FROM events;
SELECT id, name, slug FROM events ORDER BY created_at DESC LIMIT 3;
