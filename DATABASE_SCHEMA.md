# GlycoGrit Database Schema Documentation

## Overview
This document outlines the complete database architecture for the GlycoGrit running/fitness events platform, based on analysis of leading platforms like Pedal Pulse, iFinish, TCS World 10K, and others.

## Database Stack

### Primary: PostgreSQL
- **Version:** 14+
- **Purpose:** Relational data storage
- **Use Cases:** User data, events, registrations, payments, results

### Secondary: Redis (Recommended)
- **Version:** 7+
- **Purpose:** Caching and real-time data
- **Use Cases:** Leaderboards, sessions, rate limiting, live tracking

### File Storage
- **Options:** AWS S3, CloudFlare R2, Railway Volumes
- **Purpose:** Static assets (images, PDFs, certificates)

---

## Core Entities

### 1. Users
**Table:** `users`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| email | VARCHAR(255) | UNIQUE, NOT NULL, INDEX | User email |
| phone | VARCHAR(20) | UNIQUE | Phone number |
| password_hash | VARCHAR(255) | NOT NULL | Bcrypt hashed password |
| first_name | VARCHAR(100) | NOT NULL | First name |
| last_name | VARCHAR(100) | NOT NULL | Last name |
| date_of_birth | DATE | | Date of birth |
| gender | VARCHAR(20) | | Gender (Male/Female/Other) |
| profile_picture_url | VARCHAR(500) | | Profile image URL |
| bio | TEXT | | User bio |
| role | ENUM | DEFAULT 'participant' | admin/organizer/participant/volunteer |
| country | VARCHAR(100) | | Country |
| state | VARCHAR(100) | | State/Province |
| city | VARCHAR(100) | | City |
| postal_code | VARCHAR(20) | | Postal code |
| address | VARCHAR(255) | | Street address |
| emergency_contact_name | VARCHAR(100) | | Emergency contact |
| emergency_contact_phone | VARCHAR(20) | | Emergency phone |
| blood_group | VARCHAR(10) | | Blood group (A+, B-, etc.) |
| medical_conditions | TEXT | | Medical conditions |
| allergies | TEXT | | Allergies |
| is_active | BOOLEAN | DEFAULT TRUE | Account active status |
| email_verified | BOOLEAN | DEFAULT FALSE | Email verification status |
| phone_verified | BOOLEAN | DEFAULT FALSE | Phone verification status |
| created_at | TIMESTAMP | DEFAULT NOW() | Account creation time |
| updated_at | TIMESTAMP | DEFAULT NOW() | Last update time |
| last_login | TIMESTAMP | | Last login time |

**Indexes:**
```sql
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_users_city_state ON users(city, state);
CREATE INDEX idx_users_role ON users(role);
```

---

### 2. Events
**Table:** `events`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| name | VARCHAR(255) | NOT NULL, INDEX | Event name |
| slug | VARCHAR(255) | UNIQUE, INDEX | URL-friendly name |
| description | TEXT | NOT NULL | Event description |
| event_type | ENUM | NOT NULL | running/cycling/triathlon/marathon/virtual |
| status | ENUM | DEFAULT 'draft', INDEX | draft/published/registration_open/ongoing/completed/cancelled |
| banner_image_url | VARCHAR(500) | | Banner image |
| logo_url | VARCHAR(500) | | Event logo |
| thumbnail_url | VARCHAR(500) | | Thumbnail for listings |
| event_date | TIMESTAMP | NOT NULL, INDEX | Event date |
| registration_start_date | TIMESTAMP | NOT NULL | Registration opens |
| registration_end_date | TIMESTAMP | NOT NULL | Registration closes |
| start_time | TIMESTAMP | NOT NULL | Event start time |
| end_time | TIMESTAMP | | Event end time |
| location_name | VARCHAR(255) | NOT NULL | Venue name |
| country | VARCHAR(100) | NOT NULL, INDEX | Country |
| state | VARCHAR(100) | NOT NULL, INDEX | State |
| city | VARCHAR(100) | NOT NULL, INDEX | City |
| latitude | DECIMAL(10,8) | | GPS latitude |
| longitude | DECIMAL(11,8) | | GPS longitude |
| address | VARCHAR(255) | | Full address |
| route_map_url | VARCHAR(500) | | Route map image |
| total_distance | DECIMAL(10,2) | | Distance in km |
| distance_unit | VARCHAR(10) | DEFAULT 'km' | km/miles |
| difficulty_level | VARCHAR(50) | | beginner/intermediate/advanced |
| elevation_gain | DECIMAL(10,2) | | Total elevation in meters |
| max_participants | INTEGER | | Maximum capacity |
| current_participants | INTEGER | DEFAULT 0 | Current registrations |
| age_restriction_min | INTEGER | | Minimum age |
| age_restriction_max | INTEGER | | Maximum age |
| registration_fee | DECIMAL(10,2) | | Base registration fee |
| currency | VARCHAR(10) | DEFAULT 'INR' | Currency code |
| rules | TEXT | | Event rules |
| prize_details | JSONB | | Prize information |
| time_limit | INTEGER | | Time limit in minutes |
| organizer_id | INTEGER | FOREIGN KEY -> users(id) | Organizer user ID |
| organizer_contact_email | VARCHAR(255) | | Contact email |
| organizer_contact_phone | VARCHAR(20) | | Contact phone |
| category_support | JSONB | | Supported categories |
| is_virtual | BOOLEAN | DEFAULT FALSE | Virtual event flag |
| is_featured | BOOLEAN | DEFAULT FALSE | Featured on homepage |
| created_at | TIMESTAMP | DEFAULT NOW() | Creation time |
| updated_at | TIMESTAMP | DEFAULT NOW() | Last update |

