# E-Certificate System Testing Guide

## Quick Start Testing

### Prerequisites

1. ✅ Database is running and accessible
2. ✅ Backend server is running
3. ✅ You have a test user account with JWT token
4. ✅ At least one completed registration exists

---

## Step 1: Run Database Migration

```bash
# Activate virtual environment
source venv/bin/activate

# Run migration
alembic upgrade head

# Verify tables created
psql -d glycogrit -c "\dt certificate_templates"
psql -d glycogrit -c "\d user_rewards" | grep certificate
```

**Expected Output:**
```
Table "public.certificate_templates"
...
certificate_url    | character varying(500)
certificate_number | character varying(100)
```

---

## Step 2: Start Backend Server

```bash
# Make sure you're in the backend directory
cd glycogrit-backend

# Activate venv if not already
source venv/bin/activate

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

---

## Step 3: Get Authentication Token

### Option A: Login via API

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your_email@example.com",
    "password": "your_password"
  }'
```

**Save the token:**
```bash
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Option B: Use existing token

If you have a token from frontend, use that.

---

## Step 4: Create Test Data (If Needed)

### Create a completed registration

```sql
-- Connect to database
psql -d glycogrit

-- Check existing completed registrations
SELECT
    r.id as registration_id,
    r.participant_name,
    e.name as event_name,
    ap.distance_completed,
    ap.target_distance,
    ap.is_completed,
    ap.completed_at
FROM registrations r
JOIN events e ON e.id = r.event_id
LEFT JOIN activity_progress ap ON ap.registration_id = r.id
WHERE ap.is_completed = true
LIMIT 5;
```

**If no completed registrations exist, create test data:**

```sql
-- Mark a registration as completed
UPDATE activity_progress
SET
    distance_completed = target_distance + 1,
    completed_at = CURRENT_TIMESTAMP
WHERE registration_id = 1;  -- Replace with actual registration ID
```

---

## Step 5: Test Single Certificate Generation

### Test 1: First-time generation

```bash
# Replace {registration_id} with actual ID
curl -X GET "http://localhost:8000/api/v1/certificates/registration/1" \
  -H "Authorization: Bearer $TOKEN" \
  -v
```

**Expected Response (200 OK):**
```json
{
  "certificate_url": "https://r2.glycogrit.com/certificates/event_1/user_123/cert_1_20240504_031500.pdf",
  "certificate_number": "GLCG-2024-0001-00001",
  "registration_id": 1,
  "generated": true,
  "cached": false
}
```

**Check backend logs for:**
```
INFO: Starting certificate generation for registration_id=1
INFO: Fetching certificate data for registration_id=1
INFO: Loading template for event_id=1
INFO: Filling template with participant data
INFO: Generating PDF from HTML
INFO: PDF generated in 200ms, size=300KB
INFO: Uploading certificate to R2 storage
INFO: Updating UserReward record with certificate URL
INFO: Certificate generation completed successfully for registration_id=1
```

### Test 2: Cached retrieval (instant)

```bash
# Request same certificate again
curl -X GET "http://localhost:8000/api/v1/certificates/registration/1" \
  -H "Authorization: Bearer $TOKEN" \
  -v
```

**Expected Response (instant, < 50ms):**
```json
{
  "certificate_url": "https://r2.glycogrit.com/certificates/event_1/user_123/cert_1_20240504_031500.pdf",
  "certificate_number": "GLCG-2024-0001-00001",
  "registration_id": 1,
  "generated": true,
  "cached": false
}
```

**Check backend logs for:**
```
INFO: Starting certificate generation for registration_id=1
INFO: Certificate already exists for registration_id=1, returning cached URL
```

### Test 3: Force regeneration

```bash
curl -X POST "http://localhost:8000/api/v1/certificates/registration/1/regenerate" \
  -H "Authorization: Bearer $TOKEN" \
  -v
```

**Expected Response:**
```json
{
  "certificate_url": "https://r2.glycogrit.com/certificates/event_1/user_123/cert_1_20240504_032000.pdf",
  "registration_id": 1,
  "regenerated": true
}
```

---

## Step 6: Download and Verify Certificate

```bash
# Download certificate PDF
curl -o test_certificate.pdf "https://r2.glycogrit.com/certificates/event_1/user_123/cert_1_20240504_031500.pdf"

