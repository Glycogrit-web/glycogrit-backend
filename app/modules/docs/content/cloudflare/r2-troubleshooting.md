# R2 Storage Troubleshooting

## Upload Issues

### Error: "Access Denied" (403)
**Symptoms**: Upload fails with 403 Forbidden error

**Causes**:
- API token lacks write permissions
- Wrong bucket name
- Expired API token
- IP restrictions on token

**Solutions**:
1. Verify API token has **Object Read & Write** permission
2. Check `R2_BUCKET_NAME` environment variable matches exactly
3. Regenerate API token if expired
4. Remove IP restrictions or add backend IP to allowlist

**Debug**:
```python
# Test R2 connection
import boto3
client = boto3.client('s3', ...)
response = client.list_buckets()
print(response)  # Should list your buckets
```

---

### Error: "Bucket not found" (404)
**Symptoms**: `NoSuchBucket` error

**Causes**:
- Typo in bucket name
- Bucket deleted or not created
- Wrong account ID

**Solutions**:
1. Verify bucket exists in R2 dashboard
2. Check `R2_BUCKET_NAME` spelling (case-sensitive)
3. Verify `R2_ACCOUNT_ID` is correct
4. Create bucket if it doesn't exist

---

### Error: "Invalid endpoint"
**Symptoms**: Connection timeout or invalid URL error

**Causes**:
- Wrong account ID in endpoint URL
- Network connectivity issues
- Cloudflare service disruption

