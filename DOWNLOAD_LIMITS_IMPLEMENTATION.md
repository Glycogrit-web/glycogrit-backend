# Download Limits Implementation - Complete ✅

## Overview

Added download tracking and limit enforcement to the e-certificate system with full admin controls.

---

## 🎯 Features Implemented

### 1. **Download Tracking**
- ✅ Track every certificate download
- ✅ Store download count per certificate
- ✅ Record last download timestamp
- ✅ Enforce configurable limits

### 2. **User Experience**
- ✅ Preview endpoint (no download count)
- ✅ Download endpoint (tracks count)
- ✅ Clear remaining downloads display
- ✅ Informative error messages

### 3. **Admin Controls**
- ✅ Update download limit per certificate
- ✅ Reset download count (for support cases)
- ✅ Set event-wide default limits
- ✅ Download analytics dashboard

### 4. **Special Cases**
- ✅ Admins bypass limits
- ✅ 0 = unlimited downloads
- ✅ Default limit: 10 downloads

---

## 📊 Database Changes

### New Fields in `user_rewards` Table

```sql
ALTER TABLE user_rewards ADD COLUMN:
- download_count INTEGER DEFAULT 0
- download_limit INTEGER DEFAULT 10
- last_downloaded_at TIMESTAMP

CREATE INDEX idx_user_rewards_downloads ON user_rewards(download_count, download_limit);
```

---

## 🔧 API Endpoints

### User Endpoints

#### 1. **Preview Certificate** (No Download Tracking)
```http
GET /api/v1/certificates/registration/{id}
```

**Response:**
```json
{
  "certificate_url": "https://...",
  "certificate_number": "GLCG-2024-0001-00123",
  "download_count": 5,
  "download_limit": 10,
  "remaining_downloads": 5,
  "preview_mode": true,
  "message": "Preview mode - use /download endpoint to track downloads"
}
```

#### 2. **Download Certificate** (With Tracking) ⭐
```http
GET /api/v1/certificates/registration/{id}/download
```

**Response:**
```json
{
  "certificate_url": "https://...",
  "certificate_number": "GLCG-2024-0001-00123",
  "download_count": 6,
  "download_limit": 10,
  "remaining_downloads": 4,
  "last_downloaded_at": "2024-05-04T10:30:00Z",
  "message": "You have 4 downloads remaining"
}
```

**Error (Limit Exceeded):**
```http
HTTP 429 Too Many Requests
```
```json
{
  "detail": "Download limit exceeded. You have already downloaded this certificate 10 times (limit: 10). Please contact support if you need additional downloads."
}
```

#### 3. **Get My Certificates**
```http
GET /api/v1/certificates/my-certificates
```

**Response includes download info:**
```json
{
  "certificates": [
    {
      "id": 1,
      "event_name": "Mumbai Marathon 2024",
      "certificate_url": "https://...",
      "download_count": 5,
      "download_limit": 10,
      "remaining_downloads": 5
    }
  ]
}
```

---

### Admin Endpoints

#### 4. **Update Download Limit** (Single Certificate)
```http
PATCH /api/v1/certificates/registration/{id}/download-limit
Content-Type: application/json

{
  "new_limit": 20
}
```

**Response:**
```json
{
  "registration_id": 123,
  "certificate_number": "GLCG-2024-0001-00123",
  "old_limit": 10,
  "new_limit": 20,
  "download_count": 8,
  "remaining_downloads": 12,
  "message": "Download limit updated from 10 to 20"
}
```

**Set Unlimited:**
```json
{
  "new_limit": 0  // 0 = unlimited
}
```

#### 5. **Reset Download Count**
```http
POST /api/v1/certificates/registration/{id}/reset-downloads
```

**Response:**
```json
{
  "registration_id": 123,
  "certificate_number": "GLCG-2024-0001-00123",
  "old_count": 10,
  "new_count": 0,
  "download_limit": 10,
  "remaining_downloads": 10,
  "message": "Download count reset from 10 to 0"
}
```

#### 6. **Set Event-Wide Default Limit**
```http
PATCH /api/v1/certificates/events/{event_id}/default-download-limit
Content-Type: application/json

{
  "default_limit": 15,
  "apply_to_existing": true  // Update existing certificates
}
```

