# Cloudflare R2 Storage Overview

## Introduction

Cloudflare R2 is an S3-compatible object storage service used in GlycoGrit for storing user-uploaded proof images, profile pictures, and other media assets. R2 provides zero egress fees and high performance global access.

---

## Why R2 Storage?

### Benefits
- **Zero Egress Fees**: No bandwidth charges for downloads
- **S3 Compatible**: Works with existing S3 SDKs and tools
- **Global Performance**: Cloudflare's global network for fast access
- **Cost Effective**: ~$0.015/GB/month (10x cheaper than S3)
- **Automatic CDN**: Built-in caching and delivery
- **No Bandwidth Costs**: Unlimited downloads without extra charges

### Use Cases in GlycoGrit
1. **Proof Images**: Activity proof uploads from users
2. **Profile Pictures**: User avatar images (if implemented)
3. **Event Banners**: Challenge/event promotional images (if implemented)
4. **Certificate Thumbnails**: Preview images for certificates (future)

---

## Architecture Overview

```
┌─────────────┐
│    User     │
│  (Upload)   │
└──────┬──────┘
       │ Multipart Form
       │ (Image file)
       ▼
┌─────────────────┐
│    Frontend     │
│    (React)      │
└──────┬──────────┘
       │ API Call
       │ POST /api/v1/progress/{event}/upload-proof
       ▼
┌─────────────────┐
│    Backend      │
│   (FastAPI)     │
│                 │
│ 1. Validate     │
│ 2. Generate key │
│ 3. Upload to R2 │
└──────┬──────────┘
       │ S3 Compatible API
       │ boto3 client
       ▼
┌─────────────────┐
│  Cloudflare R2  │
│   (Storage)     │
│                 │
│ Bucket:         │
│ glycogrit-proof │
└──────┬──────────┘
       │
       │ Public URL
       ▼
┌─────────────────┐
│   User View     │
│ (Direct access) │
└─────────────────┘
```

---

## R2 Configuration

### Bucket Details
**Bucket Name**: `glycogrit-proof-images` (or your configured name)

**Region**: Auto (Cloudflare manages globally)

**Access**: Public read, authenticated write

**CORS**: Configured for frontend uploads (if direct upload)

---

## Environment Variables

### Required Configuration

**Backend Environment**:
```bash
# R2 Access Credentials
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY_ID=your-access-key-id
R2_SECRET_ACCESS_KEY=your-secret-access-key

# Bucket Configuration
R2_BUCKET_NAME=glycogrit-proof-images
R2_PUBLIC_URL=https://pub-xxxxx.r2.dev
```

**Where to Find**:
- `R2_ACCOUNT_ID`: Cloudflare Dashboard → R2 → Settings
- Access Keys: Cloudflare Dashboard → R2 → Manage R2 API Tokens
- Public URL: Bucket settings → Public Access

---

## Key Features

### 1. S3 Compatibility
R2 is fully compatible with S3 APIs:
- Use `boto3` library (Python)
- Use AWS SDK (Node.js)
- Standard S3 operations (PUT, GET, DELETE, LIST)

### 2. Public Access
Buckets can be configured for:
- **Public read**: Anyone can view files via public URL
- **Private**: Requires signed URLs or authentication
- **Custom domains**: Use your own domain (e.g., `media.glycogrit.com`)

### 3. Object Lifecycle
- **Automatic deletion**: Set expiry rules
- **Versioning**: Keep multiple versions of objects
- **Storage classes**: Standard (hot) only for now

---

## File Structure in R2

### Proof Images
```
glycogrit-proof-images/
├── proof/
│   ├── {user_id}/
│   │   ├── {event_id}/
│   │   │   └── {timestamp}_{random}.jpg
│   │   │   └── {timestamp}_{random}.png
```

**Example**:
```
proof/123/bicycle-day-2026/1683456789_a7b3c2d1.jpg
proof/456/mothers-day-2024/1683567890_e9f1g3h5.png
```

### Naming Convention
- **Prefix**: `proof/` for proof images
- **User ID**: For organization and access control
- **Event ID**: Event slug for easy filtering
- **Timestamp**: Unix timestamp for uniqueness
- **Random suffix**: 8-character random string to prevent collisions
- **Extension**: Original file extension (.jpg, .png, .webp)

---

## Storage Limits

### File Size Limits
- **Proof Images**: 10 MB max (enforced by backend)
- **R2 Object Limit**: 5 TB per object (far beyond our needs)

