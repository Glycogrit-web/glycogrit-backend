# Database Architecture Analysis for GlycoGrit
## Running/Fitness Events Platform Requirements

Based on analyzing leading platforms: Pedal Pulse, iFinish, TCS World 10K, Apna Run, The Conqueror Events, Great Ocean Road Run Fest, Run Army, and Virtual Pace Series

---

## Executive Summary

### Current Stack:
- **PostgreSQL** (Already configured ✅)
- FastAPI backend
- SQLAlchemy ORM

### Recommended Additions:
- **Redis** - For caching and real-time features
- **File Storage** (S3/CloudFlare R2/Railway Volumes) - For images, PDFs, certificates

---

## 1. Core Database Requirements (PostgreSQL)

### Essential Tables:

#### **A. User Management**
- **users** - Core user profiles
  - Authentication (email, password, phone)
  - Personal info (name, DOB, gender)
  - Address details
  - Emergency contacts
  - Health info (blood group, medical conditions)
  - Account status flags

#### **B. Event Management**
- **events** - Main event listings
  - Event details (name, type, description)
  - Date/time information
  - Location (city, state, GPS coordinates)
  - Capacity and restrictions
  - Registration fees and currency
  - Status workflow (draft → published → ongoing → completed)

- **event_categories** - Distance categories (5K, 10K, 21K, etc.)
  - Category-specific pricing
  - Age/gender restrictions per category
  - Individual capacity limits

- **event_checkpoints** - Course milestones
  - Distance markers
  - GPS coordinates
  - Elevation data

#### **C. Registration System**
- **registrations** - Participant sign-ups
  - Unique registration number
  - BIB number assignment
  - Status tracking (pending → confirmed → payment_completed)
  - T-shirt size, dietary preferences
  - Emergency contact for event

#### **D. Payment Processing**
- **payments** - Transaction records
  - Multiple payment methods (UPI, cards, net banking, wallet)
  - Gateway integration details (Razorpay, Stripe)
  - Refund tracking
  - Transaction status

#### **E. Results & Timing**
- **event_results** - Race performance data
  - Start/finish times (gun time vs chip time)
  - Rankings (overall, gender, age group, category)
  - Performance metrics (pace, speed, calories)
  - Status (finished, DNF, DNS, disqualified)

- **checkpoint_timings** - Split times
  - Time at each checkpoint
  - Cumulative time tracking

- **leaderboards** - Cached rankings
  - Real-time leaderboard updates
  - Multiple ranking types

#### **F. Certificates & Achievements**
- **certificates** - Digital completion certificates
  - PDF and image URLs
  - Verification codes (QR code support)
  - Certificate numbers

- **user_achievements** - Badges and milestones
  - Achievement types
  - Icons/badges

#### **G. Additional Features**
- **event_sponsors** - Sponsor information
- **event_photos** - Race photos by participant
- **virtual_challenges** - Distance/duration challenges
- **challenge_participations** - User progress in challenges

---

## 2. Key Relationships

```
USER (1) ──── (Many) REGISTRATIONS
                      │
                      ├── (1) PAYMENT
                      │
                      └── (1) EVENT_RESULT ──── (1) CERTIFICATE

EVENT (1) ──── (Many) EVENT_CATEGORIES
         │
         ├── (Many) REGISTRATIONS
         │
         ├── (Many) EVENT_CHECKPOINTS
         │
         └── (Many) EVENT_RESULTS
```

---

## 3. Redis Requirements (Caching Layer)

### Why Redis?
- Real-time leaderboard updates during events
- Reduce database load for frequently accessed data
- Session management
- Rate limiting
- Temporary data storage (OTPs)

### Redis Use Cases:

#### **A. Leaderboards (Sorted Sets)**
```
Key: leaderboard:event:{event_id}:overall
Structure: ZSET (score = finish time, member = registration_id)
TTL: 60 seconds during event, 1 hour after completion
```

#### **B. Event Listings (Strings)**
```
Key: events:featured, events:city:{city_name}
Structure: JSON string
TTL: 5 minutes
```

#### **C. Live Tracking (Hashes/Strings)**
```
Key: tracking:event:{event_id}:participant:{reg_id}
Data: GPS coordinates, checkpoint, timestamp
TTL: 30 seconds
```

#### **D. Sessions (Strings)**
```
Key: session:{session_id}
Data: User session data
TTL: 24 hours
```

#### **E. Rate Limiting (Counters)**
```
Key: rate_limit:{user_id}:{endpoint}
Structure: Counter
TTL: 60 seconds
```

#### **F. OTP Storage (Strings)**
```
Key: otp:{phone/email}
Data: 6-digit code
TTL: 5 minutes
```

---

## 4. Database Indexing Strategy

### Critical Indexes:

**Users:**
- `email` (UNIQUE, for login)
- `phone` (UNIQUE, for SMS)
- `city, state` (for location-based queries)

**Events:**
- `status` (filter active events)
- `event_date` (date range queries)
- `city, state, country` (location filtering)
- `slug` (URL lookups)