**Response:**
```json
{
  "event_id": 1,
  "event_name": "Mumbai Marathon 2024",
  "default_download_limit": 15,
  "certificates_updated": 245,
  "applied_to_existing": true,
  "message": "Set default limit to 15, updated 245 existing certificates"
}
```

#### 7. **Download Analytics**
```http
GET /api/v1/certificates/download-analytics?event_id=1
```

**Response:**
```json
{
  "total_certificates": 500,
  "total_downloads": 2750,
  "average_downloads_per_certificate": 5.5,
  "download_distribution": {
    "0": 50,
    "1-5": 200,
    "6-10": 220,
    "11-20": 25,
    "21+": 5
  },
  "certificates_at_limit": 12,
  "limit_exceeded_rate": "2.4%",
  "event_name": "Mumbai Marathon 2024"
}
```

---

## 🎯 Usage Examples

### Scenario 1: User Downloads Certificate

```bash
# First download
curl -X GET "http://localhost:8000/api/v1/certificates/registration/123/download" \
  -H "Authorization: Bearer USER_TOKEN"

# Response: download_count=1, remaining=9

# Second download (same user, lost file)
curl -X GET "http://localhost:8000/api/v1/certificates/registration/123/download" \
  -H "Authorization: Bearer USER_TOKEN"

# Response: download_count=2, remaining=8
```

### Scenario 2: User Hits Limit

```bash
# 11th download attempt (limit is 10)
curl -X GET "http://localhost:8000/api/v1/certificates/registration/123/download" \
  -H "Authorization: Bearer USER_TOKEN"

# Response: 429 Too Many Requests
# Error: "Download limit exceeded..."
```

### Scenario 3: Admin Increases Limit

```bash
# Admin increases limit to 20
curl -X PATCH "http://localhost:8000/api/v1/certificates/registration/123/download-limit" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"new_limit": 20}'

# User can now download 10 more times
```

### Scenario 4: Admin Resets Count

```bash
# Admin resets download count (support case)
curl -X POST "http://localhost:8000/api/v1/certificates/registration/123/reset-downloads" \
  -H "Authorization: Bearer ADMIN_TOKEN"

# User's count reset to 0, gets 10 fresh downloads
```

### Scenario 5: Event Organizer Sets Limit

```bash
# Set all certificates in event to 15 downloads
curl -X PATCH "http://localhost:8000/api/v1/certificates/events/1/default-download-limit" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"default_limit": 15, "apply_to_existing": true}'

# All 500 certificates updated to 15-download limit
```

---

## 🔒 Security Features

### 1. **Authorization**
- Users can only download their own certificates
- Admins can download any certificate (bypasses limits)
- Admin endpoints require admin role

### 2. **Rate Limiting**
- Download endpoint inherits API rate limits
- Prevents rapid-fire download attempts

### 3. **Audit Trail**
```python
# Every download logged
logger.info(
    f"Certificate downloaded: registration_id={id}, "
    f"downloads={count}/{limit}"
)

# Admin actions logged
logger.info(
    f"Admin {admin_id} updated download limit for registration {id}: "
    f"{old} → {new}"
)
```

---

## 💰 Cost Impact

### Before Limits (Estimated)
```
User behavior:
- 70% download 1-5 times (normal)
- 20% download 6-15 times (multiple devices)
- 10% download 16+ times (sharing, abuse)

Average: ~8 downloads per user
Bandwidth: 150K × 8 × 300KB = 360GB/year
Cost: 360GB × $0.01/GB = $3.60/year
```

### After 10-Download Limit
```
User behavior:
- 90% stay under limit (normal use)
- 10% hit limit (get blocked or contact support)

Average: ~5.5 downloads per user
Bandwidth: 150K × 5.5 × 300KB = 247GB/year
Cost: 247GB × $0.01/GB = $2.47/year

Savings: $1.13/year (31% reduction)
```

**Trade-off:** Lower bandwidth cost vs potential support tickets

---

## 📈 Analytics Dashboard

### Key Metrics to Monitor

1. **Average Downloads per Certificate**
   - Target: 3-5 downloads
   - Alert if > 7 (potential abuse)

2. **Certificates at Limit**
   - Target: < 5%
   - Alert if > 10% (limit too low)

3. **Download Distribution**
   - Most users should be in 1-5 range
   - Few users in 11-20 range

