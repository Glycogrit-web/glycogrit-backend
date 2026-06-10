"""
Cloudflare R2 Storage Service
Handles image upload, optimization, and storage to Cloudflare R2 (S3-compatible)
"""

import asyncio
import io
import logging
import os
import uuid
from datetime import datetime
from typing import Optional

import boto3
import httpx
from botocore.config import Config
from botocore.exceptions import ClientError
from PIL import Image

from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """Service for managing image storage in Cloudflare R2"""

    # Shared HTTP client for connection pooling
    _http_client: Optional[httpx.AsyncClient] = None
    _http_client_lock = asyncio.Lock()

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

                # Configure boto3 to use custom SSL settings for R2
                boto_config = Config(signature_version="s3v4", s3={"addressing_style": "path"})

                # SECURITY: SSL verification enabled
                # Only disable in development if you have certificate issues
                ssl_verify = True
                if settings.ENVIRONMENT == "development":
                    # Allow disabling SSL in development via environment variable
                    ssl_verify = os.getenv("R2_SSL_VERIFY", "true").lower() != "false"
                    if not ssl_verify:
                        logger.warning("⚠️  SSL verification DISABLED for R2 (development only)")

                self.s3_client = boto3.client(
                    "s3",
                    endpoint_url=endpoint_url,
                    aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                    region_name="auto",  # R2 uses 'auto' for region
                    config=boto_config,
                    verify=ssl_verify,
                )
                logger.info(f"✅ R2 Storage Service initialized for bucket: {self.bucket_name}")
            except Exception as e:
                logger.error(f"❌ Failed to initialize R2 client: {e}")
                self.s3_client = None
        else:
            logger.warning("⚠️  R2 credentials not configured. Image upload will not work.")

    @classmethod
    async def get_shared_http_client(cls) -> httpx.AsyncClient:
        """
        Get or create shared HTTP client for connection pooling.

        Returns:
            Shared AsyncClient instance with keepalive connections
        """
        if cls._http_client is None or cls._http_client.is_closed:
            async with cls._http_client_lock:
                # Double-check after acquiring lock
                if cls._http_client is None or cls._http_client.is_closed:
                    cls._http_client = httpx.AsyncClient(
                        timeout=30.0,
                        limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
                    )
                    logger.debug("✅ Created shared HTTP client for connection pooling")
        return cls._http_client

    def validate_image(self, file_content: bytes, max_size_mb: int = 5) -> tuple[bool, str | None]:
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
            if img.format not in ["JPEG", "PNG", "WEBP", "JPG"]:
                return False, f"Unsupported format: {img.format}. Only JPEG, PNG, WEBP allowed"

            # Check dimensions (minimum)
            min_width, min_height = 800, 450  # Minimum 16:9 aspect ratio
            if img.width < min_width or img.height < min_height:
                return False, f"Image too small. Minimum dimensions: {min_width}x{min_height}px"

            return True, None

        except Exception as e:
            return False, f"Invalid image file: {str(e)}"

    def optimize_image(
        self, file_content: bytes, target_width: int = 1600, quality: int = 85
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
            if img.mode in ("RGBA", "LA", "P"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
                img = background

            # Resize if larger than target
            if img.width > target_width:
                aspect_ratio = img.height / img.width
                new_height = int(target_width * aspect_ratio)
                img = img.resize((target_width, new_height), Image.Resampling.LANCZOS)

            # Save optimized image
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=quality, optimize=True)
            output.seek(0)

            return output.read()

        except Exception as e:
            logger.error(f"Error optimizing image: {e}")
            # Return original if optimization fails
            return file_content

    async def upload_event_image(
        self, file_content: bytes, event_id: int, filename: str
    ) -> str | None:
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
        file_extension = filename.split(".")[-1].lower()
        if file_extension not in ["jpg", "jpeg", "png", "webp"]:
            file_extension = "jpg"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        key = f"events/{event_id}/banner_{timestamp}_{unique_id}.{file_extension}"

        try:
            # Upload to R2
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=optimized_content,
                ContentType=f"image/{file_extension}",
                CacheControl="public, max-age=31536000",  # Cache for 1 year
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
                parts = image_url.split("/")
                if "events" in parts:
                    key = "/".join(parts[parts.index("events") :])
                else:
                    logger.error(f"Cannot extract key from URL: {image_url}")
                    return False

            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)

            logger.info(f"✅ Image deleted successfully: {key}")
            return True

        except ClientError as e:
            logger.error(f"❌ Failed to delete from R2: {e}")
            return False

    async def upload_proof_image(
        self, file_content: bytes, user_id: int, event_id: int, filename: str
    ) -> str | None:
        """
        Upload progress proof image to R2

        Args:
            file_content: Image file bytes
            user_id: User ID
            event_id: Event ID
            filename: Original filename

        Returns:
            Public URL of uploaded image, or None if failed
        """
        if not self.s3_client:
            logger.error("R2 client not initialized. Cannot upload image.")
            return None

        # Validate image (less strict for proof images)
        is_valid, error = self.validate_image(file_content, max_size_mb=10)
        if not is_valid:
            logger.error(f"Image validation failed: {error}")
            raise ValueError(error)

        # Optimize image (smaller size for proofs)
        optimized_content = self.optimize_image(file_content, target_width=1200, quality=80)

        # Generate unique filename
        file_extension = filename.split(".")[-1].lower()
        if file_extension not in ["jpg", "jpeg", "png", "webp"]:
            file_extension = "jpg"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        key = f"proofs/event_{event_id}/user_{user_id}_{timestamp}_{unique_id}.{file_extension}"

        try:
            # Upload to R2
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=optimized_content,
                ContentType=f"image/{file_extension}",
                CacheControl="public, max-age=31536000",  # Cache for 1 year
            )

            # Construct public URL
            if self.public_url:
                image_url = f"{self.public_url}/{key}"
            else:
                # Fallback to R2 dev URL format
                image_url = f"https://{self.bucket_name}.{settings.R2_ACCOUNT_ID}.r2.dev/{key}"

            logger.info(f"✅ Proof image uploaded successfully: {image_url}")
            return image_url

        except ClientError as e:
            logger.error(f"❌ Failed to upload proof to R2: {e}")
            raise Exception(f"Failed to upload proof image: {str(e)}")

    async def delete_proof_image(self, image_url: str) -> bool:
        """
        Delete proof image from R2

        Args:
            image_url: Full URL of the image

        Returns:
            True if deleted successfully
        """
        return await self.delete_event_image(image_url)  # Reuse the same logic

    async def upload_gallery_photo(
        self, file_content: bytes, user_id: int, filename: str
    ) -> str | None:
        """
        Upload gallery photo to R2

        Args:
            file_content: Image file bytes
            user_id: User ID
            filename: Original filename

        Returns:
            Public URL of uploaded image, or None if failed
        """
        if not self.s3_client:
            logger.error("R2 client not initialized. Cannot upload image.")
            return None

        # Validate image (8MB max for gallery photos)
        is_valid, error = self.validate_image(file_content, max_size_mb=8)
        if not is_valid:
            logger.error(f"Image validation failed: {error}")
            raise ValueError(error)

        # Optimize image
        optimized_content = self.optimize_image(file_content, target_width=1600, quality=85)

        # Generate unique filename
        file_extension = filename.split(".")[-1].lower()
        if file_extension not in ["jpg", "jpeg", "png", "webp"]:
            file_extension = "jpg"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        key = f"gallery/user_{user_id}_{timestamp}_{unique_id}.{file_extension}"

        try:
            # Upload to R2
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=optimized_content,
                ContentType=f"image/{file_extension}",
                CacheControl="public, max-age=31536000",  # Cache for 1 year
            )

            # Construct public URL
            if self.public_url:
                image_url = f"{self.public_url}/{key}"
            else:
                # Fallback to R2 dev URL format
                image_url = f"https://{self.bucket_name}.{settings.R2_ACCOUNT_ID}.r2.dev/{key}"

            logger.info(f"✅ Gallery photo uploaded successfully: {image_url}")
            return image_url

        except ClientError as e:
            logger.error(f"❌ Failed to upload gallery photo to R2: {e}")
            raise Exception(f"Failed to upload gallery photo: {str(e)}")

    def upload_file(
        self, file: io.BytesIO, key: str, content_type: str = "application/octet-stream"
    ) -> str:
        """
        Upload a generic file to R2 storage (synchronous).

        Args:
            file: File-like object (BytesIO) containing file data
            key: S3 key (path) for the file
            content_type: MIME type of the file

        Returns:
            Public URL of uploaded file

        Raises:
            Exception: If upload fails
        """
        if not self.s3_client:
            logger.error("R2 client not initialized. Cannot upload file.")
            raise Exception("R2 storage not configured")

        try:
            # Upload to R2
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file.getvalue(),
                ContentType=content_type,
                CacheControl="public, max-age=31536000",  # Cache for 1 year
            )

            # Construct public URL
            if self.public_url:
                file_url = f"{self.public_url}/{key}"
            else:
                # Fallback to R2 dev URL format
                file_url = f"https://{self.bucket_name}.{settings.R2_ACCOUNT_ID}.r2.dev/{key}"

            logger.info(f"✅ File uploaded successfully: {file_url}")
            return file_url

        except ClientError as e:
            logger.error(f"❌ Failed to upload file to R2: {e}")
            raise Exception(f"Failed to upload file: {str(e)}")


# Create singleton instance
storage_service = StorageService()
