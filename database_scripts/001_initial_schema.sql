-- GlycoGrit Database Initial Schema
-- Version: 1.0.0
-- Description: Complete database schema for running/fitness events platform

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- For text search

-- ====================
-- ENUM TYPES
-- ====================

CREATE TYPE user_role AS ENUM ('admin', 'organizer', 'participant', 'volunteer');
CREATE TYPE event_type AS ENUM ('running', 'cycling', 'triathlon', 'marathon', 'half_marathon', '5k', '10k', 'virtual');
CREATE TYPE event_status AS ENUM ('draft', 'published', 'registration_open', 'registration_closed', 'ongoing', 'completed', 'cancelled');
CREATE TYPE registration_status AS ENUM ('pending', 'confirmed', 'payment_pending', 'payment_completed', 'cancelled', 'withdrawn');
CREATE TYPE payment_method AS ENUM ('credit_card', 'debit_card', 'upi', 'net_banking', 'wallet', 'bank_transfer');
CREATE TYPE payment_status AS ENUM ('pending', 'completed', 'failed', 'refunded', 'cancelled');
CREATE TYPE result_status AS ENUM ('not_started', 'in_progress', 'finished', 'dnf', 'dns', 'disqualified');

-- ====================
-- USERS TABLE
-- ====================

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    date_of_birth DATE,
    gender VARCHAR(20),
    profile_picture_url VARCHAR(500),
    bio TEXT,
    role user_role DEFAULT 'participant',

    -- Address information
    country VARCHAR(100),
    state VARCHAR(100),
    city VARCHAR(100),
    postal_code VARCHAR(20),
    address VARCHAR(255),

    -- Emergency contact
    emergency_contact_name VARCHAR(100),
    emergency_contact_phone VARCHAR(20),

    -- Health information
    blood_group VARCHAR(10),
    medical_conditions TEXT,
    allergies TEXT,

    -- Account status
    is_active BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT FALSE,
    phone_verified BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_users_city_state ON users(city, state);
CREATE INDEX idx_users_role ON users(role);

-- ====================
-- EVENTS TABLE
-- ====================

CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    description TEXT NOT NULL,
    event_type event_type NOT NULL,
    status event_status DEFAULT 'draft',

    -- Images
    banner_image_url VARCHAR(500),
    logo_url VARCHAR(500),
    thumbnail_url VARCHAR(500),

    -- Dates and times
    event_date TIMESTAMP NOT NULL,
    registration_start_date TIMESTAMP NOT NULL,
    registration_end_date TIMESTAMP NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,

    -- Location
    location_name VARCHAR(255) NOT NULL,
    country VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    address VARCHAR(255),
    route_map_url VARCHAR(500),

    -- Event details
    total_distance DECIMAL(10,2),
    distance_unit VARCHAR(10) DEFAULT 'km',
    difficulty_level VARCHAR(50),
    elevation_gain DECIMAL(10,2),

    -- Capacity
    max_participants INTEGER,
    current_participants INTEGER DEFAULT 0,
    age_restriction_min INTEGER,
    age_restriction_max INTEGER,

    -- Registration
    registration_fee DECIMAL(10,2),
    currency VARCHAR(10) DEFAULT 'INR',

    -- Additional info
    rules TEXT,
    prize_details JSONB,
    time_limit INTEGER,
    category_support JSONB,

    -- Organizer
    organizer_id INTEGER NOT NULL REFERENCES users(id),
    organizer_contact_email VARCHAR(255),
    organizer_contact_phone VARCHAR(20),

    -- Flags
    is_virtual BOOLEAN DEFAULT FALSE,
    is_featured BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_events_status ON events(status);
CREATE INDEX idx_events_date ON events(event_date);
CREATE INDEX idx_events_location ON events(city, state, country);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_virtual ON events(is_virtual);
CREATE INDEX idx_events_slug ON events(slug);
CREATE INDEX idx_events_organizer ON events(organizer_id);