4. **Support Tickets**
   - Track "reset download limit" requests
   - If > 1% of users, consider increasing default

---

## 🎓 Best Practices

### For Admins

**1. Setting Event Limits:**
```
Free events: 5-10 downloads
Paid events: 15-20 downloads
Premium events: 0 (unlimited)
```

**2. Handling Support Requests:**
```
User: "I've hit my limit"
Admin actions:
1. Check download history
2. If legitimate (lost files, etc): Reset count
3. If suspicious (sharing): Investigate, consider ban
4. If frequent: Increase limit to 15-20
```

**3. Monitoring:**
```
Weekly: Check analytics dashboard
Monthly: Review limit-exceeded rate
Quarterly: Adjust default limits if needed
```

### For Users

**User Education (Add to FAQ):**
```
Q: Why is there a download limit?
A: To ensure system resources are available for all users.
   10 downloads should be sufficient for normal use.

Q: What if I need more downloads?
A: Contact support. We'll review and increase if needed.

Q: How can I avoid using up downloads?
A: Save certificate to cloud storage (Google Drive, Dropbox)
   for unlimited access.
```

---

## 🧪 Testing Checklist

### Manual Testing

- [ ] User downloads certificate (count increments)
- [ ] User previews certificate (count stays same)
- [ ] User hits limit (gets 429 error)
- [ ] Admin downloads (bypasses limit)
- [ ] Admin increases limit (user can download again)
- [ ] Admin resets count (user gets fresh downloads)
- [ ] Admin sets event default (all certificates updated)
- [ ] Analytics show correct data

### Edge Cases

- [ ] Download with limit=0 (unlimited works)
- [ ] Download at exactly limit (gets blocked)
- [ ] Multiple simultaneous downloads (race condition)
- [ ] Update limit while user downloading
- [ ] Reset count with ongoing downloads

---

## 🚀 Next Steps

### Phase 2 Enhancements

1. **Soft Warnings**
   ```python
   # Warn at 80% of limit
   if download_count >= download_limit * 0.8:
       send_warning_email("You're approaching your download limit")
   ```

2. **Tiered Limits**
   ```python
   # Different limits based on registration tier
   tier_limits = {
       'bronze': 5,
       'silver': 10,
       'gold': 20,
       'platinum': 0  # unlimited
   }
   ```

3. **Time-based Resets**
   ```python
   # Reset count every 6 months
   if last_reset + timedelta(days=180) < now:
       reset_download_count()
   ```

4. **Purchase Extra Downloads**
   ```python
   # Allow users to buy more downloads
   # $1 for 5 extra downloads
   ```

---

## 📝 Migration Notes

### Running the Migration

```bash
# Activate venv
source venv/bin/activate

# Run migration
alembic upgrade head

# Verify new columns exist
psql -d glycogrit -c "SELECT download_count, download_limit, last_downloaded_at FROM user_rewards LIMIT 5;"
```

### Backfilling Existing Certificates

```sql
-- Set default values for existing certificates
UPDATE user_rewards
SET
    download_count = 0,
    download_limit = 10,
    last_downloaded_at = NULL
WHERE reward_type = 'certificate'
  AND download_count IS NULL;
```

---

## 🎯 Summary

**What Changed:**
- Added 3 fields to `user_rewards` table
- Split certificate endpoint into preview + download
- Added 4 admin control endpoints
- Added download analytics endpoint

**User Impact:**
- ✅ Can preview unlimited times (no count)
- ✅ Can download 10 times (default)
- ✅ Clear error message at limit
- ✅ Can request more from support

**Admin Impact:**
- ✅ Full control over limits
- ✅ Can reset counts easily
- ✅ Event-wide configuration
- ✅ Analytics dashboard

**Cost Impact:**
- Saves ~31% bandwidth ($1.13/year)
- May increase support load
- Net benefit: To be monitored

---

## 📞 Support Process

### Standard Response Template

```
Hi [User],

I see you've reached your certificate download limit. I've reset your
download count to give you 10 fresh downloads.

To avoid this in future, I recommend:
1. Save the certificate to Google Drive or Dropbox
2. Email it to yourself for backup
3. Print physical copies if needed

Your certificate is now available for download again.

Best regards,
GlycoGrit Support
```

---

**Implementation Complete!** ✅

Ready for testing when database is accessible.
