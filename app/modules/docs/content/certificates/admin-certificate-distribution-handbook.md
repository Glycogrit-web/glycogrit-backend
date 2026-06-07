# Certificate Distribution Handbook for Admins

## Overview
This comprehensive guide walks you through distributing certificates to event participants using Google Sheets + Autocrat for bulk certificate generation.

## Prerequisites
- Admin access to the GlycoGrit platform
- Google Workspace account
- Autocrat add-on installed in Google Sheets
- Certificate template designed in Google Slides

---

## Complete Workflow

### Step 1: Export Participant Data

1. Log in to admin panel
2. Navigate to **Events → Select your event → Edit**
3. Scroll to **"Post-Event Management"** section
4. Click **"📥 Export Registrations CSV"**
5. Save the CSV file (e.g., `registrations-mothers-day-2024.csv`)

**CSV Columns Included:**
- Registration ID, Registration Number, BIB Number
- **Email** ← Critical for Autocrat matching
- Participant Name, Age, Gender, T-Shirt Size
- Status, Payment details, Shipping information

---

### Step 2: Set Up Google Sheets

1. Open Google Sheets
2. Create new spreadsheet: `Event Name - Certificates`
3. **File → Import → Upload** your CSV from Step 1
4. Verify the **Email** column exists (usually Column D)

---

### Step 3: Design Certificate Template in Google Slides

1. Open Google Slides → Create new presentation (16:9 aspect ratio)
2. Design your certificate layout
3. Add **dynamic fields** using double curly braces:
   - `{{Email}}` - Participant email (for matching)
   - `{{Participant Name}}` - Full name
   - `{{Registration Number}}` - Registration #
   - `{{event_name}}` - Event name
   - `{{date}}` - Current date
   - `{{BIB Number}}` - BIB number if applicable

4. Save the slide (e.g., "Certificate Template - Mothers Day 2024")

**Tips:**
- Use readable fonts (minimum 24pt for names)
- Keep field names **lowercase** and match CSV column headers
- Test with sample data before bulk generation

---

### Step 4: Install and Configure Autocrat

1. In Google Sheet: **Extensions → Add-ons → Get add-ons**
2. Search "**Autocrat**" → Install (free tool)
3. **Extensions → Autocrat → Launch**
4. Click **"New Job"** → Name: "Generate Certificates"

**Configuration Steps:**

**Step 1 - Template Source:**
- Click **"From Drive"**
- Select your Slides template from Step 3

**Step 2 - Field Mappings:**
- Map template tags to sheet columns:
  - `{{Email}}` → `Email` column
  - `{{Participant Name}}` → `Participant Name` column
  - `{{Registration Number}}` → `Registration Number` column
  - (Map all other fields similarly)

**Step 3 - Output Settings:**
- **File type**: Select **PDF**
- **Filename pattern**: `{{Participant Name}} - Certificate`
- **Output mode**: Multiple output mode
- **Destination folder**: Click "Choose folder"
  - Create new folder: "Certificates - [Event Name] - [Date]"
  - Select this folder
- **File sharing**: **"Anyone with the link can view"** ← **CRITICAL!**

**Step 4 - Merge Conditions** (Optional):
- Skip or add filters (e.g., only generate for "Confirmed" status)