# Open PDF
open test_certificate.pdf  # macOS
# or
xdg-open test_certificate.pdf  # Linux
```

**Verify certificate contains:**
- ✅ Participant name (correct)
- ✅ Event name (correct)
- ✅ Activity name (correct)
- ✅ Distance covered (correct format: XX.XX km)
- ✅ Completion date (correct format: Month DD, YYYY)
- ✅ Event date (correct)
- ✅ Certificate number (format: GLCG-YYYY-EEEE-RRRRR)
- ✅ Organizer name
- ✅ Professional design (gradient background, clean layout)

---

## Step 7: Test Error Cases

### Test 7.1: Registration not found

```bash
curl -X GET "http://localhost:8000/api/v1/certificates/registration/99999" \
  -H "Authorization: Bearer $TOKEN" \
  -v
```

**Expected Response (404):**
```json
{
  "detail": "Registration not found"
}
```

### Test 7.2: Unauthorized access

```bash
# Try to access another user's certificate
curl -X GET "http://localhost:8000/api/v1/certificates/registration/2" \
  -H "Authorization: Bearer $TOKEN" \
  -v
```

**Expected Response (403):**
```json
{
  "detail": "Not authorized to access this certificate"
}
```

### Test 7.3: Registration not completed

```bash
# Create incomplete registration
# Try to generate certificate for it
curl -X GET "http://localhost:8000/api/v1/certificates/registration/{incomplete_id}" \
  -H "Authorization: Bearer $TOKEN" \
  -v
```

**Expected Response (400):**
```json
{
  "detail": "Registration {id} not completed yet"
}
```

---

## Step 8: Test "My Certificates" Endpoint

```bash
curl -X GET "http://localhost:8000/api/v1/certificates/my-certificates" \
  -H "Authorization: Bearer $TOKEN" \
  -v
```

**Expected Response:**
```json
{
  "certificates": [
    {
      "id": 1,
      "event_name": "Mumbai Marathon 2024",
      "event_id": 1,
      "certificate_url": "https://r2.glycogrit.com/...",
      "certificate_number": "GLCG-2024-0001-00001",
      "awarded_at": "2024-05-04T03:15:00",
      "delivered_at": "2024-05-04T03:15:00",
      "registration_id": 1
    }
  ],
  "total": 1
}
```

---

## Step 9: Test Bulk Generation (Admin Only)

### Get admin token first

```bash
# Login as admin
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@glycogrit.com",
    "password": "admin_password"
  }'

export ADMIN_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Trigger bulk generation

```bash
curl -X POST "http://localhost:8000/api/v1/certificates/events/1/bulk-generate" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -v
```

**Expected Response:**
```json
{
  "message": "Bulk certificate generation completed",
  "event_id": 1,
  "event_name": "Mumbai Marathon 2024",
  "total_certificates": 500,
  "successful": 495,
  "failed": 5,
  "errors": [
    "registration_id=123: No activity progress found",
    "registration_id=456: Distance not completed"
  ],
  "status": "completed"
}
```

**Check backend logs for:**
```
INFO: Starting bulk certificate generation for event_id=1
INFO: Found 500 completed registrations for event_id=1
INFO: Certificate generated for registration_id=1
INFO: Certificate generated for registration_id=2
...
INFO: Bulk generation completed: 495/500 successful, 5 failed
```

---

## Step 10: Test Certificate Statistics

```bash
curl -X GET "http://localhost:8000/api/v1/certificates/event/1/statistics" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -v
```

**Expected Response:**
```json
{
  "event_id": 1,
  "event_name": "Mumbai Marathon 2024",
  "total_registrations": 1000,
  "completed_participants": 500,
  "certificates_generated": 495,
  "pending_generation": 5,
  "completion_rate": "50.0%",
  "certificate_claim_rate": "99.0%"
}
```

---

## Step 11: Verify Database Records

```sql
-- Check certificate templates table
SELECT * FROM certificate_templates;
-- Should be empty (no custom templates yet)

-- Check user_rewards for certificates
SELECT
    ur.id,
    ur.registration_id,
    ur.certificate_number,
    ur.certificate_url,
    ur.status,
    ur.awarded_at,
    ur.delivered_at,
    u.email as user_email,
    e.name as event_name
FROM user_rewards ur
JOIN users u ON u.id = ur.user_id
JOIN events e ON e.id = ur.event_id
WHERE ur.reward_type = 'certificate'
ORDER BY ur.created_at DESC
LIMIT 10;
```