**Indexes:**
```sql
CREATE INDEX idx_events_status ON events(status);
CREATE INDEX idx_events_date ON events(event_date);
CREATE INDEX idx_events_location ON events(city, state, country);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_virtual ON events(is_virtual);
CREATE INDEX idx_events_slug ON events(slug);
```

---

### 3. Event Categories
**Table:** `event_categories`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| event_id | INTEGER | FOREIGN KEY -> events(id), INDEX | Associated event |
| name | VARCHAR(100) | NOT NULL | Category name (5K, 10K, etc.) |
| distance | DECIMAL(10,2) | | Distance in km |
| description | VARCHAR(255) | | Category description |
| time_limit | INTEGER | | Time limit in minutes |
| min_age | INTEGER | | Minimum age |
| max_age | INTEGER | | Maximum age |
| gender_restriction | VARCHAR(50) | | M/F/All |
| max_participants | INTEGER | | Category capacity |
| current_participants | INTEGER | DEFAULT 0 | Current count |
| registration_fee | DECIMAL(10,2) | | Category fee |
| early_bird_fee | DECIMAL(10,2) | | Early bird discount |
| early_bird_deadline | TIMESTAMP | | Early bird deadline |
| created_at | TIMESTAMP | DEFAULT NOW() | Creation time |

**Indexes:**
```sql
CREATE INDEX idx_categories_event ON event_categories(event_id);
```

---

### 4. Registrations
**Table:** `registrations`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| user_id | INTEGER | FOREIGN KEY -> users(id), INDEX | Registered user |
| event_id | INTEGER | FOREIGN KEY -> events(id), INDEX | Event |
| registration_number | VARCHAR(50) | UNIQUE, NOT NULL, INDEX | Registration number |
| bib_number | VARCHAR(50) | UNIQUE | BIB number |
| status | ENUM | DEFAULT 'pending', INDEX | pending/confirmed/payment_pending/payment_completed/cancelled/withdrawn |
| event_category_id | INTEGER | FOREIGN KEY -> event_categories(id) | Selected category |
| participant_name | VARCHAR(255) | NOT NULL | Name on certificate |
| age | INTEGER | | Age at registration |
| gender | VARCHAR(20) | | Gender |
| t_shirt_size | VARCHAR(10) | | T-shirt size (XS/S/M/L/XL/XXL) |
| emergency_contact_name | VARCHAR(100) | | Emergency contact |
| emergency_contact_phone | VARCHAR(20) | | Emergency phone |
| dietary_restrictions | TEXT | | Dietary info |
| notes | TEXT | | Additional notes |
| registered_at | TIMESTAMP | DEFAULT NOW(), INDEX | Registration time |
| confirmed_at | TIMESTAMP | | Confirmation time |
| cancelled_at | TIMESTAMP | | Cancellation time |

**Indexes:**
```sql
CREATE INDEX idx_registrations_user_event ON registrations(user_id, event_id);
CREATE INDEX idx_registrations_status ON registrations(status);
CREATE INDEX idx_registrations_bib ON registrations(bib_number);
CREATE INDEX idx_registrations_number ON registrations(registration_number);
```

---

