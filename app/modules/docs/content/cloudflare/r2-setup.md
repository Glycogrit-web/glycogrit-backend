# Cloudflare R2 Setup Guide

## Prerequisites

- Cloudflare account (free tier available)
- Admin access to GlycoGrit backend configuration
- Credit card for Cloudflare verification (no charges for free tier)

---

## Step 1: Create Cloudflare Account

### 1.1 Sign Up
1. Go to [https://dash.cloudflare.com/sign-up](https://dash.cloudflare.com/sign-up)
2. Enter email and create password
3. Verify email address
4. Complete account setup

### 1.2 Add Payment Method (Required)
1. Go to **Billing** section
2. Add credit/debit card
3. No charges until you exceed free tier (10 GB storage)

> **📖 Note:** Credit card required for verification, but R2 has a generous free tier (10 GB storage, 1M Class A operations/month).

---

## Step 2: Enable R2 Storage

### 2.1 Navigate to R2
1. Log in to [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Click **R2** in the left sidebar
3. Click **Enable R2** (if not already enabled)
4. Accept terms of service

### 2.2 Note Your Account ID
1. In R2 dashboard, look for **Account ID** at the top
2. Copy and save this ID (format: `abc123def456...`)
3. You'll need this for backend configuration

> **✅ Tip:** Account ID is NOT sensitive, but keep access keys secure.

---

## Step 3: Create R2 Bucket

### 3.1 Create New Bucket
1. In R2 dashboard, click **Create bucket**
2. **Bucket name**: `glycogrit-proof-images` (or your preferred name)
3. **Location**: Leave as **Automatic** (Cloudflare optimizes globally)
4. Click **Create bucket**

> **📖 Note:** Bucket names must be globally unique across all Cloudflare accounts.

### 3.2 Configure Public Access
1. Open your new bucket
2. Go to **Settings** tab
3. Scroll to **Public access**
4. Click **Allow Access**
5. Copy the **Public bucket URL** (format: `https://pub-xxxxx.r2.dev`)
6. Save this URL for backend configuration

**Public URL Example**: `https://pub-a1b2c3d4e5f6.r2.dev`

> **⚠️ Warning:** Public access allows anyone to view files via direct URL. This is acceptable for proof images but consider signed URLs for sensitive content.

---

## Step 4: Create API Tokens

### 4.1 Navigate to API Tokens
1. In R2 dashboard, click **Manage R2 API Tokens**
2. Click **Create API token**

### 4.2 Configure Token Permissions
**Token Name**: `GlycoGrit Backend`

**Permissions**:
- ✅ **Object Read & Write** (for upload/delete operations)
- ✅ **Edit** access to your bucket

**TTL**: Leave blank (no expiration) or set to 1 year

**IP Address Filtering** (optional): Leave blank unless you have static backend IP

Click **Create API Token**

### 4.3 Save Credentials
A popup will show:
- **Access Key ID**: `abc123...` (like AWS access key)
- **Secret Access Key**: `xyz789...` (like AWS secret key)

> **🚫 Danger:** This is the ONLY time you'll see the Secret Access Key. Copy both values immediately!

**Save to secure location**:
```
R2_ACCESS_KEY_ID=your_access_key_id_here
R2_SECRET_ACCESS_KEY=your_secret_access_key_here
```

---

## Step 5: Configure Backend Environment

### 5.1 Add Environment Variables

Add to your backend environment (Doppler, Railway, or .env):

```bash
# R2 Account Configuration
R2_ACCOUNT_ID=your-account-id-from-step-2

# R2 API Credentials (from Step 4)
R2_ACCESS_KEY_ID=your-access-key-id
R2_SECRET_ACCESS_KEY=your-secret-access-key

# Bucket Configuration
R2_BUCKET_NAME=glycogrit-proof-images
R2_PUBLIC_URL=https://pub-xxxxx.r2.dev
```

### 5.2 Doppler Configuration
If using Doppler:
1. Open your Doppler project
2. Add each secret individually
3. Sync to your environment (dev/staging/production)

### 5.3 Railway Configuration
If using Railway:
1. Go to your service settings
2. Click **Variables** tab
3. Add each environment variable
4. Redeploy service

> **📖 Note:** Restart backend service after adding environment variables.

---

## Step 6: Install Python Dependencies

### 6.1 Add to requirements.txt
```txt
boto3==1.28.0  # AWS S3 SDK (R2 compatible)
botocore==1.31.0
```

### 6.2 Install Dependencies
```bash
pip install boto3 botocore
```

Or if using Poetry:
```bash
poetry add boto3 botocore
```

---

## Step 7: Implement R2 Service

### 7.1 Create R2 Service Class

**File**: `app/modules/activities/services/r2_service.py`

```python
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
import os
import uuid
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class R2Service:
    """Cloudflare R2 storage service for proof images"""

    def __init__(self):
        account_id = os.getenv('R2_ACCOUNT_ID')
        access_key = os.getenv('R2_ACCESS_KEY_ID')
        secret_key = os.getenv('R2_SECRET_ACCESS_KEY')

        if not all([account_id, access_key, secret_key]):
            raise ValueError("R2 credentials not configured")

        # Initialize S3-compatible client for R2
        self.client = boto3.client(
            's3',
            endpoint_url=f'https://{account_id}.r2.cloudflarestorage.com',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version='s3v4'),
            region_name='auto'  # R2 uses 'auto' for region
        )

        self.bucket_name = os.getenv('R2_BUCKET_NAME')
        self.public_url = os.getenv('R2_PUBLIC_URL')

    def upload_proof_image(
        self,
        file_content: bytes,
        user_id: int,
        event_slug: str,
        file_extension: str,
        content_type: str
    ) -> str:
        """
        Upload proof image to R2 storage

        Args:
            file_content: Image bytes
            user_id: User ID for organization
            event_slug: Event identifier
            file_extension: File extension (.jpg, .png, etc.)
            content_type: MIME type (image/jpeg, image/png, etc.)

        Returns:
            Public URL of uploaded file
        """
        try:
            # Generate unique key
            timestamp = int(datetime.now().timestamp())
            random_suffix = uuid.uuid4().hex[:8]
            key = f"proof/{user_id}/{event_slug}/{timestamp}_{random_suffix}{file_extension}"

            # Upload to R2
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_content,
                ContentType=content_type,
                ACL='public-read',  # Make publicly accessible
                Metadata={
                    'user-id': str(user_id),
                    'event-slug': event_slug,
                    'uploaded-at': datetime.now().isoformat()
                }
            )

            # Construct public URL
            file_url = f"{self.public_url}/{key}"

            logger.info(f"Uploaded proof image to R2: {key} for user {user_id}")
            return file_url

        except ClientError as e:
            logger.error(f"R2 upload failed: {e}")
            raise Exception(f"Failed to upload to R2: {str(e)}")

    def delete_proof_image(self, image_url: str):
        """
        Delete proof image from R2

        Args:
            image_url: Public URL of the image to delete
        """
        try:
            # Extract key from public URL
            key = image_url.replace(f"{self.public_url}/", "")

            # Delete from R2
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )

            logger.info(f"Deleted proof image from R2: {key}")

        except ClientError as e:
            logger.error(f"R2 delete failed: {e}")
            raise Exception(f"Failed to delete from R2: {str(e)}")

    def file_exists(self, image_url: str) -> bool:
        """Check if file exists in R2"""
        try:
            key = image_url.replace(f"{self.public_url}/", "")
            self.client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False
```

---

## Step 8: Update Upload Endpoint

### 8.1 Modify Progress API

**File**: `app/modules/activities/api/progress.py`

```python
from ..services.r2_service import R2Service

@router.post("/events/{event_slug}/upload-proof")
async def upload_proof(
    event_slug: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload proof image to R2 storage"""

    # Validate file type
    allowed_types = ['image/jpeg', 'image/png', 'image/webp']
    if file.content_type not in allowed_types:
        raise HTTPException(400, "Invalid file type")

    # Validate file size (10 MB)
    file_content = await file.read()
    if len(file_content) > 10 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 10 MB)")

    # Get file extension
    file_extension = os.path.splitext(file.filename)[1]

    # Upload to R2
    r2_service = R2Service()
    image_url = r2_service.upload_proof_image(
        file_content=file_content,
        user_id=current_user.id,
        event_slug=event_slug,
        file_extension=file_extension,
        content_type=file.content_type
    )

    # Save URL to database
    # ... (existing database logic)

    return {"proof_image_url": image_url}
```

---

## Step 9: Test R2 Integration

### 9.1 Test Upload
```bash
curl -X POST http://localhost:8000/api/v1/progress/test-event/upload-proof \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@test-image.jpg"
```

**Expected Response**:
```json
{
  "proof_image_url": "https://pub-xxxxx.r2.dev/proof/123/test-event/1683456789_a7b3c2d1.jpg"
}
```

### 9.2 Verify in R2 Dashboard
1. Go to Cloudflare R2 dashboard
2. Open your bucket
3. Navigate to `proof/` folder
4. Confirm file exists
5. Click file to view public URL

### 9.3 Test Public Access
Open the returned URL in browser - image should display.

---

## Step 10: Configure CORS (Optional)

If implementing direct frontend uploads:

### 10.1 Add CORS Policy
1. In R2 bucket settings
2. Go to **CORS policy**
3. Add configuration:

```json
[
  {
    "AllowedOrigins": [
      "https://glycogrit.com",
      "https://www.glycogrit.com"
    ],
    "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
    "AllowedHeaders": ["*"],
    "MaxAgeSeconds": 3600
  }
]
```

---

## Troubleshooting

### Error: "Access Denied"
**Solution**: Verify API token has **Object Read & Write** permissions

### Error: "Bucket not found"
**Solution**: Check `R2_BUCKET_NAME` matches exactly (case-sensitive)

### Error: "Invalid endpoint"
**Solution**: Verify `R2_ACCOUNT_ID` is correct

### Files not publicly accessible
**Solution**: Enable public access in bucket settings

---

## Security Checklist

- [ ] API credentials stored in environment variables (not code)
- [ ] Bucket has public read access enabled
- [ ] API token has minimal required permissions
- [ ] File validation implemented (type, size)
- [ ] Upload rate limiting configured
- [ ] Logging enabled for all R2 operations

---

## Next Steps

- **[Implementation Guide](./r2-implementation.md)** - Detailed code examples
- **[Migration Guide](./r2-migration.md)** - Migrate existing files to R2
- **[Troubleshooting](./r2-troubleshooting.md)** - Common issues

---

**Last Updated**: June 7, 2026
**Version**: 1.0
