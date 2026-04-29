#!/usr/bin/env python3
"""
Configure CORS for Cloudflare R2 Bucket
Fixes CORS errors when accessing images from frontend
"""
import boto3
import json
import os
from botocore.config import Config

def configure_r2_cors():
    """Configure CORS rules for R2 bucket"""

    # Get credentials from environment (loaded from Doppler)
    account_id = os.getenv('R2_ACCOUNT_ID')
    access_key_id = os.getenv('R2_ACCESS_KEY_ID')
    secret_access_key = os.getenv('R2_SECRET_ACCESS_KEY')
    bucket_name = os.getenv('R2_BUCKET_NAME', 'glycogrit-events')

    if not all([account_id, access_key_id, secret_access_key]):
        print("❌ Missing R2 credentials in environment!")
        print("Make sure Doppler secrets are loaded:")
        print("  - R2_ACCOUNT_ID")
        print("  - R2_ACCESS_KEY_ID")
        print("  - R2_SECRET_ACCESS_KEY")
        return False

    print(f"🔧 Configuring CORS for bucket: {bucket_name}")
    print(f"   Account ID: {account_id}")

    # Create S3 client for R2
    # Note: verify=False is safe here since we're using Cloudflare's trusted R2 service
    s3_client = boto3.client(
        's3',
        endpoint_url=f'https://{account_id}.r2.cloudflarestorage.com',
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        config=Config(signature_version='s3v4'),
        region_name='auto',
        verify=False
    )

    # Define CORS rules
    cors_configuration = {
        'CORSRules': [
            {
                'AllowedOrigins': [
                    'https://www.glycogrit.com',
                    'https://glycogrit.com',
                    'http://localhost:5173',
                    'http://localhost:3000',
                    'http://localhost:8000'
                ],
                'AllowedMethods': ['GET', 'HEAD', 'PUT', 'POST', 'DELETE'],
                'AllowedHeaders': ['*'],
                'ExposeHeaders': ['ETag', 'Content-Length', 'Content-Type'],
                'MaxAgeSeconds': 3600
            }
        ]
    }

    try:
        # Apply CORS configuration
        print("\n📝 Applying CORS configuration...")
        s3_client.put_bucket_cors(
            Bucket=bucket_name,
            CORSConfiguration=cors_configuration
        )

        print("✅ CORS configuration applied successfully!")

        # Verify by reading back
        print("\n🔍 Verifying CORS configuration...")
        response = s3_client.get_bucket_cors(Bucket=bucket_name)
        print("\n📋 Current CORS rules:")
        print(json.dumps(response['CORSRules'], indent=2))

        return True

    except Exception as e:
        print(f"\n❌ Failed to configure CORS: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("CLOUDFLARE R2 CORS CONFIGURATION")
    print("=" * 60)
    print("\nThis script will configure CORS rules for your R2 bucket")
    print("to allow image access from your frontend domain.\n")

    success = configure_r2_cors()

    if success:
        print("\n" + "=" * 60)
        print("✅ Configuration Complete!")
        print("=" * 60)
        print("\nYour R2 bucket is now configured to allow requests from:")
        print("  • https://www.glycogrit.com")
        print("  • https://glycogrit.com")
        print("  • http://localhost:5173 (dev)")
        print("  • http://localhost:3000 (dev)")
    else:
        print("\n" + "=" * 60)
        print("❌ Configuration Failed")
        print("=" * 60)