-- ====================
-- EVENT CATEGORIES TABLE
-- ====================

CREATE TABLE event_categories (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    distance DECIMAL(10,2),
    description VARCHAR(255),

    -- Restrictions
    time_limit INTEGER,
    min_age INTEGER,
    max_age INTEGER,
    gender_restriction VARCHAR(50),

    -- Capacity
    max_participants INTEGER,
    current_participants INTEGER DEFAULT 0,

    -- Pricing
    registration_fee DECIMAL(10,2),
    early_bird_fee DECIMAL(10,2),
    early_bird_deadline TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_categories_event ON event_categories(event_id);

-- ====================
-- REGISTRATIONS TABLE
-- ====================

CREATE TABLE registrations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    event_id INTEGER NOT NULL REFERENCES events(id),
    event_category_id INTEGER REFERENCES event_categories(id),

    -- Registration details
    registration_number VARCHAR(50) UNIQUE NOT NULL,
    bib_number VARCHAR(50) UNIQUE,
    status registration_status DEFAULT 'pending',

    -- Participant details
    participant_name VARCHAR(255) NOT NULL,
    age INTEGER,
    gender VARCHAR(20),
    t_shirt_size VARCHAR(10),

    -- Emergency contact
    emergency_contact_name VARCHAR(100),
    emergency_contact_phone VARCHAR(20),

    -- Additional info
    dietary_restrictions TEXT,
    notes TEXT,

    -- Timestamps
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confirmed_at TIMESTAMP,
    cancelled_at TIMESTAMP
);

CREATE INDEX idx_registrations_user_event ON registrations(user_id, event_id);
CREATE INDEX idx_registrations_status ON registrations(status);
CREATE INDEX idx_registrations_bib ON registrations(bib_number);
CREATE INDEX idx_registrations_number ON registrations(registration_number);
CREATE INDEX idx_registrations_event ON registrations(event_id);

-- ====================
-- PAYMENTS TABLE
-- ====================

CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    registration_id INTEGER NOT NULL REFERENCES registrations(id),

    -- Payment details
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'INR',
    payment_method payment_method NOT NULL,
    status payment_status DEFAULT 'pending',

    -- Transaction info
    transaction_id VARCHAR(100) UNIQUE,
    gateway_reference VARCHAR(100),
    gateway_name VARCHAR(50),

    -- Refund details
    refund_amount DECIMAL(10,2),
    refund_reason VARCHAR(255),

    -- Timestamps
    initiated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    refunded_at TIMESTAMP,

    notes VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_payments_status ON payments(status, created_at);
CREATE INDEX idx_payments_user ON payments(user_id);
CREATE INDEX idx_payments_transaction ON payments(transaction_id);
CREATE INDEX idx_payments_registration ON payments(registration_id);

-- ====================
-- EVENT RESULTS TABLE
-- ====================