### 5. Payments
**Table:** `payments`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| user_id | INTEGER | FOREIGN KEY -> users(id), INDEX | User |
| registration_id | INTEGER | FOREIGN KEY -> registrations(id), INDEX | Registration |
| amount | DECIMAL(10,2) | NOT NULL | Payment amount |
| currency | VARCHAR(10) | DEFAULT 'INR' | Currency |
| payment_method | ENUM | NOT NULL | credit_card/debit_card/upi/net_banking/wallet |
| status | ENUM | DEFAULT 'pending', INDEX | pending/completed/failed/refunded/cancelled |
| transaction_id | VARCHAR(100) | UNIQUE | Transaction ID |
| gateway_reference | VARCHAR(100) | | Payment gateway reference |
| gateway_name | VARCHAR(50) | | Razorpay/Stripe/PayPal |
| initiated_at | TIMESTAMP | DEFAULT NOW() | Payment initiation |
| completed_at | TIMESTAMP | | Payment completion |
| refunded_at | TIMESTAMP | | Refund time |
| refund_amount | DECIMAL(10,2) | | Refund amount |
| refund_reason | VARCHAR(255) | | Refund reason |
| notes | VARCHAR(500) | | Additional notes |
| created_at | TIMESTAMP | DEFAULT NOW() | Creation time |
| updated_at | TIMESTAMP | DEFAULT NOW() | Last update |

**Indexes:**
```sql
CREATE INDEX idx_payments_status ON payments(status, created_at);
CREATE INDEX idx_payments_user ON payments(user_id);
CREATE INDEX idx_payments_transaction ON payments(transaction_id);
```

---

### 6. Event Results
**Table:** `event_results`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| event_id | INTEGER | FOREIGN KEY -> events(id), INDEX | Event |
| registration_id | INTEGER | FOREIGN KEY -> registrations(id), UNIQUE | Registration |
| start_time | TIMESTAMP | | Actual start time |
| finish_time | TIMESTAMP | | Finish time |
| chip_start_time | TIMESTAMP | | Chip start time |
| chip_finish_time | TIMESTAMP | | Chip finish time |
| gun_time_seconds | INTEGER | | Gun time in seconds |
| chip_time_seconds | INTEGER | | Chip time in seconds |
| avg_pace_per_km | DECIMAL(5,2) | | Pace (min/km) |
| top_speed | DECIMAL(5,2) | | Top speed (km/h) |
| overall_rank | INTEGER | INDEX | Overall ranking |
| gender_rank | INTEGER | | Gender ranking |
| age_group_rank | INTEGER | | Age group ranking |
| category_rank | INTEGER | | Category ranking |
| status | ENUM | DEFAULT 'not_started' | not_started/in_progress/finished/dnf/dns/disqualified |
| calories_burned | DECIMAL(8,2) | | Estimated calories |
| elevation_gain | DECIMAL(10,2) | | Elevation gained |
| distance_covered | DECIMAL(10,2) | | Actual distance |
| splits | JSONB | | Checkpoint splits data |
| notes | VARCHAR(500) | | Notes |
| published | BOOLEAN | DEFAULT FALSE | Result published |
| published_at | TIMESTAMP | | Publication time |
| created_at | TIMESTAMP | DEFAULT NOW() | Creation time |
| updated_at | TIMESTAMP | DEFAULT NOW() | Last update |

**Indexes:**
```sql
CREATE INDEX idx_results_event_rank ON event_results(event_id, overall_rank);
CREATE INDEX idx_results_event_status ON event_results(event_id, status);
CREATE INDEX idx_results_finish_time ON event_results(finish_time);
```

---

### 7. Certificates
**Table:** `certificates`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| user_id | INTEGER | FOREIGN KEY -> users(id), INDEX | User |
| event_id | INTEGER | FOREIGN KEY -> events(id), INDEX | Event |
| registration_id | INTEGER | FOREIGN KEY -> registrations(id) | Registration |
| certificate_number | VARCHAR(100) | UNIQUE, NOT NULL | Certificate number |
| certificate_url | VARCHAR(500) | NOT NULL | Certificate image URL |
| certificate_pdf_url | VARCHAR(500) | | PDF download URL |
| is_verified | BOOLEAN | DEFAULT TRUE | Verification status |
| verification_code | VARCHAR(50) | UNIQUE, NOT NULL | QR code/verification |
| issued_at | TIMESTAMP | DEFAULT NOW() | Issue date |

**Indexes:**
```sql
CREATE INDEX idx_certificates_user ON certificates(user_id);
CREATE INDEX idx_certificates_verification ON certificates(verification_code);
```

---

