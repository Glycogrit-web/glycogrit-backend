-- Seed Data for GlycoGrit Platform
-- Development and Testing Data

-- ====================
-- USERS
-- ====================

-- Admin User (password: admin123)
INSERT INTO users (email, password_hash, first_name, last_name, role, email_verified, phone, city, state, country)
VALUES ('admin@glycogrit.com', '$2b$12$KIXxkqLQvhBqWkZvQ2zJKuFTzQxQN4p0YrQvZJQzQxQN4p0YrQvZJ', 'Admin', 'User', 'admin', TRUE, '+919876543210', 'Bangalore', 'Karnataka', 'India')
ON CONFLICT (email) DO NOTHING;

-- Event Organizer (password: organizer123)
INSERT INTO users (email, password_hash, first_name, last_name, role, email_verified, phone, city, state, country, bio)
VALUES ('organizer@glycogrit.com', '$2b$12$KIXxkqLQvhBqWkZvQ2zJKuFTzQxQN4p0YrQvZJQzQxQN4p0YrQvZJ', 'Event', 'Organizer', 'organizer', TRUE, '+919876543211', 'Mumbai', 'Maharashtra', 'India', 'Passionate about organizing running events')
ON CONFLICT (email) DO NOTHING;

-- Test Participants (password: test123)
INSERT INTO users (email, password_hash, first_name, last_name, role, email_verified, phone, city, state, country, date_of_birth, gender)
VALUES
    ('john.doe@example.com', '$2b$12$KIXxkqLQvhBqWkZvQ2zJKuFTzQxQN4p0YrQvZJQzQxQN4p0YrQvZJ', 'John', 'Doe', 'participant', TRUE, '+919876543212', 'Delhi', 'Delhi', 'India', '1990-05-15', 'Male'),
    ('jane.smith@example.com', '$2b$12$KIXxkqLQvhBqWkZvQ2zJKuFTzQxQN4p0YrQvZJQzQxQN4p0YrQvZJ', 'Jane', 'Smith', 'participant', TRUE, '+919876543213', 'Pune', 'Maharashtra', 'India', '1992-08-20', 'Female'),
    ('mike.runner@example.com', '$2b$12$KIXxkqLQvhBqWkZvQ2zJKuFTzQxQN4p0YrQvZJQzQxQN4p0YrQvZJ', 'Mike', 'Runner', 'participant', TRUE, '+919876543214', 'Chennai', 'Tamil Nadu', 'India', '1988-03-10', 'Male'),
    ('sarah.cyclist@example.com', '$2b$12$KIXxkqLQvhBqWkZvQ2zJKuFTzQxQN4p0YrQvZJQzQxQN4p0YrQvZJ', 'Sarah', 'Cyclist', 'participant', TRUE, '+919876543215', 'Bangalore', 'Karnataka', 'India', '1995-11-25', 'Female')
ON CONFLICT (email) DO NOTHING;

-- ====================
-- EVENTS
-- ====================

-- Sample Running Event
INSERT INTO events (
    name, slug, description, event_type, status,
    banner_image_url, event_date, registration_start_date, registration_end_date,
    start_time, location_name, country, state, city,
    latitude, longitude, total_distance, max_participants,
    registration_fee, organizer_id, organizer_contact_email,
    is_featured
)
VALUES (
    'Bangalore Marathon 2026',
    'bangalore-marathon-2026',
    'Join us for the annual Bangalore Marathon! Experience the joy of running through the Garden City with thousands of fellow runners. All fitness levels welcome!',
    'marathon',
    'registration_open',
    'https://example.com/banners/bangalore-marathon.jpg',
    '2026-05-15 06:00:00',
    '2026-03-01 00:00:00',
    '2026-05-10 23:59:59',
    '2026-05-15 06:00:00',
    'Cubbon Park',
    'India',
    'Karnataka',
    'Bangalore',
    12.9716, 77.5946,
    42.195,
    5000,
    1200.00,
    (SELECT id FROM users WHERE email = 'organizer@glycogrit.com'),
    'organizer@glycogrit.com',
    TRUE
);

-- Sample 10K Event
INSERT INTO events (
    name, slug, description, event_type, status,
    event_date, registration_start_date, registration_end_date,
    start_time, location_name, country, state, city,
    total_distance, max_participants, registration_fee,
    organizer_id, organizer_contact_email
)
VALUES (
    'Mumbai 10K Run 2026',
    'mumbai-10k-run-2026',
    'A scenic 10K run along Marine Drive. Perfect for beginners and experienced runners alike!',
    '10k',
    'registration_open',
    '2026-06-20 06:30:00',
    '2026-04-01 00:00:00',
    '2026-06-15 23:59:59',
    '2026-06-20 06:30:00',
    'Marine Drive',
    'India',
    'Maharashtra',
    'Mumbai',
    10.0,
    2000,
    600.00,
    (SELECT id FROM users WHERE email = 'organizer@glycogrit.com'),
    'organizer@glycogrit.com'
);

