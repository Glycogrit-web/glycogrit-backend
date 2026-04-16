-- Insert just ONE sample event to test
-- This will show any errors that might be happening

INSERT INTO events (
    name, slug, description, event_type, status, start_date, end_date,
    location, total_distance, max_participants, current_participants,
    registration_fee, currency, difficulty_level, goals, rewards, rules,
    is_virtual, is_featured, created_at, updated_at
) VALUES (
    '30-Day Running Challenge',
    '30-day-running-challenge',
    'Build your running habit with our 30-day challenge. Run at least 3km every day for 30 days.',
    'running',
    'registration_open',
    CURRENT_DATE,
    CURRENT_DATE + INTERVAL '30 days',
    'Virtual - Anywhere',
    90.0,
    1000,
    0,
    0.0,
    'INR',
    'beginner',
    '["Run 3km daily", "Complete 30 consecutive days", "Build a running habit"]'::jsonb,
    '["Digital certificate", "30-Day Runner badge", "Entry into prize draw"]'::jsonb,
    E'Must log at least 3km run each day\nRest days allowed with prior notification\nActivity must be verified via tracking app',
    true,
    true,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- Verify it was inserted
SELECT id, name, slug, event_type, difficulty_level, is_featured
FROM events
WHERE slug = '30-day-running-challenge';

-- Show total count
SELECT COUNT(*) as total_events FROM events;