**Solutions**:
1. Verify endpoint format: `https://{account_id}.r2.cloudflarestorage.com`
2. Check `R2_ACCOUNT_ID` environment variable
3. Test connectivity: `curl https://{account_id}.r2.cloudflarestorage.com`
4. Check [Cloudflare Status](https://www.cloudflarestatus.com)

---

### Error: "File too large"
**Symptoms**: Upload succeeds but file corrupted or truncated

**Causes**:
- Backend memory limits
- Multipart upload needed for large files
- Network timeout

**Solutions**:
1. Implement multipart upload for files >5MB
2. Increase backend memory allocation
3. Add upload timeout configuration
4. Split large files into chunks

**Multipart Upload Example**:
```python
# For files >5MB, use multipart upload
def upload_large_file(file_content, key):
    mpu = client.create_multipart_upload(
        Bucket=bucket,
        Key=key
    )

    # Upload in 5MB chunks
    chunk_size = 5 * 1024 * 1024
    parts = []

    for i, start in enumerate(range(0, len(file_content), chunk_size)):
        chunk = file_content[start:start + chunk_size]
        part = client.upload_part(
            Bucket=bucket,
            Key=key,
            PartNumber=i + 1,
            UploadId=mpu['UploadId'],
            Body=chunk
        )
        parts.append({
            'PartNumber': i + 1,
            'ETag': part['ETag']
        })

    # Complete upload
    client.complete_multipart_upload(
        Bucket=bucket,
        Key=key,
        UploadId=mpu['UploadId'],
        MultipartUpload={'Parts': parts}
    )
```

---

## Access Issues

### Public URL returns 404
**Symptoms**: File uploaded successfully but public URL shows 404

**Causes**:
- Public access not enabled on bucket
- Wrong public URL configured
- File key mismatch

**Solutions**:
1. Enable public access in R2 bucket settings
2. Verify `R2_PUBLIC_URL` is correct (from bucket settings)
3. Check file exists: `client.head_object(Bucket=bucket, Key=key)`
4. Ensure key doesn't have leading slash

**Verify Public Access**:
1. R2 Dashboard → Your Bucket → Settings
2. Scroll to "Public access"
3. Should show "Allowed" with public URL
4. If "Blocked", click "Allow Access"

---

### CORS errors in browser
**Symptoms**: Upload works from backend but fails from frontend with CORS error

**Causes**:
- CORS policy not configured on bucket
- Wrong origin in CORS policy
- Preflight request failing

**Solutions**:
1. Configure CORS policy in R2 bucket settings
2. Add your domain to `AllowedOrigins`
3. Include required headers in `AllowedHeaders`
4. Set appropriate `MaxAgeSeconds`

**CORS Configuration**:
```json
[
  {
    "AllowedOrigins": ["https://glycogrit.com", "http://localhost:5173"],
    "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
    "AllowedHeaders": ["*"],
    "ExposeHeaders": ["ETag", "Content-Length"],
    "MaxAgeSeconds": 3600
  }
]
```

---

## Performance Issues

### Slow uploads
**Symptoms**: Uploads take longer than expected

**Causes**:
- Large file size
- Slow network connection
- Backend processing bottleneck
- No multipart upload for large files

**Solutions**:
1. Implement progress tracking for user feedback
2. Use multipart uploads for files >5MB
3. Compress images before upload (if acceptable)
4. Increase backend timeout settings

**Image Optimization**:
```python
from PIL import Image
import io

def optimize_image(file_content, max_size=(1920, 1920), quality=85):
    """Optimize image before upload"""
    img = Image.open(io.BytesIO(file_content))

    # Resize if too large
    img.thumbnail(max_size, Image.LANCZOS)

    # Convert to RGB if RGBA (for JPEG)
    if img.mode == 'RGBA':
        img = img.convert('RGB')

    # Compress
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=quality, optimize=True)
    return output.getvalue()
```

---

### High costs
**Symptoms**: R2 bill higher than expected

**Causes**:
- Excessive Class A operations (writes)
- Storage beyond free tier
- Many small files (inefficient)

**Solutions**:
1. Batch operations when possible
2. Implement caching to reduce reads
3. Clean up old/unused files
4. Monitor usage in Cloudflare dashboard

**Monitor Usage**:
```python
# List all objects and calculate total size
def get_storage_usage():
    paginator = client.get_paginator('list_objects_v2')
    total_size = 0
    file_count = 0

    for page in paginator.paginate(Bucket=bucket):
        for obj in page.get('Contents', []):
            total_size += obj['Size']
            file_count += 1

    print(f"Files: {file_count}")
    print(f"Total size: {total_size / (1024**3):.2f} GB")
```

---

## Authentication Issues

### Invalid credentials
**Symptoms**: "SignatureDoesNotMatch" or "InvalidAccessKeyId"

**Causes**:
- Wrong access key ID
- Wrong secret access key
- Extra spaces in environment variables
- Keys from wrong R2 account

**Solutions**:
1. Verify credentials in Cloudflare dashboard
2. Regenerate API token if unsure
3. Remove quotes/spaces from environment variables
4. Restart backend after updating credentials

**Test Credentials**:
```bash
# Check environment variables
echo $R2_ACCESS_KEY_ID
echo $R2_SECRET_ACCESS_KEY | wc -c  # Should be 40+ characters

# Test with boto3
python3 << EOF
import boto3, os
client = boto3.client(
    's3',
    endpoint_url=f'https://{os.getenv("R2_ACCOUNT_ID")}.r2.cloudflarestorage.com',
    aws_access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY')
)
print(client.list_buckets())
EOF
```

---

## File Management Issues

### Cannot delete file
**Symptoms**: Delete operation fails or times out

**Causes**:
- File doesn't exist
- Missing delete permissions
- File locked by another process

**Solutions**:
1. Verify file exists before deleting
2. Check API token has write permissions
3. Handle 404 errors gracefully (file already deleted)

**Safe Delete**:
```python
def safe_delete(image_url):
    try:
        key = extract_key_from_url(image_url)

        # Check if file exists
        try:
            client.head_object(Bucket=bucket, Key=key)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                logger.warning(f"File already deleted: {key}")
                return  # Already deleted, consider success

        # Delete file
        client.delete_object(Bucket=bucket, Key=key)
        logger.info(f"Deleted file: {key}")

    except Exception as e:
        logger.error(f"Delete failed: {e}")
        raise
```

---

### Files not organizing correctly
**Symptoms**: Files uploaded to wrong location or flat structure

**Causes**:
- Incorrect key generation logic
- Missing user_id or event_slug
- URL encoding issues

**Solutions**:
1. Verify key generation includes proper path structure
2. Test with sample data
3. Ensure special characters are encoded
4. Use consistent naming convention

**Proper Key Generation**:
```python
import urllib.parse
from datetime import datetime
import uuid

def generate_key(user_id, event_slug, file_extension):
    # Sanitize event slug
    safe_slug = urllib.parse.quote(event_slug, safe='')

    # Generate unique filename
    timestamp = int(datetime.now().timestamp())
    random_id = uuid.uuid4().hex[:8]

    # Construct key with clear hierarchy
    key = f"proof/{user_id}/{safe_slug}/{timestamp}_{random_id}{file_extension}"

    return key

# Example:
# proof/123/mothers-day-2024/1683456789_a7b3c2d1.jpg
```

---

## Debugging Tips

### Enable Debug Logging
```python
import logging

# Enable boto3 debug logging
logging.basicConfig(level=logging.DEBUG)
boto3.set_stream_logger('boto3.resources', logging.DEBUG)
```

### Test R2 Connection
```python
def test_r2_connection():
    """Test R2 connectivity and permissions"""
    try:
        # List buckets
        buckets = client.list_buckets()
        print("✓ Can list buckets")

        # Test bucket access
        client.head_bucket(Bucket=bucket_name)
        print("✓ Can access bucket")

        # Test write permission
        test_key = f"test/{uuid.uuid4().hex}.txt"
        client.put_object(
            Bucket=bucket_name,
            Key=test_key,
            Body=b"test"
        )
        print("✓ Can write to bucket")

        # Test read permission
        obj = client.get_object(Bucket=bucket_name, Key=test_key)
        print("✓ Can read from bucket")

        # Test delete permission
        client.delete_object(Bucket=bucket_name, Key=test_key)
        print("✓ Can delete from bucket")

        print("\n✅ All R2 tests passed!")

    except Exception as e:
        print(f"❌ R2 test failed: {e}")
```

### Monitor API Calls
```python
# Log all R2 operations
class R2ServiceWithLogging(R2Service):
    def upload_proof_image(self, *args, **kwargs):
        start = time.time()
        try:
            result = super().upload_proof_image(*args, **kwargs)
            duration = time.time() - start
            logger.info(f"R2 upload completed in {duration:.2f}s")
            return result
        except Exception as e:
            logger.error(f"R2 upload failed after {time.time() - start:.2f}s: {e}")
            raise
```

---

## Getting Help

1. **Check Cloudflare Status**: [cloudflarestatus.com](https://www.cloudflarestatus.com)
2. **Review R2 Documentation**: [Cloudflare R2 Docs](https://developers.cloudflare.com/r2/)
3. **Check Backend Logs**: Look for boto3/R2 error messages
4. **Cloudflare Community**: [community.cloudflare.com](https://community.cloudflare.com/)
5. **Contact Support**: Cloudflare dashboard → Support

---

**Last Updated**: June 7, 2026
**Version**: 1.0