**Step 5 - Share & Email:**
- Select **"No"** (we'll distribute via platform, not email)

Click **Save**

---

### Step 5: Run Autocrat to Generate Certificates

1. In Autocrat sidebar, find your job
2. Click **▶ Run** button
3. Wait for processing (progress bar shows status)
   - For 100 participants: ~2-3 minutes
   - For 500+ participants: ~10-15 minutes

4. **Result**: New columns appear in your sheet:
   - `Status` (shows "Sent")
   - **`Merge Doc URL`** ← This is the certificate Google Drive link!

**Example Merge Doc URL:**
```
https://drive.google.com/file/d/1zAbC123dEfGh456IjKlM789nOpQr012/view
```

**Verify Success:**
- Open a few certificate links to check quality
- Ensure names, dates, and formatting are correct
- If errors found, fix template and re-run Autocrat

### 📋 Column Name Flexibility

The system uses **intelligent pattern matching** to find certificate URLs in your uploaded CSV/XLSX file. This makes it compatible with various Autocrat configurations.

**Supported Column Name Patterns:**

| Priority | Pattern | Example Column Names | Match Type |
|----------|---------|---------------------|------------|
| 1 (Highest) | "Merged Doc URL" | "Merged Doc URL"<br>"Merged Doc URL - Auto Certificate"<br>"Merged Doc URL - Custom" | Substring |
| 2 | "Link to merged" | "Link to merged Doc"<br>"Link to merged Doc - Auto Certificate" | Substring |
| 3 (Lowest) | "Certificate URL" | "Certificate URL" (exact) | Exact match |

**How Pattern Matching Works:**

1. **Checks all columns** in your CSV file
2. **Identifies matches** using patterns above (case-insensitive)
3. **Prioritizes Autocrat columns** over generic system columns
4. **Selects best match** based on pattern priority

**Example Scenario:**

Your exported CSV contains both:
- Column 26: "Certificate URL" (empty - from system export)
- Column 31: "Merged Doc URL - Auto Certificate" (populated - from Autocrat)

✅ **System correctly selects Column 31** (Autocrat column with URLs)
❌ System does NOT select Column 26 (empty generic column)

**Why This Matters:**

When you export participant data from GlycoGrit and then merge it with Autocrat-generated certificates, the resulting file contains BOTH the system's empty "Certificate URL" column AND Autocrat's populated "Merged Doc URL - Auto Certificate" column. The intelligent pattern matching ensures the system always picks the right one.

**Troubleshooting:**

If certificates aren't being imported:
1. Check backend logs for "📋 Found certificate URL column" message
2. Verify the matched column name in logs
3. Ensure at least one pattern matches your Autocrat column name
4. Confirm the matched column contains actual URLs (not empty)

---

### Step 6: Grant Backend Access to Google Drive

**⚠️ ONE-TIME SETUP PER EVENT**

Your backend needs read access to the certificate folder via a Service Account.

1. Open the Google Drive folder where certificates were saved
2. Click **Share** button (top right)
3. In "Add people and groups" field, enter:
   ```
   glycogrit-service@glycogrit-backend.iam.gserviceaccount.com
   ```
   (Get actual service account email from tech team)
4. Set permission: **Viewer** (read-only)
5. **Uncheck** "Notify people" (it's a service account)
6. Click **Done**

**Security Notes:**
- Service account has **read-only** access
- Folder remains private to your team
- Users never access Drive directly

---

### Step 7: Export Enhanced CSV with Certificate URLs

1. In your Google Sheet, **select all columns** including:
   - Email column
   - Merged Doc URL column (new column from Autocrat)
   - All other columns

2. **File → Download → Comma Separated Values (.csv)**
3. Save as: `certificates-[event-name]-[date].csv`

**Verify CSV has these columns:**
- `Email` (required)
- `Merged Doc URL` (required)
- Other columns are optional but helpful for verification

---

### Step 8: Upload CSV to Platform

1. Return to admin panel → Event edit page
2. Scroll to **"Post-Event Management"** section
3. Find **"Upload Certificate URLs"**
4. Click **Choose File** → Select your CSV from Step 7
5. Click **Upload** button

**Processing Results Display:**
```
✅ Processed: 95/100
❌ Failed: 3
⚠️  User not found: 2

[View Errors]
Row 45: User not found - user@example.com
Row 67: Empty email or URL
Row 89: No registration found for event
```

**Common Errors & Fixes:**
- **"User not found"**: Email in CSV doesn't match registered email
  - Check for typos, case differences, extra spaces
  - User may have registered with different email
- **"No registration found"**: User exists but didn't register for this event
  - Verify event ID matches
- **"Empty email or URL"**: Missing data in CSV row
  - Check Autocrat ran successfully for all rows

---

### Step 9: Quality Check & Unlock Certificates

**⚠️ IMPORTANT: Certificates are locked by default until admin approval**

1. In Post-Event Management section, click **"🔓 Manage Certificate Access"**
2. Modal opens showing all participants with certificates:

| ☑ | Registration # | Name | Email | Status |
|---|----------------|------|-------|--------|
| ☑ | EVT31-ABC123 | John Doe | john@example.com | 🔒 Locked |
| ☑ | EVT31-DEF456 | Jane Smith | jane@example.com | 🔒 Locked |

3. **Quality Check** (CRITICAL):
   - Click on a few certificate URLs to review
   - Verify formatting, spelling, data accuracy
   - Check all dynamic fields populated correctly
   - Ensure PDF quality is acceptable

4. **Select Participants**:
   - Check individual boxes, OR
   - Click "Select All" checkbox (top left)

5. Click **"Unlock Selected (95)"** button
6. Confirm action in dialog

**Result**: Certificates are now available for users to download!

---

### Step 10: Notify Participants

Send notification via email/WhatsApp/platform:

**Email Template:**
```
Subject: 🎉 Your [Event Name] Certificate is Ready!

Hi [Name],

Congratulations on completing the [Event Name]!

Your participation certificate is now available for download.

👉 Download Your Certificate:
Log in to your GlycoGrit dashboard → My Rewards → Download Certificate

Certificate Features:
✅ Official PDF certificate
✅ Personalized with your name and details
✅ Download anytime
✅ Share on LinkedIn, Instagram, or print it!

Questions? Reply to this email or contact support.

Keep running! 🏃‍♂️
The GlycoGrit Team
```

**WhatsApp Template:**
```
🎉 [Name], your [Event Name] certificate is ready!

Download it now from your dashboard:
https://glycogrit.com/rewards

Congrats on completing the challenge! 🏅
```

---

## Troubleshooting Guide

### Issue: "User not found" in CSV upload

**Cause**: Email in CSV doesn't match any registered user

**Solutions:**
1. Check for typos in email addresses
2. Look for extra spaces (trim whitespace)
3. Verify case sensitivity (usually case-insensitive but check)
4. User may have registered with different email - cross-reference registration records

### Issue: "Certificate not available" when user tries to download

**Causes & Fixes:**
1. **Not unlocked yet**
   - Go to Manage Certificate Access modal
   - Verify certificate is unlocked
2. **Google Drive permissions missing**
   - Verify service account has Viewer access to folder
   - Re-share folder with service account
3. **Invalid Drive URL**
   - Check Autocrat ran successfully
   - Verify Merge Doc URL column has valid links

### Issue: Google Drive shows "Access Denied"

**Cause**: Service account not added to folder permissions or wrong permission level

**Fix:**
1. Go to Google Drive folder
2. Click Share
3. Add service account email with **Viewer** permission
4. Ensure "Anyone with the link" is NOT enabled (keep folder private)

### Issue: Autocrat didn't generate certificates

**Causes & Fixes:**
1. **Template not found**
   - Verify template is accessible in your Drive
   - Check sharing permissions on template
2. **Field mapping errors**
   - Re-check field mappings in Autocrat
   - Ensure tag names match exactly (case-sensitive)
3. **Quota exceeded**
   - Google has daily limits on Drive API calls
   - Wait 24 hours or contact Google Workspace admin

### Issue: Certificates have wrong data

**Cause**: Field mapping mismatch or CSV data issues

**Fix:**
1. Delete generated certificates from Drive folder
2. Fix template or CSV data
3. Re-run Autocrat
4. Upload new CSV to platform (overwrites old URLs)

### Issue: Download fails with "Service Unavailable"

**Cause**: Backend can't access Google Drive API

**Fix:**
1. Verify `GOOGLE_SERVICE_ACCOUNT_JSON` environment variable is set
2. Check service account credentials are valid
3. Contact tech team to verify backend configuration

---

## Best Practices

### 1. Test with Small Batch First
- Generate certificates for 5-10 test participants
- Verify quality, formatting, data accuracy
- Fix any issues before full batch

### 2. Use Descriptive Folder Names
- Format: `Certificates - [Event Name] - [YYYY-MM-DD]`
- Example: `Certificates - Mothers Day Run - 2024-05-12`
- Makes it easy to find certificates later

### 3. Keep Backup of Google Sheet
- File → Make a copy
- Name: `[Event Name] Certificates BACKUP - [Date]`
- Keep for audit trail and re-generation if needed

### 4. Quality Check Before Unlocking
- **Always** review 5-10 random certificates
- Check for:
  - Spelling errors
  - Data accuracy (names, dates, numbers)
  - Formatting issues
  - Image quality
- Don't unlock until verified!

### 5. Unlock in Batches (Large Events)
- For 500+ participants, unlock in batches:
  - Day 1: Unlock first 200
  - Day 2: Unlock next 200 (monitor for issues)
  - Day 3: Unlock remaining
- Allows you to catch issues early

### 6. Document Service Account Email
- Keep service account email in secure location
- Format: `[project-name]-service@[project-id].iam.gserviceaccount.com`
- You'll need it for every event

### 7. Version Your Templates
- Name templates: `Certificate Template v2 - [Event Name]`
- Keep old versions in Drive for reference
- Document changes between versions

---

## FAQ

**Q: Can I regenerate certificates after upload?**

A: Yes! Fix your template/data, re-run Autocrat, export new CSV, and upload again. New URLs will overwrite old ones.

**Q: Can participants download multiple times?**

A: Yes, unlimited downloads for external certificates. No download limits apply.

**Q: What if I need to revoke a certificate?**

A: Currently, use the Manage Certificate Access modal to see unlock status. To revoke completely:
- Method 1: Delete the file from Google Drive (user gets "not found" error)
- Method 2: Contact tech team for database update to set `external_certificate_unlocked = false`

**Q: Can I use different templates for different tiers?**

A: Not directly in one batch. Solution:
1. Filter your Google Sheet by tier
2. Generate certificates for Tier 1 with Template A
3. Generate certificates for Tier 2 with Template B
4. Upload separate CSVs sequentially

**Q: What happens if the same email appears twice?**

A: The system will process both rows. If it's the same registration, the second upload will overwrite the first certificate URL.

**Q: How long does processing take?**

A: Upload and processing is near-instant:
- 100 participants: ~5-10 seconds
- 500 participants: ~20-30 seconds
- Bottleneck is usually Autocrat generation (2-15 minutes)

**Q: Can I see who has downloaded their certificate?**

A: Not currently implemented. This is a planned feature. Users download through the backend proxy, so tracking requires additional logging.

**Q: What if a user's email changes after registration?**

A: The system matches on the email in the User table (current email). If they changed email after registration:
- Option 1: Update the CSV with their current email
- Option 2: Contact tech team to manually link certificate to registration ID

---

## Advanced: Bulk Operations

### Regenerating All Certificates

If you need to fix a major issue (wrong date, spelling error), here's how to regenerate all:

1. Fix the Google Slides template
2. **Delete** the "Merge Doc URL" column in your Google Sheet
3. Re-run Autocrat (it will regenerate all PDFs)
4. Export new CSV with fresh URLs
5. Upload to platform (overwrites all URLs)
6. Quality check again
7. Re-unlock if needed

### Generating Certificates for Specific Group

Filter your Google Sheet before running Autocrat:

1. **Data → Create a filter**
2. Filter by criteria (e.g., Tier, Status, Date)
3. Autocrat will only process visible rows
4. Clear filter when done

### Using Multiple Drive Folders

For very large events (1000+ participants), split into folders:

1. Create folders: `Certificates Batch 1`, `Certificates Batch 2`
2. Configure separate Autocrat jobs for each batch
3. Share both folders with service account
4. Upload separate CSVs to platform

---

## Support Contacts

- **Technical Issues**: support@glycogrit.com
- **Google Workspace Help**: [Autocrat Documentation](https://support.google.com)
- **Service Account Setup**: Contact dev team
- **Backend Configuration**: Check with DevOps team

---

## Appendix: Sample CSV Format

**Exported CSV (from Step 1):**
```csv
Registration ID,Registration Number,BIB Number,Email,Participant Name,Age,Gender,T-Shirt Size,Status,Total Paid,Payment Status,Registered Date,Confirmed Date
1,EVT31-ABC123,BIB001,john@example.com,John Doe,32,Male,L,PAYMENT_COMPLETED,500.00,success,2024-05-01 10:30:00,2024-05-01 10:35:00
2,EVT31-DEF456,BIB002,jane@example.com,Jane Smith,28,Female,M,PAYMENT_COMPLETED,500.00,success,2024-05-01 11:15:00,2024-05-01 11:20:00
```

**Enhanced CSV after Autocrat (for Step 7):**
```csv
Registration ID,Email,Participant Name,Merge Doc URL,Status
1,john@example.com,John Doe,https://drive.google.com/file/d/1AbC123xyz.../view,Sent
2,jane@example.com,Jane Smith,https://drive.google.com/file/d/2DeF456abc.../view,Sent
```

---

**Last Updated**: June 6, 2024
**Version**: 1.0
**Maintained By**: GlycoGrit Admin Team
