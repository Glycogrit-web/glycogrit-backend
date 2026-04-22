"""
Cloudflare R2 Storage Service
Handles image upload, optimization, and storage to Cloudflare R2 (S3-compatible)
"""
import io
import uuid
from typing import Optional, Tuple
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from PIL import Image
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """Service for managing image storage in Cloudflare R2"""

    def __init__(self):
        """Initialize S3 client for Cloudflare R2"""
        self.s3_client = None
        self.bucket_name = settings.R2_BUCKET_NAME
        self.public_url = settings.R2_PUBLIC_URL

        # Only initialize if credentials are provided
        if settings.R2_ACCESS_KEY_ID and settings.R2_SECRET_ACCESS_KEY and settings.R2_ACCOUNT_ID:
            try:
                # Cloudflare R2 endpoint format: https://{account_id}.r2.cloudflarestorage.com
                endpoint_url = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

                self.s3_client = boto3.client(
                    's3',
                    endpoint_url=endpoint_url,
                    aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                    region_name='auto'  # R2 uses 'auto' for region
                )
                logger.info(f"✅ R2 Storage Service initialized for bucket: {self.bucket_name}")
            except Exception as e:
                logger.error(f"❌ Failed to initialize R2 client: {e}")
                self.s3_client = None
        else:
            logger.warning("⚠️  R2 credentials not configured. Image upload will not work.")

    def validate_image(self, file_content: bytes, max_size_mb: int = 5) -> Tuple[bool, Optional[str]]:
        """
        Validate image file

        Args:
            file_content: Raw file bytes
            max_size_mb: Maximum file size in MB

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file size
        max_size_bytes = max_size_mb * 1024 * 1024
        if len(file_content) > max_size_bytes:
            return False, f"File size exceeds {max_size_mb}MB limit"

        # Try to open as image
        try:
            img = Image.open(io.BytesIO(file_content))

            # Check format
            if img.format not in ['JPEG', 'PNG', 'WEBP', 'JPG']:
                return False, f"Unsupported format: {img.format}. Only JPEG, PNG, WEBP allowed"

            # Check dimensions (minimum)
            min_width, min_height = 800, 450  # Minimum 16:9 aspect ratio
            if img.width < min_width or img.height < min_height:
                return False, f"Image too small. Minimum dimensions: {min_width}x{min_height}px"

            return True, None

        except Exception as e:
            return False, f"Invalid image file: {str(e)}"

    def optimize_image(
        self,
        file_content: bytes,
        target_width: int = 1600,
        quality: int = 85
    ) -> bytes:
        """
        Optimize image by resizing and compressing

        Args:
            file_content: Original image bytes
            target_width: Target width (maintains aspect ratio)
            quality: JPEG quality (1-100)

        Returns:
            Optimized image bytes
        """
        try:
            img = Image.open(io.BytesIO(file_content))

            # Convert RGBA to RGB if needed (for JPEG)
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background

            # Resize if larger than target
            if img.width > target_width:
                aspect_ratio = img.height / img.width
                new_height = int(target_width * aspect_ratio)
                img = img.resize((target_width, new_height), Image.Resampling.LANCZOS)

            # Save optimized image
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=quality, optimize=True)
            output.seek(0)

            return output.read()

        except Exception as e:
            logger.error(f"Error optimizing image: {e}")
            # Return original if optimization fails
            return file_content

    async def upload_event_image(
        self,
        file_content: bytes,
        event_id: int,
        filename: str
    ) -> Optional[str]:
        """
        Upload event banner image to R2

        Args:
            file_content: Image file bytes
            event_id: Event ID for organizing storage
            filename: Original filename

        Returns:
            Public URL of uploaded image, or None if failed
        """
        if not self.s3_client:
            logger.error("R2 client not initialized. Cannot upload image.")
            return None

        # Validate image
        is_valid, error = self.validate_image(file_content)
        if not is_valid:
            logger.error(f"Image validation failed: {error}")
            raise ValueError(error)

        # Optimize image
        optimized_content = self.optimize_image(file_content)

        # Generate unique filename
        file_extension = filename.split('.')[-1].lower()
        if file_extension not in ['jpg', 'jpeg', 'png', 'webp']:
            file_extension = 'jpg'

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        key = f"events/{event_id}/banner_{timestamp}_{unique_id}.{file_extension}"

        try:
            # Upload to R2
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=optimized_content,
                ContentType=f'image/{file_extension}',
                CacheControl='public, max-age=31536000',  # Cache for 1 year
            )

            # Construct public URL
            if self.public_url:
                image_url = f"{self.public_url}/{key}"
            else:
                # Fallback to R2 dev URL format (you should set up custom domain)
                image_url = f"https://{self.bucket_name}.{settings.R2_ACCOUNT_ID}.r2.dev/{key}"

            logger.info(f"✅ Image uploaded successfully: {image_url}")
            return image_url

        except ClientError as e:
            logger.error(f"❌ Failed to upload to R2: {e}")
            raise Exception(f"Failed to upload image: {str(e)}")

    async def delete_event_image(self, image_url: str) -> bool:
        """
        Delete event image from R2

        Args:
            image_url: Full URL of the image

        Returns:
            True if deleted successfully
        """
        if not self.s3_client:
            logger.error("R2 client not initialized.")
            return False

        try:
            # Extract key from URL
            if self.public_url and image_url.startswith(self.public_url):
                key = image_url.replace(f"{self.public_url}/", "")
            else:
                # Try to extract from R2 dev URL
                parts = image_url.split('/')
                if 'events' in parts:
                    key = '/'.join(parts[parts.index('events'):])
                else:
                    logger.error(f"Cannot extract key from URL: {image_url}")
                    return False

            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )

            logger.info(f"✅ Image deleted successfully: {key}")
            return True

        except ClientError as e:
            logger.error(f"❌ Failed to delete from R2: {e}")
            return False


# Create singleton instance
storage_service = StorageService()