-- Sample Cycling Event
INSERT INTO events (
    name, slug, description, event_type, status,
    event_date, registration_start_date, registration_end_date,
    start_time, location_name, country, state, city,
    total_distance, max_participants, registration_fee,
    organizer_id, is_featured
)
VALUES (
    'Nandi Hills Cycling Challenge',
    'nandi-hills-cycling-2026',
    'Challenge yourself with this scenic cycling route to Nandi Hills. Beautiful views and great company guaranteed!',
    'cycling',
    'published',
    '2026-07-10 05:00:00',
    '2026-05-01 00:00:00',
    '2026-07-05 23:59:59',
    '2026-07-10 05:00:00',
    'Nandi Hills Base',
    'India',
    'Karnataka',
    'Bangalore',
    60.0,
    500,
    800.00,
    (SELECT id FROM users WHERE email = 'organizer@glycogrit.com'),
    TRUE
);

-- ====================
-- EVENT CATEGORIES
-- ====================

-- Categories for Bangalore Marathon
INSERT INTO event_categories (event_id, name, distance, max_participants, registration_fee, min_age, max_age)
VALUES
    ((SELECT id FROM events WHERE slug = 'bangalore-marathon-2026'), 'Full Marathon', 42.195, 2000, 1200.00, 18, NULL),
    ((SELECT id FROM events WHERE slug = 'bangalore-marathon-2026'), 'Half Marathon', 21.0975, 2000, 900.00, 16, NULL),
    ((SELECT id FROM events WHERE slug = 'bangalore-marathon-2026'), '10K Run', 10.0, 1000, 600.00, 14, NULL);

-- Categories for Mumbai 10K
INSERT INTO event_categories (event_id, name, distance, max_participants, registration_fee)
VALUES
    ((SELECT id FROM events WHERE slug = 'mumbai-10k-run-2026'), 'Open 10K', 10.0, 2000, 600.00);

-- ====================
-- SAMPLE REGISTRATIONS
-- ====================

-- Registration for John Doe
INSERT INTO registrations (
    user_id, event_id, event_category_id,
    registration_number, bib_number, status,
    participant_name, age, gender, t_shirt_size,
    emergency_contact_name, emergency_contact_phone
)
VALUES (
    (SELECT id FROM users WHERE email = 'john.doe@example.com'),
    (SELECT id FROM events WHERE slug = 'bangalore-marathon-2026'),
    (SELECT id FROM event_categories WHERE event_id = (SELECT id FROM events WHERE slug = 'bangalore-marathon-2026') AND name = 'Half Marathon'),
    'BAN-000001',
    '0001',
    'payment_completed',
    'John Doe',
    36,
    'Male',
    'L',
    'Emergency Contact',
    '+919999999999'
);

-- Registration for Jane Smith
INSERT INTO registrations (
    user_id, event_id, event_category_id,
    registration_number, bib_number, status,
    participant_name, age, gender, t_shirt_size
)
VALUES (
    (SELECT id FROM users WHERE email = 'jane.smith@example.com'),
    (SELECT id FROM events WHERE slug = 'mumbai-10k-run-2026'),
    (SELECT id FROM event_categories WHERE event_id = (SELECT id FROM events WHERE slug = 'mumbai-10k-run-2026') LIMIT 1),
    'MUM-000001',
    '0001',
    'confirmed',
    'Jane Smith',
    34,
    'Female',
    'M'
);

-- ====================
-- VIRTUAL CHALLENGES
-- ====================

INSERT INTO virtual_challenges (name, description, challenge_type, target_value, start_date, end_date)
VALUES
    ('100K April Challenge', 'Run or walk 100 kilometers during the month of April', 'distance', 100.0, '2026-04-01', '2026-04-30'),
    ('30 Days Running Streak', 'Run at least 1km every day for 30 days', 'streak', 30, '2026-05-01', '2026-05-30'),
    ('Summer Fitness Challenge', 'Complete 50 hours of any fitness activity', 'duration', 50.0, '2026-06-01', '2026-08-31');

-- ====================
-- Update Statistics
-- ====================

-- Update event participant counts
UPDATE events SET current_participants = (
    SELECT COUNT(*) FROM registrations
    WHERE registrations.event_id = events.id
    AND registrations.status IN ('confirmed', 'payment_completed')
);

-- Update category participant counts
UPDATE event_categories SET current_participants = (
    SELECT COUNT(*) FROM registrations
    WHERE registrations.event_category_id = event_categories.id
    AND registrations.status IN ('confirmed', 'payment_completed')
);

-- Success message
SELECT '✅ Seed data inserted successfully!' as message;