CREATE TABLE event_results (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES events(id),
    registration_id INTEGER NOT NULL REFERENCES registrations(id) UNIQUE,

    -- Timing
    start_time TIMESTAMP,
    finish_time TIMESTAMP,
    chip_start_time TIMESTAMP,
    chip_finish_time TIMESTAMP,
    gun_time_seconds INTEGER,
    chip_time_seconds INTEGER,

    -- Performance
    avg_pace_per_km DECIMAL(5,2),
    top_speed DECIMAL(5,2),

    -- Rankings
    overall_rank INTEGER,
    gender_rank INTEGER,
    age_group_rank INTEGER,
    category_rank INTEGER,

    -- Status
    status result_status DEFAULT 'not_started',

    -- Additional metrics
    calories_burned DECIMAL(8,2),
    elevation_gain DECIMAL(10,2),
    distance_covered DECIMAL(10,2),

    -- Checkpoint data
    splits JSONB,

    notes VARCHAR(500),
    published BOOLEAN DEFAULT FALSE,
    published_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_results_event_rank ON event_results(event_id, overall_rank);
CREATE INDEX idx_results_event_status ON event_results(event_id, status);
CREATE INDEX idx_results_finish_time ON event_results(finish_time);
CREATE INDEX idx_results_registration ON event_results(registration_id);

-- ====================
-- CERTIFICATES TABLE
-- ====================

CREATE TABLE certificates (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    event_id INTEGER NOT NULL REFERENCES events(id),
    registration_id INTEGER REFERENCES registrations(id),

    certificate_number VARCHAR(100) UNIQUE NOT NULL,
    certificate_url VARCHAR(500) NOT NULL,
    certificate_pdf_url VARCHAR(500),

    is_verified BOOLEAN DEFAULT TRUE,
    verification_code VARCHAR(50) UNIQUE NOT NULL,

    issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_certificates_user ON certificates(user_id);
CREATE INDEX idx_certificates_verification ON certificates(verification_code);
CREATE INDEX idx_certificates_event ON certificates(event_id);

-- ====================
-- LEADERBOARDS TABLE (Cached)
-- ====================

CREATE TABLE leaderboards (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES events(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    registration_id INTEGER NOT NULL REFERENCES registrations(id),

    -- Rankings
    overall_rank INTEGER NOT NULL,
    gender_rank INTEGER,
    age_group_rank INTEGER,
    category_rank INTEGER,

    -- Performance
    finish_time_seconds INTEGER,
    avg_pace_per_km DECIMAL(5,2),
    total_time_display VARCHAR(20),

    points DECIMAL(10,2) DEFAULT 0,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_leaderboard_event_rank ON leaderboards(event_id, overall_rank);
CREATE INDEX idx_leaderboard_user ON leaderboards(user_id);

-- ====================
-- EVENT CHECKPOINTS TABLE
-- ====================

CREATE TABLE event_checkpoints (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    checkpoint_number INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    distance_from_start DECIMAL(10,2),
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    elevation DECIMAL(10,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_checkpoints_event ON event_checkpoints(event_id, checkpoint_number);

-- ====================
-- CHECKPOINT TIMINGS TABLE
-- ====================

CREATE TABLE checkpoint_timings (
    id SERIAL PRIMARY KEY,
    registration_id INTEGER NOT NULL REFERENCES registrations(id),
    checkpoint_id INTEGER NOT NULL REFERENCES event_checkpoints(id),
    timestamp TIMESTAMP NOT NULL,
    time_from_start_seconds INTEGER,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_checkpoint_timings ON checkpoint_timings(registration_id, checkpoint_id);

-- ====================
-- USER ACHIEVEMENTS TABLE
-- ====================

CREATE TABLE user_achievements (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    achievement_type VARCHAR(50) NOT NULL,
    title VARCHAR(100) NOT NULL,
    description TEXT,
    icon_url VARCHAR(500),

    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_achievements_user ON user_achievements(user_id);

-- ====================
-- EVENT SPONSORS TABLE
-- ====================

CREATE TABLE event_sponsors (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    logo_url VARCHAR(500),
    website_url VARCHAR(500),
    sponsor_type VARCHAR(50),
    display_order INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sponsors_event ON event_sponsors(event_id);

-- ====================
-- EVENT PHOTOS TABLE
-- ====================

CREATE TABLE event_photos (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES events(id),
    registration_id INTEGER REFERENCES registrations(id),
    photo_url VARCHAR(500) NOT NULL,
    thumbnail_url VARCHAR(500),
    photographer_name VARCHAR(100),
    checkpoint_id INTEGER REFERENCES event_checkpoints(id),

    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_photos_event ON event_photos(event_id);
CREATE INDEX idx_photos_registration ON event_photos(registration_id);

-- ====================
-- VIRTUAL CHALLENGES TABLE
-- ====================

CREATE TABLE virtual_challenges (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    challenge_type VARCHAR(50) NOT NULL,
    target_value DECIMAL(10,2) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    medal_image_url VARCHAR(500),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ====================
-- CHALLENGE PARTICIPATIONS TABLE
-- ====================

CREATE TABLE challenge_participations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    challenge_id INTEGER NOT NULL REFERENCES virtual_challenges(id),
    current_progress DECIMAL(10,2) DEFAULT 0,
    status VARCHAR(50) DEFAULT 'active',

    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX idx_challenge_participation ON challenge_participations(user_id, challenge_id);

-- ====================
-- TRIGGERS FOR UPDATED_AT
-- ====================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_events_updated_at BEFORE UPDATE ON events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payments_updated_at BEFORE UPDATE ON payments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_results_updated_at BEFORE UPDATE ON event_results
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ====================
-- FUNCTIONS FOR BUSINESS LOGIC
-- ====================

-- Function to generate registration number
CREATE OR REPLACE FUNCTION generate_registration_number(event_id_param INTEGER)
RETURNS VARCHAR AS $$
DECLARE
    event_prefix VARCHAR(10);
    sequence_num INTEGER;
    reg_number VARCHAR(50);
BEGIN
    SELECT UPPER(SUBSTRING(slug FROM 1 FOR 3)) INTO event_prefix FROM events WHERE id = event_id_param;
    SELECT COUNT(*) + 1 INTO sequence_num FROM registrations WHERE event_id = event_id_param;
    reg_number := event_prefix || '-' || LPAD(sequence_num::TEXT, 6, '0');
    RETURN reg_number;
END;
$$ LANGUAGE plpgsql;

-- Function to generate BIB number
CREATE OR REPLACE FUNCTION generate_bib_number(event_id_param INTEGER)
RETURNS VARCHAR AS $$
DECLARE
    sequence_num INTEGER;
BEGIN
    SELECT COUNT(*) + 1 INTO sequence_num
    FROM registrations
    WHERE event_id = event_id_param AND status IN ('confirmed', 'payment_completed');

    RETURN LPAD(sequence_num::TEXT, 4, '0');
END;
$$ LANGUAGE plpgsql;

-- ====================
-- VIEWS FOR COMMON QUERIES
-- ====================

-- View: Active Events
CREATE VIEW active_events AS
SELECT
    e.*,
    u.first_name || ' ' || u.last_name as organizer_name,
    COUNT(DISTINCT r.id) as total_registrations,
    COUNT(DISTINCT CASE WHEN r.status = 'payment_completed' THEN r.id END) as confirmed_registrations
FROM events e
LEFT JOIN users u ON e.organizer_id = u.id
LEFT JOIN registrations r ON e.id = r.event_id
WHERE e.status IN ('published', 'registration_open')
GROUP BY e.id, u.first_name, u.last_name;

-- View: User Statistics
CREATE VIEW user_statistics AS
SELECT
    u.id as user_id,
    u.first_name || ' ' || u.last_name as name,
    COUNT(DISTINCT r.id) as total_events_registered,
    COUNT(DISTINCT CASE WHEN res.status = 'finished' THEN res.id END) as events_completed,
    SUM(CASE WHEN res.status = 'finished' THEN res.distance_covered ELSE 0 END) as total_distance_km,
    MIN(res.chip_time_seconds) as best_time_seconds,
    AVG(res.chip_time_seconds) as avg_time_seconds
FROM users u
LEFT JOIN registrations r ON u.id = r.user_id
LEFT JOIN event_results res ON r.id = res.registration_id
GROUP BY u.id;

-- ====================
-- SAMPLE DATA (Optional)
-- ====================

-- Insert admin user (password: admin123)
INSERT INTO users (email, password_hash, first_name, last_name, role, email_verified)
VALUES ('admin@glycogrit.com', '$2b$12$KIXxkqLQvhBqWkZvQ2zJKuFTzQxQN4p0YrQvZJQzQxQN4p0YrQvZJ', 'Admin', 'User', 'admin', TRUE);

-- Grant all privileges
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO CURRENT_USER;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO CURRENT_USER;
