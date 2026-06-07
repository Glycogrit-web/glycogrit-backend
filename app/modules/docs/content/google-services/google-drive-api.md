# Google Drive API Integration

## Overview

Google Drive API is used to securely stream certificate PDFs to users. Certificates are generated via Google Autocrat and stored in a shared Drive folder. A service account provides read-only access without exposing Drive URLs to end users.

---

## Prerequisites

- Google Cloud Console access
- Existing Google Drive folder for certificates
- Admin access to GlycoGrit backend configuration

---

## Step 1: Create Service Account

### 1.1 Navigate to Service Accounts
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Select your project (same as OAuth setup)
3. Go to **"IAM & Admin" → "Service Accounts"**
4. Click **"+ Create Service Account"**

### 1.2 Service Account Details
**Service account name**: `glycogrit-drive-reader`

**Service account ID**: `glycogrit-drive-reader@your-project.iam.gserviceaccount.com`

**Description**: `Read-only access to certificate PDFs in Google Drive`

Click **"Create and Continue"**

### 1.3 Grant Permissions
**Role**: Leave blank (no project-level permissions needed)

Click **"Continue"** → **"Done"**

---

## Step 2: Generate Service Account Key

### 2.1 Create Key
1. Click on the service account you just created
2. Go to **"Keys"** tab
3. Click **"Add Key" → "Create new key"**
4. Select **"JSON"** format
5. Click **"Create"**
6. JSON file downloads automatically

> **🚫 Danger:** This file contains sensitive credentials. Store it securely and NEVER commit to Git.

### 2.2 JSON Key Structure
```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "xxxxx",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "glycogrit-drive-reader@your-project.iam.gserviceaccount.com",
  "client_id": "123456789",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  ...
}
```

---

## Step 3: Share Drive Folder with Service Account

### 3.1 Locate Certificate Folder
1. Open Google Drive
2. Navigate to your certificate folder (e.g., "Event Certificates")
3. Right-click folder → **"Share"**

### 3.2 Add Service Account
1. Paste service account email: `glycogrit-drive-reader@your-project.iam.gserviceaccount.com`
2. Set permission: **"Viewer"** (read-only)
3. **Uncheck** "Notify people"
4. Click **"Share"**

> **✅ Tip:** Service account now has read-only access to this folder and all files within it.

---

## Step 4: Configure Backend Environment

### 4.1 Add Service Account JSON
Convert the entire JSON file to a single-line string and add to environment:

```bash
GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account","project_id":"...","private_key":"..."}'
```

> **📖 Note:** Use single quotes to wrap the JSON string. Escape any internal quotes if needed.

### 4.2 Doppler Configuration
If using Doppler:
1. Open your Doppler project
2. Add secret: `GOOGLE_SERVICE_ACCOUNT_JSON`
3. Paste entire JSON content
4. Save

---

## Architecture Flow

```
┌───────────────┐
│     Admin     │
│   (Autocrat)  │
└───────┬───────┘
        │ Generates Certificates
        ▼
┌───────────────┐
│ Google Drive  │
│   Folder      │◄──────────────┐ Share with viewer permission
└───────┬───────┘               │
        │                       │
        │ PDFs stored       ┌───┴─────────────────┐
        │                   │  Service Account    │
        ▼                   │ (Read-only access)  │
┌───────────────┐           └───────┬─────────────┘
│     CSV       │                   │
│  (URLs list)  │                   │
└───────┬───────┘                   │
        │                           │
        │ Upload                    │
        ▼                           │
┌───────────────┐                   │ Streams PDF
│   Backend     │───────────────────┘
│   (FastAPI)   │
└───────┬───────┘
        │ Secure stream
        ▼
┌───────────────┐
│     User      │
│  (Downloads)  │
└───────────────┘
```

---

## Code Implementation

### Backend Service

**File**: `app/modules/certificates/services/google_drive_service.py`

```python
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import json
import os
import io

class GoogleDriveService:
    def __init__(self):
        # Load service account credentials
        credentials_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
        credentials_dict = json.loads(credentials_json)

        self.credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )

        # Build Drive API client
        self.service = build('drive', 'v3', credentials=self.credentials)

    def get_file_content(self, file_id: str) -> bytes:
        """Stream file content from Google Drive"""
        request = self.service.files().get_media(fileId=file_id)
        file_stream = io.BytesIO()
        downloader = MediaIoBaseDownload(file_stream, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()

        return file_stream.getvalue()

    def extract_file_id_from_url(self, drive_url: str) -> str:
        """Extract file ID from Google Drive URL"""
        # Handle different URL formats
        if '/file/d/' in drive_url:
            return drive_url.split('/file/d/')[1].split('/')[0]
        elif 'id=' in drive_url:
            return drive_url.split('id=')[1].split('&')[0]
        else:
            raise ValueError("Invalid Google Drive URL format")
```

### API Endpoint

**File**: `app/modules/certificates/api/certificates.py`

```python
@router.get("/events/{event_slug}/certificate/download")
async def download_certificate(
    event_slug: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Stream certificate PDF from Google Drive"""
    # Get registration and check if certificate is unlocked
    registration = get_user_registration(db, current_user.id, event_slug)

    if not registration.external_certificate_unlocked:
        raise HTTPException(403, "Certificate is locked")

    # Extract file ID from Drive URL
    drive_service = GoogleDriveService()
    file_id = drive_service.extract_file_id_from_url(
        registration.external_certificate_url
    )

    # Stream PDF from Drive
    pdf_content = drive_service.get_file_content(file_id)

    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="certificate-{event_slug}.pdf"'
        }
    )
```

---

## Security Considerations

### ✅ Best Practices
- Service account has **read-only** access (Viewer permission)
- Users never see actual Drive URLs
- All downloads logged in backend
- File IDs validated before streaming
- PDFs streamed through backend (no direct Drive access)

### 🚫 Security Risks to Avoid
- Never grant service account write/edit permissions
- Don't expose Drive URLs to frontend
- Validate file IDs to prevent unauthorized access
- Rate limit certificate downloads if needed

---

## Troubleshooting

### Error: "File not found"
**Cause**: Service account doesn't have access to file

**Solution**:
1. Verify folder is shared with service account email
2. Check file is inside shared folder (not just linked)
3. Service account needs access to parent folder too

---

### Error: "Invalid credentials"
**Cause**: Service account JSON is incorrect or malformed

**Solution**:
1. Re-download JSON key from Google Cloud Console
2. Verify JSON is valid (use JSON validator)
3. Ensure no extra spaces or line breaks in environment variable
4. Restart backend after updating credentials

---

### Error: "Permission denied"
**Cause**: Service account lacks necessary Drive API permissions

**Solution**:
1. Enable Google Drive API in Google Cloud Console
2. Verify service account has correct scopes
3. Check folder sharing permissions (Viewer role)

---

## Testing

### Test Checklist
- [ ] Service account created
- [ ] JSON key downloaded and added to environment
- [ ] Drive folder shared with service account
- [ ] Backend can authenticate with Drive API
- [ ] Can extract file ID from Drive URL
- [ ] Can stream PDF content
- [ ] User downloads certificate successfully

---

## Next Steps

- **[Google Fit API Guide](./google-fit-api.md)** - Enable activity sync
- **[Architecture Guide](./architecture.md)** - Detailed code architecture
- **[Troubleshooting](./troubleshooting.md)** - Common issues

---

**Last Updated**: June 7, 2026
**Version**: 1.0
