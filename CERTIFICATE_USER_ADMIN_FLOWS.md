# Certificate System - User & Admin Flows

**Complete Visual Guide to Certificate Generation and Management**
**Date:** May 5, 2026
**Version:** 1.0

---

## 📋 Table of Contents

1. [User Flow - Getting Certificates](#user-flow---getting-certificates)
2. [Admin Flow - Managing Certificates](#admin-flow---managing-certificates)
3. [Technical Flow - What Happens Behind the Scenes](#technical-flow---what-happens-behind-the-scenes)
4. [Support Flow - Helping Users](#support-flow---helping-users)
5. [Visual Diagrams](#visual-diagrams)

---

## 👤 USER FLOW - Getting Certificates

### Overview
Users automatically earn certificates when they complete race challenges. No admin action required - it's 100% automated!

---

### Step 1: Register for Event

**User Action:**
```
User visits website → Browses events → Selects "Mumbai Marathon 2024"
→ Chooses distance tier (5K, 10K, 21K, 42K)
→ Completes payment → Receives registration confirmation
```

**What Happens:**
```sql
-- Database creates registration
INSERT INTO registrations (user_id, event_id, tier_id, participant_name)
VALUES (789, 42, 3, 'Rahul Sharma');
-- Registration ID: 12345

-- Creates reward entry automatically
INSERT INTO user_rewards (registration_id, user_id, reward_type, status)
VALUES (12345, 789, 'certificate', 'pending');
```

**User Sees:**
```
┌─────────────────────────────────────────┐
│  ✅ Registration Successful!            │
│                                          │
│  Event: Mumbai Marathon 2024            │
│  Distance: 10K                           │
│  Registration #: MM-2024-12345          │
│                                          │
│  📍 Complete your race to earn your     │
│     certificate!                         │
└─────────────────────────────────────────┘
```

---

### Step 2: Complete Race Activity

**User Action:**
```
User tracks their run using:
- GPS app (Strava, Google Fit, etc.)
- Manual upload
- Race day tracking
```

**Example:**
```
Date: December 15, 2024
Distance: 10.2 km
Time: 58 minutes 42 seconds
Route: [GPS data]
```

**What Happens:**
```sql
-- Activity synced to backend
INSERT INTO activity_progress
(registration_id, distance_km, duration_seconds, is_completed)
VALUES (12345, 10.2, 3522, true);

-- System validates completion
-- Required: 10 km ✓
-- Actual: 10.2 km ✓
-- Status: COMPLETED ✓
```

**User Sees:**
```
┌─────────────────────────────────────────┐
│  🎉 Congratulations!                    │
│                                          │
│  You completed the 10K challenge!       │
│                                          │
│  Distance: 10.2 km                       │
│  Time: 58:42                             │
│  Pace: 5:45 min/km                       │
│                                          │
│  📜 Your certificate is ready!          │
│  [ Download Certificate ]               │
└─────────────────────────────────────────┘
```

---

### Step 3: Download Certificate (First Time)

**User Action:**
```
User clicks: "Download Certificate"
```

**UI Shows:**
```
┌─────────────────────────────────────────┐
│  Generating your certificate...         │
│  ⏳ Please wait...                      │
└─────────────────────────────────────────┘
```

**Backend Processing (500ms):**

```
Step 1: Check if certificate exists
  └─> Query: SELECT certificate_url FROM user_rewards WHERE registration_id = 12345
  └─> Result: NULL (first time)

Step 2: Fetch user and event data
  └─> Participant: "Rahul Sharma"
  └─> Event: "Mumbai Marathon 2024"
  └─> Distance: "10K"
  └─> Completion Date: "December 15, 2024"

Step 3: Generate unique certificate number
  └─> Format: GLCG-YYYY-EEEE-RRRRR
  └─> Result: GLCG-2024-0042-12345
      ├─> GLCG = GlycoGrit prefix
      ├─> 2024 = Year
      ├─> 0042 = Event ID (padded)
      └─> 12345 = Registration ID (padded)

Step 4: Load HTML template
  └─> Uses default embedded Jinja2 template
  └─> Contains: Certificate design, borders, logo placeholders

Step 5: Fill template with data
  └─> Replace {{participant_name}} → "Rahul Sharma"
  └─> Replace {{event_name}} → "Mumbai Marathon 2024"
  └─> Replace {{distance}} → "10 Kilometers"
  └─> Replace {{date}} → "December 15, 2024"
  └─> Replace {{certificate_number}} → "GLCG-2024-0042-12345"

Step 6: Generate PDF using WeasyPrint
  └─> HTML → PDF conversion
  └─> Time: ~300ms
  └─> Size: ~300KB

Step 7: Upload to Cloudflare R2
  └─> Path: certificates/events/42/registration-12345.pdf
  └─> URL: https://r2.glycogrit.com/certificates/events/42/registration-12345.pdf
  └─> Cache: 1 year

Step 8: Save to database
  └─> UPDATE user_rewards SET
        certificate_url = 'https://r2.glycogrit.com/...',
        certificate_number = 'GLCG-2024-0042-12345',
        download_count = 1,
        last_downloaded_at = NOW(),
        reward_status = 'issued'

Step 9: Return to user
  └─> Total time: ~500ms
```

**User Sees:**
```
✅ Certificate downloaded successfully!

Certificate opens in new tab:

┌─────────────────────────────────────────────────┐
│                                                  │
│           CERTIFICATE OF COMPLETION              │
│                                                  │
│      This is to certify that                     │
│                                                  │
│            Rahul Sharma                          │
│                                                  │
│      has successfully completed                  │
│                                                  │
│        Mumbai Marathon 2024                      │
│           10 Kilometers                          │
│                                                  │
│      on December 15, 2024                        │
│                                                  │
│   Certificate No: GLCG-2024-0042-12345          │
│                                                  │
└─────────────────────────────────────────────────┘

Downloads: 1/10 remaining
```

---

### Step 4: Re-Download Certificate

**User Action:**
```
User loses PDF → Returns to app → Clicks "Download Certificate" again
```

**Backend Processing (50ms - Fast!):**

```
Step 1: Check if certificate exists
  └─> Query: SELECT certificate_url FROM user_rewards WHERE registration_id = 12345
  └─> Result: "https://r2.glycogrit.com/..." (EXISTS!)

Step 2: Check download limit
  └─> download_count = 1
  └─> download_limit = 10
  └─> 1 < 10 ✓ (ALLOWED)

Step 3: Increment download count
  └─> UPDATE user_rewards SET
        download_count = 2,
        last_downloaded_at = NOW()

Step 4: Return cached URL
  └─> No PDF generation needed!
  └─> Total time: ~50ms
```

**User Sees:**
```
✅ Certificate downloaded! 8 downloads remaining.

Same PDF opens in new tab
Downloads: 2/10 remaining
```

---

### Step 5: Check All My Certificates

**User Action:**
```
User navigates to: "My Certificates" page
```

**Backend Processing:**

```
GET /api/v1/certificates/my-certificates

Query:
SELECT
  r.id as registration_id,
  e.name as event_name,
  e.event_date,
  t.name as distance,
  ur.certificate_url,
  ur.certificate_number,
  ur.download_count,
  ur.download_limit,
  ur.last_downloaded_at
FROM user_rewards ur
JOIN registrations r ON ur.registration_id = r.id
JOIN events e ON r.event_id = e.id
JOIN tiers t ON r.tier_id = t.id
WHERE ur.user_id = 789
  AND ur.reward_type = 'certificate'
  AND ur.certificate_url IS NOT NULL
ORDER BY e.event_date DESC
```

**User Sees:**

```
┌─────────────────────────────────────────────────────────┐
│                                                          │
│  📜 My Certificates                                     │
│  You have earned 3 certificates                         │
│                                                          │
│  ┌─────────────────────┐  ┌─────────────────────┐     │
│  │ 📜 Mumbai Marathon  │  │ 📜 Delhi Half       │     │
│  │    2024             │  │    Marathon 2024    │     │
│  │                     │  │                     │     │
│  │ 10K                 │  │ 21K                 │     │
│  │ Dec 15, 2024        │  │ Oct 20, 2024        │     │
│  │                     │  │                     │     │
│  │ GLCG-2024-0042-12345│  │ GLCG-2024-0038-11234│     │
│  │                     │  │                     │     │
│  │ Downloads: 2/10     │  │ Downloads: 10/10    │     │
│  │ [█████░░░░░] 20%    │  │ [██████████] 100%   │     │
│  │                     │  │                     │     │
│  │ [ Download Again ]  │  │ [ Limit Reached ]   │     │
│  └─────────────────────┘  └─────────────────────┘     │
│                                                          │
│  ┌─────────────────────┐                                │
│  │ 📜 Bangalore Ultra  │                                │
│  │    2024             │                                │
│  │                     │                                │
│  │ 50K                 │                                │
│  │ Aug 12, 2024        │                                │
│  │                     │                                │
│  │ GLCG-2024-0035-10123│                                │
│  │                     │                                │
│  │ Downloads: 2/∞      │                                │
│  │ Unlimited           │                                │
│  │                     │                                │
│  │ [ Download Again ]  │                                │
│  └─────────────────────┘                                │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

### Step 6: Hit Download Limit

**User Action:**
```
User downloads certificate 10 times → Tries 11th download
```

**Backend Processing:**

```
Step 1: Check download limit
  └─> download_count = 10
  └─> download_limit = 10
  └─> 10 >= 10 ✗ (LIMIT EXCEEDED)

Step 2: Reject request
  └─> HTTP 429 Too Many Requests
  └─> Error: "Download limit exceeded"
```

**User Sees:**

```
┌─────────────────────────────────────────┐
│  ⚠️  Download Limit Reached             │
│                                          │
│  You've downloaded this certificate     │
│  10 times (maximum allowed).            │
│                                          │
│  Need more downloads?                   │
│                                          │
│  Please contact support:                │
│  support@glycogrit.com                  │
│                                          │
│  [ Contact Support ]                    │
└─────────────────────────────────────────┘
```

---

## 👔 ADMIN FLOW - Managing Certificates

### Overview
Admins monitor certificate downloads, manage limits, and handle user requests. No need to create certificates manually!

---

### Admin Action 1: View Certificate Analytics

**Admin Navigates:**
```
Admin Dashboard → Certificate Analytics
```

**What Admin Sees:**

```
┌──────────────────────────────────────────────────────────────┐
│                                                               │
│  📊 Certificate Analytics - Mumbai Marathon 2024            │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Total Certs  │  │ Downloads    │  │ At Limit     │      │
│  │    245       │  │   1,127      │  │    12        │      │
│  │              │  │ Avg: 4.6     │  │   4.9%       │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌──────────────┐                                            │
│  │ Bandwidth    │   Event Details:                          │
│  │  84.5 MB     │   • Total Registrations: 1,250           │
│  │ ₹127.50/mo   │   • Completed Activities: 987            │
│  └──────────────┘   • Completion Rate: 78.9%               │
│                                                               │
│  📈 Download Distribution:                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 0-3 downloads    │ ████████████████ 89 users       │   │
│  │ 4-6 downloads    │ ██████████████████████ 134 users│   │
│  │ 7-9 downloads    │ ████ 10 users                   │   │
│  │ 10+ downloads    │ █████ 12 users (AT LIMIT)       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  🔝 Top Downloaders:                                        │
│  ┌───────────────┬──────────────────┬───────────┬─────────┐│
│  │ Participant   │ Certificate #    │ Downloads │ Status  ││
│  ├───────────────┼──────────────────┼───────────┼─────────┤│
│  │ Rahul Sharma  │ GLCG-2024-...-01 │   10/10   │ 🔴 Max  ││
│  │ Priya Desai   │ GLCG-2024-...-02 │    9/10   │ 🟡 High ││
│  │ Amit Kumar    │    8/10   │ 🟢 OK   ││
│  └───────────────┴──────────────────┴───────────┴─────────┘│
│                                                               │
│  [ Export Report ] [ Refresh Data ]                         │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

**API Call:**
```http
GET /api/v1/certificates/download-analytics?event_id=42
Authorization: Bearer ADMIN_TOKEN
```

**Response:**
```json
{
  "event_id": 42,
  "event_name": "Mumbai Marathon 2024",
  "total_certificates": 245,
  "total_downloads": 1127,
  "average_downloads_per_certificate": 4.6,
  "certificates_at_limit": 12,
  "certificates_at_limit_percentage": 4.9,
  "download_distribution": {
    "0-3": 89,
    "4-6": 134,
    "7-9": 10,
    "10+": 12
  },
  "bandwidth_used_mb": 84.5,
  "estimated_monthly_cost": "₹127.50"
}
```

---

### Admin Action 2: User Requests More Downloads

**Scenario:**
```
User contacts support: "I need to download my certificate again but I've
reached the limit. I lost the PDF file."
```

**Admin Steps:**

**Step 1: Verify User Identity**

```
Admin asks user for:
├─ Registered email: rahul.sharma@example.com
├─ Registration number: MM-2024-12345
└─ Event name: Mumbai Marathon 2024
```

**Step 2: Search for Certificate**

```
Admin Dashboard → Certificate Management → Search

Search query: "rahul.sharma@example.com" OR "MM-2024-12345"
```

**What Admin Sees:**

```
┌──────────────────────────────────────────────────────────┐
│                                                           │
│  🔍 Certificate Details                                  │
│                                                           │
│  Registration #: MM-2024-12345 (ID: 12345)              │
│  Participant: Rahul Sharma                               │
│  Email: rahul.sharma@example.com                         │
│  Event: Mumbai Marathon 2024                             │
│  Distance: 10K                                           │
│                                                           │
│  📜 Certificate: GLCG-2024-0042-12345                   │
│  Status: Issued                                          │
│                                                           │
│  📊 Download Stats:                                      │
│  Downloads: 10/10 🔴 LIMIT REACHED                      │
│  Last Download: Dec 16, 2024 10:30 AM                   │
│                                                           │
│  ⚙️ Actions:                                            │
│  ┌─────────────────────────────────────────┐           │
│  │ Reset Download Count                     │           │
│  │ (Reset to 0, keeps limit at 10)         │           │
│  │ [ Reset Count ]                          │           │
│  └─────────────────────────────────────────┘           │
│                                                           │
│  ┌─────────────────────────────────────────┐           │
│  │ Increase Download Limit                  │           │
│  │ New Limit: [20 ▼]                        │           │
│  │ [ Update Limit ]                         │           │
│  └─────────────────────────────────────────┘           │
│                                                           │
│  ┌─────────────────────────────────────────┐           │
│  │ Set Unlimited Downloads                  │           │
│  │ (For VIP/Press use)                      │           │
│  │ [ Set Unlimited ]                        │           │
│  └─────────────────────────────────────────┘           │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

**Step 3: Admin Takes Action (Option A - Reset Count)**

```
Admin clicks: "Reset Count"
Confirmation: "Reset download count for Rahul Sharma?"
Admin clicks: "Yes, Reset"
```

**API Call:**
```http
POST /api/v1/certificates/registration/12345/reset-downloads
Authorization: Bearer ADMIN_TOKEN
```

**Backend Processing:**
```sql
UPDATE user_rewards
SET download_count = 0,
    last_downloaded_at = NULL
WHERE registration_id = 12345;
```

**Response:**
```json
{
  "message": "Download count reset successfully",
  "registration_id": 12345,
  "previous_count": 10,
  "new_count": 0,
  "download_limit": 10,
  "reset_by": "admin@glycogrit.com",
  "reset_at": "2024-12-17T09:15:00Z"
}
```

**Admin Sees:**
```
✅ Download count reset successfully!
   Rahul Sharma can now download 10 more times.
```

**Step 3: Admin Takes Action (Option B - Increase Limit)**

```
Admin selects: "New Limit: 20"
Admin clicks: "Update Limit"
```

**API Call:**
```http
PATCH /api/v1/certificates/registration/12345/download-limit
Authorization: Bearer ADMIN_TOKEN
Content-Type: application/json

{
  "new_limit": 20
}
```

**Backend Processing:**
```sql
UPDATE user_rewards
SET download_limit = 20
WHERE registration_id = 12345;
-- download_count stays at 10
-- User now has 10 more downloads available
```

**Response:**
```json
{
  "message": "Download limit updated successfully",
  "registration_id": 12345,
  "previous_limit": 10,
  "new_limit": 20,
  "download_count": 10
}
```

**Admin Sees:**
```
✅ Download limit increased to 20!
   Rahul Sharma now has 10 downloads remaining (10/20).
```

**Step 4: Notify User**

```
Admin → Support System → Email User

Subject: Certificate Download Limit Updated

Hi Rahul,

Your certificate download limit has been reset/increased.
You can now download your certificate again.

Certificate: Mumbai Marathon 2024
Certificate #: GLCG-2024-0042-12345
Downloads Available: 10 remaining

Download here: [Link to My Certificates page]

Best regards,
GlycoGrit Support Team
```

---

### Admin Action 3: Bulk Update for Premium Event

**Scenario:**
```
Admin decides: "Premium event participants should get 20 downloads
instead of 10"
```

**Admin Steps:**

**Step 1: Navigate to Event Settings**

```
Admin Dashboard → Events → Mumbai Marathon 2024 → Certificate Settings
```

**What Admin Sees:**

```
┌──────────────────────────────────────────────────────────┐
│                                                           │
│  ⚙️ Certificate Settings - Mumbai Marathon 2024         │
│                                                           │
│  Event Type: Premium                                     │
│  Total Participants: 1,250                               │
│  Certificates Issued: 245                                │
│                                                           │
│  📊 Current Settings:                                    │
│  Default Download Limit: 10                              │
│                                                           │
│  💫 Update Download Limits:                             │
│  ┌─────────────────────────────────────────┐           │
│  │ New Default Limit: [20 ▼]               │           │
│  │                                          │           │
│  │ ☑ Apply to existing certificates        │           │
│  │   (Updates all 245 issued certificates) │           │
│  │                                          │           │
│  │ ⚠️ This action affects:                 │           │
│  │   • 245 existing certificates           │           │
│  │   • All future certificates             │           │
│  │                                          │           │
│  │ [ Cancel ] [ Update Limits ]            │           │
│  └─────────────────────────────────────────┘           │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

**Step 2: Apply Changes**

```
Admin:
1. Selects "New Default Limit: 20"
2. Checks "Apply to existing certificates"
3. Clicks "Update Limits"
```

**Confirmation Dialog:**
```
┌──────────────────────────────────────────┐
│  ⚠️ Confirm Bulk Update                  │
│                                           │
│  You are about to update:                │
│  • 245 existing certificates             │
│  • Default for future certificates       │
│                                           │
│  New limit: 20 downloads                 │
│                                           │
│  This cannot be undone.                  │
│                                           │
│  [ Cancel ] [ Yes, Update All ]          │
└──────────────────────────────────────────┘
```

**API Call:**
```http
PATCH /api/v1/certificates/events/42/default-download-limit
Authorization: Bearer ADMIN_TOKEN
Content-Type: application/json

{
  "default_limit": 20,
  "apply_to_existing": true
}
```

**Backend Processing:**
```sql
-- Update event default
UPDATE events
SET certificate_download_limit = 20
WHERE id = 42;

-- Update all existing certificates for this event
UPDATE user_rewards
SET download_limit = 20
WHERE registration_id IN (
  SELECT id FROM registrations WHERE event_id = 42
)
AND reward_type = 'certificate';
-- Affected rows: 245
```

**Response:**
```json
{
  "message": "Download limits updated successfully",
  "event_id": 42,
  "new_default_limit": 20,
  "certificates_updated": 245
}
```

**Admin Sees:**
```
✅ Download limits updated successfully!

Event: Mumbai Marathon 2024
New Default: 20 downloads
Certificates Updated: 245

All participants now have increased download limits.
```

---

### Admin Action 4: Set VIP Unlimited Downloads

**Scenario:**
```
VIP participant needs unlimited downloads for media/press use
```

**Admin Steps:**

```
1. Search for participant: "celebrity.runner@example.com"
2. View certificate details
3. Click "Set Unlimited"
4. Add note: "VIP - Press/Media use"
```

**API Call:**
```http
PATCH /api/v1/certificates/registration/12345/download-limit
Authorization: Bearer ADMIN_TOKEN
Content-Type: application/json

{
  "new_limit": 0
}
```

**Note:** `0` means unlimited downloads

**Backend Processing:**
```sql
UPDATE user_rewards
SET download_limit = 0
WHERE registration_id = 12345;
-- 0 = unlimited, no limit check performed
```

**Admin Sees:**
```
✅ Set to unlimited downloads!

Participant can download certificate unlimited times.
Download count will still be tracked for analytics.
```

---

## 🔧 TECHNICAL FLOW - What Happens Behind the Scenes

### Database State Changes

**Initial State (After Registration):**
```sql
user_rewards table:
┌────┬────────────────┬─────────────────┬───────────────┬───────────┐
│ id │ registration_id│ reward_type     │ reward_status │ cert_url  │
├────┼────────────────┼─────────────────┼───────────────┼───────────┤
│ 1  │ 12345          │ certificate     │ pending       │ NULL      │
└────┴────────────────┴─────────────────┴───────────────┴───────────┘
```

**After First Download:**
```sql
user_rewards table:
┌────┬────────────────┬─────────────┬───────────────┬─────────────────────────┬──────────────────┬────────────┬────────────┐
│ id │ registration_id│ reward_type │ reward_status │ certificate_url         │ certificate_num  │ down_count │ down_limit │
├────┼────────────────┼─────────────┼───────────────┼─────────────────────────┼──────────────────┼────────────┼────────────┤
│ 1  │ 12345          │ certificate │ issued        │ https://r2.glycogrit... │ GLCG-2024-...    │ 1          │ 10         │
└────┴────────────────┴─────────────┴───────────────┴─────────────────────────┴──────────────────┴────────────┴────────────┘
```

**After Multiple Downloads:**
```sql
user_rewards table:
┌────┬────────────────┬────────────┬────────────┬─────────────────────┐
│ id │ registration_id│ down_count │ down_limit │ last_downloaded_at  │
├────┼────────────────┼────────────┼────────────┼─────────────────────┤
│ 1  │ 12345          │ 5          │ 10         │ 2024-12-16 10:30:00 │
└────┴────────────────┴────────────┴────────────┴─────────────────────┘
```

**At Download Limit:**
```sql
user_rewards table:
┌────┬────────────────┬────────────┬────────────┬─────────┐
│ id │ registration_id│ down_count │ down_limit │ Status  │
├────┼────────────────┼────────────┼────────────┼─────────┤
│ 1  │ 12345          │ 10         │ 10         │ 🔴 MAX  │
└────┴────────────────┴────────────┴────────────┴─────────┘
```

---

### API Request Flow

**User Download Request:**
```
User Browser
    ↓ (HTTP GET)
API Gateway
    ↓ (Route)
/api/v1/certificates/registration/12345/download
    ↓ (Authenticate)
JWT Token Validation
    ↓ (Authorize)
Check: User owns registration?
    ↓ (Generate if needed)
CertificateService.generate_certificate()
    ↓ (Track download)
CertificateService.track_download()
    ↓ (Check limit)
download_count < download_limit?
    ↓ (Return)
Certificate URL + Stats
    ↓ (Response)
User Browser opens PDF
```

---

## 🆘 SUPPORT FLOW - Helping Users

### Common Support Scenarios

#### Scenario 1: "I can't download my certificate"

**Possible Causes:**
1. Activity not completed
2. Download limit exceeded
3. Technical error

**Support Agent Steps:**

```
Step 1: Verify completion
  └─> Check: activity_progress.is_completed = true?

Step 2: Check certificate status
  └─> Query user_rewards table
  └─> certificate_url exists?

Step 3: Check download limit
  └─> download_count vs download_limit

Step 4: Take action
  ├─> If incomplete: "Please complete the activity first"
  ├─> If at limit: Reset count or increase limit
  └─> If technical: Check logs, regenerate if needed
```

#### Scenario 2: "My certificate shows wrong information"

**Support Agent Steps:**

```
Step 1: Verify complaint
  └─> Ask user: What information is incorrect?

Step 2: Check source data
  └─> registration table: participant_name, tier
  └─> events table: event name, date
  └─> activity_progress: distance, time

Step 3: If data is correct
  └─> Regenerate certificate with force flag
  └─> POST /api/v1/certificates/registration/{id}/regenerate

Step 4: If data is incorrect
  └─> Update source data first
  └─> Then regenerate certificate
```

#### Scenario 3: "I need certificate for corporate reimbursement"

**Support Agent Steps:**

```
Step 1: Verify legitimacy
  └─> Check user completed activity

Step 2: If at download limit
  └─> Increase limit or reset count

Step 3: Provide download link
  └─> Direct link to certificate
  └─> Or guide to "My Certificates" page

Step 4: Optional
  └─> Set unlimited downloads for business users
```

---

## 📊 VISUAL DIAGRAMS

### Complete System Flow

```
┌─────────────┐
│   USER      │
│ Registers   │
│ for Event   │
└──────┬──────┘
       │
       ↓
┌──────────────────┐
│  REGISTRATION    │
│  Entry Created   │
│  reward_type =   │
│  'certificate'   │
└──────┬───────────┘
       │
       ↓
┌──────────────────┐
│   USER           │
│ Completes Race   │
│ (GPS tracking)   │
└──────┬───────────┘
       │
       ↓
┌──────────────────────┐
│  ACTIVITY PROGRESS   │
│  is_completed = true │
└──────┬───────────────┘
       │
       ↓
┌──────────────────────┐
│   USER               │
│ Clicks Download      │
│ Certificate Button   │
└──────┬───────────────┘
       │
       ↓
┌──────────────────────┐      ┌─────────────────┐
│  BACKEND CHECK       │─────>│ Certificate     │
│  Does cert exist?    │      │ exists?         │
└──────┬───────────────┘      └────────┬────────┘
       │ NO                            │ YES
       ↓                               ↓
┌──────────────────────┐      ┌────────────────┐
│  GENERATE            │      │ RETURN CACHED  │
│  1. Fetch data       │      │ URL (~50ms)    │
│  2. Create PDF       │      └────────────────┘
│  3. Upload R2        │
│  4. Save URL         │
│  (~500ms)            │
└──────┬───────────────┘
       │
       ↓
┌──────────────────────┐
│  TRACK DOWNLOAD      │
│  1. Check limit      │
│  2. Increment count  │
│  3. Return URL       │
└──────┬───────────────┘
       │
       ↓
┌──────────────────────┐
│   USER               │
│ Opens PDF in         │
│ new tab              │
└──────────────────────┘
```

### Admin Management Flow

```
┌─────────────┐
│   ADMIN     │
│ Dashboard   │
└──────┬──────┘
       │
       ├────────────────┬─────────────────┬──────────────────┐
       ↓                ↓                 ↓                  ↓
┌─────────────┐  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐
│ View        │  │ Reset       │  │ Increase     │  │ Bulk Update  │
│ Analytics   │  │ Download    │  │ Limit        │  │ Event Limits │
│             │  │ Count       │  │              │  │              │
│ • Total     │  │             │  │              │  │              │
│ • Downloads │  │ Count = 0   │  │ Limit = 20   │  │ All certs    │
│ • At Limit  │  │             │  │              │  │ in event     │
│ • Bandwidth │  │             │  │              │  │              │
└─────────────┘  └─────────────┘  └──────────────┘  └──────────────┘
```

---

## 🎯 QUICK REFERENCE

### User Journey Summary

```
Register → Complete Activity → Download Certificate → Re-download if needed
   ↓            ↓                    ↓                      ↓
Database    Database          Generate PDF           Use cached URL
 entry      validation        (~500ms first)         (~50ms after)
```

### Admin Actions Summary

```
Monitor Analytics → Handle Support Requests → Update Limits → Bulk Management
      ↓                    ↓                       ↓               ↓
  View stats       Reset count/            Individual         Event-wide
  Track usage      Increase limit         certificate        settings
```

### Key Concepts

1. **Automatic**: Certificates auto-generate on first download
2. **Cached**: Once generated, reused for subsequent downloads
3. **Tracked**: Every download is counted
4. **Limited**: Default 10 downloads, customizable
5. **Managed**: Admins have full control

---

**System Status:** ✅ Production Ready
**User Experience:** ✅ Automated and Seamless
**Admin Control:** ✅ Full Management Capabilities

**Last Updated:** May 5, 2026
