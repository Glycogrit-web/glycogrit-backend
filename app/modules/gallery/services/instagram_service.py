import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class InstagramService:
    """
    Service for interacting with Instagram Graph API.
    Handles media container creation and publishing.
    """

    def __init__(self):
        self.access_token = settings.instagram_access_token
        self.instagram_account_id = settings.instagram_account_id
        self.base_url = "https://graph.facebook.com/v18.0"

        if not self.access_token:
            raise ValueError("Instagram access token not configured")
        if not self.instagram_account_id:
            raise ValueError("Instagram account ID not configured")

    async def create_media_container(
        self, image_data: bytes, caption: str, is_published: bool = False
    ) -> str:
        """
        Create an Instagram media container (unpublished by default).

        Args:
            image_data: Image file bytes
            caption: Caption for the post
            is_published: Whether to publish immediately (default: False for admin review)

        Returns:
            Container ID (creation_id) that can be used to publish later

        Note: For unpublished containers, admin can review in Instagram's
        Content Library and publish manually when approved.
        """
        try:
            # Step 1: Upload image to Instagram (creates container)
            url = f"{self.base_url}/{self.instagram_account_id}/media"

            # For unpublished media, we need to use a different approach
            # First, upload the image to a temporary URL or use direct upload

            async with httpx.AsyncClient(timeout=30.0) as client:
                # Create media container with image URL
                # Note: Instagram requires image to be accessible via URL
                # For direct byte upload, we need to use Facebook's Upload API first

                # Step 1: Upload image to Facebook first to get URL
                upload_url = await self._upload_image_to_facebook(image_data, client)

                if not upload_url:
                    raise Exception("Failed to upload image to Facebook")

                # Step 2: Create Instagram media container
                params = {
                    "image_url": upload_url,
                    "caption": caption,
                    "access_token": self.access_token,
                }

                # If we want it unpublished, we don't add is_published parameter
                # The container stays in draft state until manually published

                response = await client.post(url, data=params)
                response.raise_for_status()

                result = response.json()
                container_id = result.get("id")

                if not container_id:
                    raise Exception("No container ID returned from Instagram")

                logger.info(f"Created Instagram media container: {container_id}")

                # If is_published is True, publish immediately
                if is_published:
                    await self._publish_container(container_id, client)

                return container_id

        except httpx.HTTPStatusError as e:
            logger.error(f"Instagram API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Instagram API error: {e.response.text}")
        except Exception as e:
            logger.error(f"Error creating Instagram media container: {str(e)}")
            raise

    async def _upload_image_to_facebook(
        self, image_data: bytes, client: httpx.AsyncClient
    ) -> str | None:
        """
        Upload image to Facebook to get a URL that Instagram can access.
        Uses Facebook Pages Photo Upload API.

        Returns:
            URL of the uploaded image
        """
        try:
            # Get Facebook Page ID from Instagram account
            page_id = await self._get_facebook_page_id(client)

            if not page_id:
                raise Exception("Could not retrieve Facebook Page ID")

            # Upload photo to Facebook Page
            url = f"{self.base_url}/{page_id}/photos"

            files = {"source": ("image.jpg", image_data, "image/jpeg")}

            data = {
                "access_token": self.access_token,
                "published": "false",  # Don't publish to Facebook Page
            }

            response = await client.post(url, files=files, data=data)
            response.raise_for_status()

            result = response.json()
            photo_id = result.get("id")

            if not photo_id:
                raise Exception("No photo ID returned from Facebook")

            # Get the photo URL
            photo_url = await self._get_photo_url(photo_id, client)

            return photo_url

        except Exception as e:
            logger.error(f"Error uploading image to Facebook: {str(e)}")
            return None

    async def _get_facebook_page_id(self, client: httpx.AsyncClient) -> str | None:
        """Get the Facebook Page ID associated with Instagram account."""
        try:
            url = f"{self.base_url}/{self.instagram_account_id}"
            params = {"fields": "connected_facebook_page", "access_token": self.access_token}

            response = await client.get(url, params=params)
            response.raise_for_status()

            result = response.json()
            page_id = result.get("connected_facebook_page", {}).get("id")

            return page_id

        except Exception as e:
            logger.error(f"Error getting Facebook Page ID: {str(e)}")
            return None

    async def _get_photo_url(self, photo_id: str, client: httpx.AsyncClient) -> str | None:
        """Get the URL of an uploaded Facebook photo."""
        try:
            url = f"{self.base_url}/{photo_id}"
            params = {"fields": "images", "access_token": self.access_token}

            response = await client.get(url, params=params)
            response.raise_for_status()

            result = response.json()
            images = result.get("images", [])

            # Get the highest quality image URL
            if images:
                return images[0].get("source")

            return None

        except Exception as e:
            logger.error(f"Error getting photo URL: {str(e)}")
            return None

    async def _publish_container(self, container_id: str, client: httpx.AsyncClient):
        """Publish a media container to Instagram."""
        try:
            url = f"{self.base_url}/{self.instagram_account_id}/media_publish"

            params = {
                "creation_id": container_id,
                "access_token": self.access_token,
            }

            response = await client.post(url, data=params)
            response.raise_for_status()

            result = response.json()
            media_id = result.get("id")

            logger.info(f"Published Instagram media: {media_id}")

            return media_id

        except Exception as e:
            logger.error(f"Error publishing Instagram container: {str(e)}")
            raise

    async def publish_media(self, container_id: str) -> str:
        """
        Publish a previously created media container.
        Used by admin after reviewing and approving submission.

        Args:
            container_id: The container ID returned from create_media_container

        Returns:
            Published media ID
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            return await self._publish_container(container_id, client)