### 8. Leaderboards (Cached Table)
**Table:** `leaderboards`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| event_id | INTEGER | FOREIGN KEY -> events(id), INDEX | Event |
| user_id | INTEGER | FOREIGN KEY -> users(id) | User |
| registration_id | INTEGER | FOREIGN KEY -> registrations(id) | Registration |
| overall_rank | INTEGER | NOT NULL | Overall rank |
| gender_rank | INTEGER | | Gender rank |
| age_group_rank | INTEGER | | Age group rank |
| category_rank | INTEGER | | Category rank |
| finish_time_seconds | INTEGER | | Time in seconds |
| avg_pace_per_km | DECIMAL(5,2) | | Pace |
| total_time_display | VARCHAR(20) | | HH:MM:SS format |
| points | DECIMAL(10,2) | DEFAULT 0 | Points earned |
| updated_at | TIMESTAMP | DEFAULT NOW() | Last cache update |

**Indexes:**
```sql
CREATE INDEX idx_leaderboard_event_rank ON leaderboards(event_id, overall_rank);
CREATE INDEX idx_leaderboard_user ON leaderboards(user_id);
```

---

### 9. Event Checkpoints
**Table:** `event_checkpoints`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| event_id | INTEGER | FOREIGN KEY -> events(id), INDEX | Event |
| checkpoint_number | INTEGER | NOT NULL | Checkpoint sequence |
| name | VARCHAR(100) | NOT NULL | Checkpoint name |
| distance_from_start | DECIMAL(10,2) | | Distance in km |
| latitude | DECIMAL(10,8) | | GPS latitude |
| longitude | DECIMAL(11,8) | | GPS longitude |
| elevation | DECIMAL(10,2) | | Elevation in meters |
| created_at | TIMESTAMP | DEFAULT NOW() | Creation time |

**Indexes:**
```sql
CREATE INDEX idx_checkpoints_event ON event_checkpoints(event_id, checkpoint_number);
```

---

### 10. Checkpoint Timings
**Table:** `checkpoint_timings`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| registration_id | INTEGER | FOREIGN KEY -> registrations(id), INDEX | Registration |
| checkpoint_id | INTEGER | FOREIGN KEY -> event_checkpoints(id) | Checkpoint |
| timestamp | TIMESTAMP | NOT NULL | Crossing time |
| time_from_start_seconds | INTEGER | | Time from start |
| created_at | TIMESTAMP | DEFAULT NOW() | Record creation |

**Indexes:**
```sql
CREATE INDEX idx_checkpoint_timings ON checkpoint_timings(registration_id, checkpoint_id);
```

---

### 11. User Achievements
**Table:** `user_achievements`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| user_id | INTEGER | FOREIGN KEY -> users(id), INDEX | User |
| achievement_type | VARCHAR(50) | NOT NULL | Type of achievement |
| title | VARCHAR(100) | NOT NULL | Achievement title |
| description | TEXT | | Description |
| icon_url | VARCHAR(500) | | Icon/badge image |
| earned_at | TIMESTAMP | DEFAULT NOW() | Earned date |

**Indexes:**
```sql
CREATE INDEX idx_achievements_user ON user_achievements(user_id);
```

---

### 12. Event Sponsors
**Table:** `event_sponsors`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| event_id | INTEGER | FOREIGN KEY -> events(id), INDEX | Event |
| name | VARCHAR(255) | NOT NULL | Sponsor name |
| logo_url | VARCHAR(500) | | Logo image |
| website_url | VARCHAR(500) | | Website |
| sponsor_type | VARCHAR(50) | | title/platinum/gold/silver |
| display_order | INTEGER | DEFAULT 0 | Display order |
| created_at | TIMESTAMP | DEFAULT NOW() | Creation time |

---

### 13. Event Photos
**Table:** `event_photos`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| event_id | INTEGER | FOREIGN KEY -> events(id), INDEX | Event |
| registration_id | INTEGER | FOREIGN KEY -> registrations(id) | Associated participant |
| photo_url | VARCHAR(500) | NOT NULL | Photo URL |
| thumbnail_url | VARCHAR(500) | | Thumbnail URL |
| photographer_name | VARCHAR(100) | | Photographer |
| checkpoint_id | INTEGER | FOREIGN KEY -> event_checkpoints(id) | Checkpoint location |
| uploaded_at | TIMESTAMP | DEFAULT NOW() | Upload time |

**Indexes:**
```sql
CREATE INDEX idx_photos_event ON event_photos(event_id);
CREATE INDEX idx_photos_registration ON event_photos(registration_id);
```

---