**Expected Output:**
```
 id | registration_id | certificate_number    | certificate_url           | status    | user_email
----+-----------------+----------------------+---------------------------+-----------+-------------------
  1 |               1 | GLCG-2024-0001-00001 | https://r2.glycogrit.com/ | DELIVERED | user@example.com
```

---

## Step 12: Verify R2 Storage

### Check files in R2 bucket

```bash
# Using AWS CLI (configured for R2)
aws s3 ls s3://glycogrit-events/certificates/ \
  --endpoint-url https://{ACCOUNT_ID}.r2.cloudflarestorage.com \
  --recursive
```

**Expected Output:**
```
2024-05-04 03:15:00    302145 certificates/event_1/user_123/cert_1_20240504_031500.pdf
2024-05-04 03:16:00    298763 certificates/event_1/user_124/cert_2_20240504_031600.pdf
```

### Verify public access

```bash
# Try downloading without authentication
curl -I "https://r2.glycogrit.com/certificates/event_1/user_123/cert_1_20240504_031500.pdf"
```

**Expected Response:**
```
HTTP/1.1 200 OK
Content-Type: application/pdf
Content-Length: 302145
```

---

## Performance Benchmarks

### Measure generation time

```bash
# Time single certificate generation
time curl -X GET "http://localhost:8000/api/v1/certificates/registration/1?force_regenerate=true" \
  -H "Authorization: Bearer $TOKEN" \
  -s -o /dev/null
```

**Expected:**
```
real    0m0.350s  # ~350ms
user    0m0.010s
sys     0m0.005s
```

### Measure cached retrieval

```bash
time curl -X GET "http://localhost:8000/api/v1/certificates/registration/1" \
  -H "Authorization: Bearer $TOKEN" \
  -s -o /dev/null
```

**Expected:**
```
real    0m0.045s  # ~45ms
user    0m0.010s
sys     0m0.005s
```

---

## Troubleshooting

### Issue: PDF generation fails

**Error:**
```
ValueError: Failed to generate PDF: OSError: cannot load library 'pango'
```

**Solution (macOS):**
```bash
brew install pango cairo
```

**Solution (Ubuntu/Debian):**
```bash
sudo apt-get install libpango-1.0-0 libpangocairo-1.0-0
```

### Issue: R2 upload fails

**Error:**
```
ValueError: Failed to upload certificate: S3 error
```

**Check:**
1. R2 credentials in `.env`:
   ```
   R2_ACCOUNT_ID=...
   R2_ACCESS_KEY_ID=...
   R2_SECRET_ACCESS_KEY=...
   R2_BUCKET_NAME=glycogrit-events
   ```

2. Test R2 connection:
   ```bash
   aws s3 ls s3://glycogrit-events \
     --endpoint-url https://{ACCOUNT_ID}.r2.cloudflarestorage.com
   ```

### Issue: Database migration fails

**Error:**
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) connection failed
```

**Check:**
1. Database is running
2. DATABASE_URL in `.env` is correct
3. Database exists

### Issue: "Registration not completed yet"

**Check:**
```sql
SELECT
    r.id,
    ap.distance_completed,
    ap.target_distance,
    ap.is_completed,
    ap.completed_at
FROM registrations r
LEFT JOIN activity_progress ap ON ap.registration_id = r.id
WHERE r.id = 1;
```

**Fix:**
```sql
UPDATE activity_progress
SET
    distance_completed = target_distance + 1,
    completed_at = CURRENT_TIMESTAMP
WHERE registration_id = 1;
```

---

## Success Criteria Checklist

- [ ] Database migration runs successfully
- [ ] Backend server starts without errors
- [ ] Single certificate generation works (< 500ms)
- [ ] Certificate PDF downloads successfully
- [ ] Certificate content is accurate
- [ ] Certificate design looks professional
- [ ] Cached retrieval is instant (< 50ms)
- [ ] Regeneration creates new certificate
- [ ] "My Certificates" endpoint returns data
- [ ] Bulk generation works for admin
- [ ] Error handling works correctly
- [ ] R2 storage verification passes
- [ ] Database records are correct

---

## Next Steps After Testing

1. ✅ **Verify all tests pass**
2. ✅ **Document any issues found**
3. ✅ **Measure actual performance metrics**
4. ✅ **Start Phase 2 implementation** (Template system)
5. ✅ **Begin frontend integration**

---

**Happy Testing!** 🎉

If you encounter any issues, check the backend logs and refer to the troubleshooting section above.
