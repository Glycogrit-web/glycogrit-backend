# Certificate Distribution - Quick Start Guide

> 📜 **5-Minute Guide for Admins**

## 🎯 What This System Does

Allows you to bulk-generate certificates using Google Sheets + Autocrat, upload them to the platform, and let users download them securely.

---

## ⚡ Quick Workflow

```
Export CSV → Generate Certificates → Upload CSV → Unlock → Users Download
   (2 min)      (5-10 min Google)      (1 min)      (1 min)    (Instant)
```

---

## 📝 Step-by-Step (5 Steps)

### Step 1: Export Participants (30 seconds)

1. Go to your event edit page
2. Scroll to **"Post-Event Management"**
3. Click **"📥 Export Registrations CSV"**
4. Save the file (e.g., `mothers-day-2024.csv`)

---

### Step 2: Generate Certificates (5-10 minutes)

1. Open [Google Sheets](https://sheets.google.com)
2. Create new spreadsheet
3. Import your CSV: **File → Import → Upload**
4. Install **Autocrat** add-on: **Extensions → Add-ons → Get add-ons**
5. Set up Autocrat job:
   - Template: Your certificate design in Google Slides
   - Map fields: `{{name}}` → `Participant Name`, `{{email}}` → `Email`
   - Output: PDF, save to Drive folder (set to "Anyone with link")
6. Run Autocrat
7. **Result:** New column "Merged Doc URL" appears with certificate links

> **💡 Tip:** See full Autocrat setup in [admin-certificate-distribution-handbook.md](./admin-certificate-distribution-handbook.md)

---

### Step 3: Share Drive Folder (One-time setup per event)

1. Open the Drive folder where certificates are saved
2. Click **Share**
3. Add: `glycogrit-service@your-project.iam.gserviceaccount.com` *(get from tech team)*
4. Set permission: **Viewer**
5. Click Done

---

### Step 4: Upload Back to Platform (1 minute)

1. In Google Sheets: **File → Download → CSV** (or keep as XLSX)
2. Navigate to event page as admin
3. Scroll to **"Post-Event Management"** section
4. Click **"Choose File"** under "Step 2: Upload Certificate URLs"
5. Select your CSV or XLSX file
6. Watch the upload statistics appear

**📋 Column Name Compatibility:**

The system automatically detects certificate URLs from columns named:
- "Merged Doc URL" (or variations like "Merged Doc URL - Auto Certificate")
- "Link to merged Doc" (or similar)
- "Certificate URL" (exact match)

✅ No need to rename columns - the system adapts to your Autocrat configuration!

**Success looks like:**
```
✅ Successful: 45
📊 Total Rows: 45
🔄 Overwritten: 0
```

If errors occur, expand the error section to see details.

---

### Step 5: Unlock Certificates (1 minute)

1. Click **"🔓 Manage Certificate Access"**
2. Review the list of participants
3. **Optional:** Open a few certificate links to verify quality
4. Check "Select All" or individual participants
5. Click **"Unlock Selected"**
6. Done! ✅

---

## 👤 What Users See

After unlocking:

1. User logs into platform
2. Goes to **"My Rewards"** page
3. Sees certificate card with **"Download Certificate"** button
4. Clicks button → Certificate downloads instantly

---

## ⚠️ Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| **"User not found" errors** | Email in CSV doesn't match platform. Check for typos/spaces |
| **Certificate won't download** | Not unlocked yet. Go to Step 5 |
| **"Access Denied" from Drive** | Share folder with service account (Step 3) |
| **Missing "Merged Doc URL" column** | Autocrat didn't run. Re-run Autocrat job |

---

## 🆘 Need Help?

1. **Full Guide:** [admin-certificate-distribution-handbook.md](./admin-certificate-distribution-handbook.md)
2. **Technical Issues:** Contact tech support
3. **Google Workspace Help:** [Autocrat Docs](https://autocrat.io)

---

## ✅ Checklist Before Event

One-time setup per event:

- [ ] Certificate template designed in Google Slides
- [ ] Drive folder created for certificates
- [ ] Drive folder shared with service account
- [ ] Autocrat add-on installed
- [ ] Autocrat job configured and tested with 2-3 participants

---

## 🎉 Pro Tips

1. **Test First:** Always generate 2-3 test certificates before running full batch
2. **Quality Check:** Download and review certificates before unlocking
3. **Naming Convention:** Use folder names like "Certificates - Event YYYY-MM-DD"
4. **Backup:** Keep the Google Sheet as a backup
5. **Timing:** Generate certificates 1-2 days after event when final results are confirmed

---

## 📊 Expected Timings

| Task | Time |
|------|------|
| Export CSV | 30 seconds |
| Set up Autocrat (first time) | 10 minutes |
| Set up Autocrat (subsequent) | 2 minutes |
| Generate certificates (Autocrat) | 5-10 minutes for 100 participants |
| Upload CSV | 30 seconds |
| Unlock certificates | 1 minute |
| **Total (first time)** | **~20 minutes** |
| **Total (subsequent events)** | **~10 minutes** |

---

## 🔐 Security Notes

- ✅ Certificates stored in private Google Drive folders
- ✅ Users can only download their own certificates
- ✅ Admin approval required before users can download
- ✅ All downloads are logged
- ✅ Service account has read-only access

---

**Last Updated:** 2026-06-06

**For detailed instructions, see:** [admin-certificate-distribution-handbook.md](./admin-certificate-distribution-handbook.md)