### 14. Virtual Challenges
**Table:** `virtual_challenges`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| name | VARCHAR(255) | NOT NULL | Challenge name |
| description | TEXT | NOT NULL | Challenge description |
| challenge_type | VARCHAR(50) | NOT NULL | distance/duration/streak |
| target_value | DECIMAL(10,2) | NOT NULL | Target (km or days) |
| start_date | DATE | NOT NULL | Challenge start |
| end_date | DATE | NOT NULL | Challenge end |
| medal_image_url | VARCHAR(500) | | Medal image |
| created_at | TIMESTAMP | DEFAULT NOW() | Creation time |

---

### 15. Challenge Participations
**Table:** `challenge_participations`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique identifier |
| user_id | INTEGER | FOREIGN KEY -> users(id), INDEX | User |
| challenge_id | INTEGER | FOREIGN KEY -> virtual_challenges(id) | Challenge |
| current_progress | DECIMAL(10,2) | DEFAULT 0 | Current progress |
| status | VARCHAR(50) | DEFAULT 'active' | active/completed/abandoned |
| started_at | TIMESTAMP | DEFAULT NOW() | Start date |
| completed_at | TIMESTAMP | | Completion date |

**Indexes:**
```sql
CREATE INDEX idx_challenge_participation ON challenge_participations(user_id, challenge_id);
```

---

## Redis Cache Schema

### Key Patterns:

```
leaderboard:event:{event_id}:overall
leaderboard:event:{event_id}:gender:{gender}
leaderboard:event:{event_id}:age_group:{group}
leaderboard:event:{event_id}:category:{category_id}

event:featured:list
event:upcoming:city:{city_name}
event:trending

user:session:{user_id}
user:otp:{phone_number}

rate_limit:api:{user_id}:{endpoint}

live_tracking:event:{event_id}:participant:{registration_id}
```

### Example Redis Operations:

```python
# Leaderboard (Sorted Set)
ZADD leaderboard:event:123:overall 3600 "reg_456"  # 3600 seconds = 1 hour

# Get top 10
ZRANGE leaderboard:event:123:overall 0 9 WITHSCORES

# Cache event list (String with TTL)
SETEX event:featured:list 300 "<json_data>"

# Rate limiting (Counter)
INCR rate_limit:api:user_123:/api/events
EXPIRE rate_limit:api:user_123:/api/events 60
```

---

## Database Migration Strategy

### Using Alembic for Migrations:

```bash
# Initialize Alembic
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Create initial tables"

# Apply migration
alembic upgrade head
```

---

## Performance Optimization

### Indexing Strategy:
1. **Foreign Keys:** Always index foreign key columns
2. **Search Columns:** Index columns used in WHERE, ORDER BY, GROUP BY
3. **Composite Indexes:** For multi-column queries
4. **Partial Indexes:** For status-based queries

### Query Optimization:
```sql
-- Example: Efficient event search with filters
SELECT e.*, COUNT(r.id) as participant_count
FROM events e
LEFT JOIN registrations r ON e.id = r.event_id AND r.status = 'confirmed'
WHERE e.status = 'registration_open'
  AND e.city = 'Mumbai'
  AND e.event_date >= CURRENT_DATE
GROUP BY e.id
ORDER BY e.event_date ASC
LIMIT 20;
```

### Connection Pooling:
```python
# Already configured in your database.py
pool_size=5
max_overflow=10
pool_pre_ping=True
```

---

## Backup Strategy

### PostgreSQL Backups:
```bash
# Daily backup
pg_dump -h hostname -U username -d glycogrit_db > backup_$(date +%Y%m%d).sql

# Point-in-time recovery (enable WAL archiving)
wal_level = replica
archive_mode = on
archive_command = 'cp %p /archive/%f'
```

---

## Security Considerations

1. **Password Storage:** Use bcrypt/argon2 for hashing
2. **SQL Injection:** Use parameterized queries (SQLAlchemy ORM)
3. **Data Encryption:** Encrypt sensitive fields (medical info, payment data)
4. **Access Control:** Role-based permissions
5. **Audit Logs:** Track critical operations

---

## Monitoring

### Key Metrics to Track:
- Database connection pool utilization
- Query execution times
- Cache hit/miss ratios
- Registration conversion rates
- Payment success rates

### Tools:
- PostgreSQL: pg_stat_statements
- Redis: INFO stats
- Application: Prometheus + Grafana

---

## Estimated Storage Requirements

**For 1000 events with 500 participants each:**
- Users: ~200 KB
- Events: ~100 KB
- Registrations: ~25 MB
- Results: ~30 MB
- Certificates: ~50 GB (images)
- Photos: ~500 GB

**Total Database:** ~60 MB (without binary data)
**Total Storage:** ~550 GB (with images/PDFs)