### Bucket Limits
- **Free Tier**: 10 GB storage / month
- **Paid**: $0.015 per GB/month
- **Operations**: 1M free Class A operations/month

### Current Usage (Estimate)
- Average proof image: ~2 MB
- 1000 users uploading 1 proof each: ~2 GB
- Cost: ~$0.03/month

---

## Security Model

### Access Control
- **Backend credentials**: Full read/write access
- **Public URLs**: Read-only access to uploaded files
- **Pre-signed URLs**: Time-limited access (if needed)

### File Validation
- File type: JPG, PNG, WEBP only
- File size: 10 MB maximum
- Content type verification
- Malware scanning (future enhancement)

### Best Practices
- Never expose R2 credentials to frontend
- Use backend proxy for uploads
- Validate all uploads server-side
- Implement rate limiting
- Log all upload/delete operations

---

## Performance

### Upload Speed
- Direct upload: ~5-10 seconds for 5MB file
- Cloudflare network: Global edge locations
- Automatic retries on failure

### Download Speed
- Public URL: Cached at edge
- First access: ~100-500ms
- Cached access: ~10-50ms
- No bandwidth limits

---

## Cost Breakdown

### Pricing (as of 2024)
| Operation | Price | Free Tier |
|-----------|-------|-----------|
| Storage | $0.015/GB/month | 10 GB |
| Class A Operations (write) | $4.50/million | 1M/month |
| Class B Operations (read) | $0.36/million | 10M/month |
| Egress | **$0** | Unlimited |

### Example Monthly Cost
**Scenario**: 5000 users, 2 proofs each, 2MB average
- Storage: 20 GB = $0.30
- Uploads: 10,000 writes = $0.045
- Views: 50,000 reads = $0.002
- **Total**: ~$0.35/month

**Compared to AWS S3**:
- S3 storage: $0.023/GB = $0.46
- S3 egress: $0.09/GB for 100GB = $9.00
- **S3 Total**: ~$9.46/month (27x more expensive)

---

## Integration Points

### Backend Files
- `app/modules/activities/services/r2_service.py` - R2 client wrapper
- `app/modules/activities/api/progress.py` - Upload proof endpoint
- `app/core/config.py` - R2 configuration

### Frontend Files
- `src/components/features/ProofUpload.tsx` - Upload UI
- `src/services/progress-api.ts` - API client
- `src/lib/api-client.ts` - HTTP client

---

## Common Operations

### Upload File
```python
# Backend - app/modules/activities/services/r2_service.py
import boto3
from botocore.client import Config

class R2Service:
    def __init__(self):
        self.client = boto3.client(
            's3',
            endpoint_url=f'https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com',
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            config=Config(signature_version='s3v4')
        )

    def upload_proof_image(self, file_content: bytes, key: str, content_type: str) -> str:
        """Upload proof image to R2"""
        self.client.put_object(
            Bucket=R2_BUCKET_NAME,
            Key=key,
            Body=file_content,
            ContentType=content_type,
            ACL='public-read'
        )
        return f"{R2_PUBLIC_URL}/{key}"
```

### Generate Signed URL (Private Access)
```python
def generate_signed_url(self, key: str, expires_in: int = 3600) -> str:
    """Generate time-limited access URL"""
    return self.client.generate_presigned_url(
        'get_object',
        Params={'Bucket': R2_BUCKET_NAME, 'Key': key},
        ExpiresIn=expires_in
    )
```

### Delete File
```python
def delete_proof_image(self, key: str):
    """Delete proof image from R2"""
    self.client.delete_object(
        Bucket=R2_BUCKET_NAME,
        Key=key
    )
```

---

## Monitoring

### Cloudflare Dashboard
- **Storage Usage**: Track GB used over time
- **Operations Count**: Monitor read/write operations
- **Bandwidth**: View data transfer (always $0)
- **Request Analytics**: See access patterns

### Backend Logging
- Log all uploads with user ID, event ID, file size
- Log all deletions with reason
- Track failed uploads with error details
- Monitor API latency

---

## Quick Links

- **[Setup Guide](./r2-setup.md)** - Configure R2 bucket and credentials
- **[Implementation Guide](./r2-implementation.md)** - Code implementation details
- **[Migration Guide](./r2-migration.md)** - Migrate from local storage to R2
- **[Troubleshooting](./r2-troubleshooting.md)** - Common issues and solutions

---

**Last Updated**: June 7, 2026
**Version**: 1.0