**Registrations:**
- `user_id, event_id` (composite for user's events)
- `registration_number` (unique lookup)
- `bib_number` (unique lookup)
- `status` (filter by payment status)

**Event Results:**
- `event_id, overall_rank` (leaderboard queries)
- `event_id, status` (filter finishers)

**Payments:**
- `status, created_at` (analytics)
- `transaction_id` (gateway callbacks)

---

## 5. Query Patterns Analysis

### Most Frequent Queries:

1. **Event Discovery**
   ```sql
   SELECT * FROM events
   WHERE status = 'registration_open'
     AND city = 'Mumbai'
     AND event_date >= CURRENT_DATE
   ORDER BY event_date ASC
   ```

2. **User Dashboard**
   ```sql
   SELECT e.*, r.status, r.bib_number
   FROM events e
   JOIN registrations r ON e.id = r.event_id
   WHERE r.user_id = ?
   ORDER BY e.event_date DESC
   ```

3. **Leaderboard**
   ```sql
   SELECT r.bib_number, u.first_name, u.last_name,
          res.chip_time_seconds, res.overall_rank
   FROM event_results res
   JOIN registrations r ON res.registration_id = r.id
   JOIN users u ON r.user_id = u.id
   WHERE res.event_id = ?
     AND res.status = 'finished'
   ORDER BY res.overall_rank ASC
   LIMIT 100
   ```

4. **Payment Verification**
   ```sql
   SELECT * FROM payments
   WHERE transaction_id = ?
   ```

5. **Certificate Lookup**
   ```sql
   SELECT c.*, e.name, u.first_name, u.last_name
   FROM certificates c
   JOIN events e ON c.event_id = e.id
   JOIN users u ON c.user_id = u.id
   WHERE c.verification_code = ?
   ```

---

## 6. Features Breakdown by Platform

### Common Features (All Platforms):

✅ User registration and profiles
✅ Event listings with filters (date, location, distance)
✅ Online registration with payment
✅ BIB number generation
✅ Event results and timing
✅ Leaderboards (overall, gender, age group)
✅ Digital certificates
✅ Multiple event categories (5K, 10K, etc.)

### Advanced Features (Some Platforms):

**iFinish / Pedal Pulse:**
- Live tracking with GPS
- Checkpoint split times
- Photo galleries tagged to participants
- Team registrations
- Corporate registrations

**TCS World 10K / Apna Run:**
- Charity cause selection
- T-shirt customization
- Volunteer management
- Pace groups/pacers
- Training plans

**The Conqueror Events:**
- Virtual challenges (complete X km in Y days)
- Progress tracking with streaks
- Virtual medals on completion
- Social sharing features
- Global leaderboards

**Great Ocean Road / Run Army:**
- Route elevation profiles
- Weather information
- Post-race surveys
- Age group prizes
- Early bird pricing

---

## 7. Data Volume Estimates

### For a Platform with 10,000 Active Users:

| Table | Rows per Event | Growth Rate | Storage Impact |
|-------|---------------|-------------|----------------|
| users | 10,000 | Linear | ~2 MB |
| events | 100/year | Linear | ~100 KB |
| registrations | 500/event | High | ~25 MB/year |
| payments | 500/event | High | ~20 MB/year |
| event_results | 500/event | High | ~30 MB/year |
| certificates | 400/event | High | ~40 KB/year (DB) |
| event_photos | 2,000/event | High | ~0 (external storage) |

**Total Database Size (1 year):** ~100 MB
**Total File Storage (1 year):** ~500 GB (images, PDFs)

---

## 8. Performance Optimization Strategies

### Database Level:
1. **Connection Pooling** (Already configured ✅)
   - pool_size=5
   - max_overflow=10

2. **Query Optimization**
   - Use SELECT specific columns (not SELECT *)
   - Add LIMIT to paginated queries
   - Use COUNT(*) sparingly (cache counts)

3. **Partitioning** (Future consideration)
   - Partition event_results by year
   - Partition payments by month

### Application Level:
1. **Eager Loading**
   - Use SQLAlchemy `joinedload()` for related data
   - Avoid N+1 query problems

2. **Caching Strategy**
   - Cache event lists (5 min TTL)
   - Cache leaderboards (1 min TTL during event)
   - Cache user sessions (24 hours)

3. **Async Operations**
   - Certificate generation (background task)
   - Email notifications (queue-based)
   - Photo processing (background)

---

## 9. Security Considerations

### Database Security:
1. **Password Storage**
   - Use bcrypt/argon2 for hashing
   - Never store plain text passwords

2. **SQL Injection Prevention**
   - Use SQLAlchemy ORM (parameterized queries)
   - Validate all user inputs

3. **Sensitive Data Encryption**
   - Encrypt medical information
   - Encrypt payment details (PCI compliance)

4. **Role-Based Access Control**
   - Admin: Full access
   - Organizer: Own events only
   - Participant: Own registrations only

5. **Audit Logging**
   - Log all payment transactions
   - Log result modifications
   - Log certificate generations

### API Security:
1. **Rate Limiting** (Redis-based)
   - 100 requests/minute per user
   - 1000 requests/minute per IP

2. **Authentication**
   - JWT tokens or session-based
   - Refresh token mechanism

3. **Payment Gateway Security**
   - Use official SDKs (Razorpay, Stripe)
   - Verify webhook signatures
   - Never log full card numbers

---

## 10. Migration Strategy

### Phase 1: Core Features (MVP)
- Users table
- Events table
- Event categories
- Registrations
- Payments (basic)

### Phase 2: Results & Timing
- Event results
- Leaderboards
- Certificates

### Phase 3: Advanced Features
- Checkpoints and split times
- Live tracking
- Photo galleries
- Virtual challenges

### Phase 4: Optimization
- Redis caching
- Performance tuning
- Analytics

---

## 11. Technology Stack Recommendations

### Current Stack (Keep):
- **PostgreSQL 14+** - Relational database
- **FastAPI** - API framework
- **SQLAlchemy** - ORM
- **Pydantic** - Data validation

### Add to Stack:
- **Redis 7+** - Caching layer
- **Celery** - Background task queue
- **Alembic** - Database migrations
- **AWS S3 / CloudFlare R2** - File storage
- **Razorpay / Stripe** - Payment gateway

### Optional (Future):
- **Elasticsearch** - Advanced search
- **GraphQL** - Flexible API queries
- **WebSockets** - Real-time updates
- **Prometheus + Grafana** - Monitoring

---

## 12. Cost Estimates

### Database (Railway/AWS):
- **PostgreSQL:** $5-20/month (small scale)
- **Redis:** $5-15/month
- **Storage (S3):** $0.023/GB/month (~$10-50/month)
- **Total:** ~$20-85/month for 10K users

### Scaling Thresholds:
- Up to 10K users: Single PostgreSQL instance
- 10K-100K users: Read replicas + Redis cluster
- 100K+ users: Database sharding + CDN

---

## 13. Business Logic Examples

### Registration Flow:
1. User selects event and category
2. Fill registration form
3. Payment gateway integration
4. Generate registration number
5. Send confirmation email
6. Assign BIB number (closer to event date)

### Result Submission Flow:
1. Timing system records finish time
2. Calculate rankings (overall, gender, age group)
3. Update leaderboard (Redis)
4. Publish results to database
5. Generate certificate
6. Send completion email

### Virtual Challenge Flow:
1. User joins challenge
2. Sync activities (manual or app integration)
3. Update progress
4. Check milestone achievements
5. Award virtual medal on completion

---

## 14. API Endpoint Structure (Recommended)

```
Authentication:
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/logout
POST   /api/v1/auth/verify-otp

Users:
GET    /api/v1/users/me
PUT    /api/v1/users/me
GET    /api/v1/users/{id}/statistics

Events:
GET    /api/v1/events (with filters)
GET    /api/v1/events/{id}
POST   /api/v1/events (organizer)
PUT    /api/v1/events/{id} (organizer)
GET    /api/v1/events/{id}/categories
GET    /api/v1/events/{id}/leaderboard

Registrations:
POST   /api/v1/registrations
GET    /api/v1/registrations/{id}
GET    /api/v1/users/me/registrations
DELETE /api/v1/registrations/{id}

Payments:
POST   /api/v1/payments/initiate
POST   /api/v1/payments/verify
GET    /api/v1/payments/{id}

Results:
GET    /api/v1/events/{id}/results
GET    /api/v1/results/{registration_id}

Certificates:
GET    /api/v1/certificates/{id}
GET    /api/v1/certificates/verify/{code}
```

---

## 15. Next Steps

### Immediate Actions:
1. ✅ Review this analysis document
2. Decide on MVP feature set
3. Set up Redis (Railway plugin)
4. Design database migrations with Alembic
5. Set up file storage (S3/CloudFlare R2)

### Development Phases:
**Week 1-2:** Database schema and migrations
**Week 3-4:** Authentication and user management
**Week 5-6:** Event management and listings
**Week 7-8:** Registration and payment flow
**Week 9-10:** Results and leaderboards
**Week 11-12:** Certificates and notifications

---

## Questions to Clarify

Before implementation, decide on:

1. **Payment Gateway:** Razorpay (India) or Stripe (Global)?
2. **File Storage:** AWS S3, CloudFlare R2, or Railway Volumes?
3. **Email Service:** SendGrid, AWS SES, or Postmark?
4. **SMS Service:** Twilio, AWS SNS, or local provider?
5. **MVP Features:** What's the minimum viable feature set?
6. **Target Market:** India-focused or global?
7. **Event Scale:** Average participants per event?
8. **Virtual vs Physical:** Focus on which type?

---

## Conclusion

This platform requires:

### Database Architecture:
- **PostgreSQL** as primary database (15 core tables)
- **Redis** for caching and real-time features
- **File Storage** for images and documents

### Key Features:
- User management with health profiles
- Multi-category event management
- Payment gateway integration
- Real-time leaderboards
- Certificate generation
- Live tracking capabilities

### Performance Strategy:
- Strategic indexing for common queries
- Redis caching for hot data
- Connection pooling
- Background task processing

The architecture is designed to scale from 100 to 100,000+ users with proper optimization at each stage.
