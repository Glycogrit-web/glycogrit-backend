"""
Certificate Template Processor

Handles rendering user data onto certificate templates.
"""

import io
import logging
from pathlib import Path
from typing import Any

import httpx
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


class TemplateProcessor:
    """Processes certificate templates by overlaying user data"""

    # Font file paths (relative to backend root)
    FONTS_DIR = Path(__file__).parent.parent.parent.parent / "assets" / "fonts"

    FONT_FILES = {
        "Montserrat": {
            "regular": "Montserrat-Regular.ttf",
            "bold": "Montserrat-Bold.ttf",
        },
        "Playfair Display": {
            "regular": "PlayfairDisplay-Regular.ttf",
            "bold": "PlayfairDisplay-Bold.ttf",
        },
        "Great Vibes": {
            "regular": "GreatVibes-Regular.ttf",
        }
    }

    # Minimum font scale factor (80% of original)
    MIN_FONT_SCALE = 0.80

    def __init__(self):
        """Initialize template processor"""
        self._ensure_fonts_exist()

    def _ensure_fonts_exist(self):
        """Verify font files exist, log warnings if missing"""
        if not self.FONTS_DIR.exists():
            logger.warning(f"Fonts directory not found: {self.FONTS_DIR}")
            return

        for family, variants in self.FONT_FILES.items():
            for variant, filename in variants.items():
                font_path = self.FONTS_DIR / filename
                if not font_path.exists():
                    logger.warning(f"Font file missing: {font_path}")

    async def generate_certificate(
        self,
        template_url: str,
        template_config: dict[str, Any],
        user_data: dict[str, str]
    ) -> bytes:
        """
        Generate certificate by overlaying user data on template.

        Args:
            template_url: URL to template image in R2
            template_config: Configuration from OCR with tag positions
            user_data: Dictionary mapping tags to values

        Returns:
            Certificate image as PNG bytes

        Raises:
            Exception: If generation fails
        """
        try:
            # Download template from R2
            template_img = await self._download_template(template_url)

            # Create drawing context
            draw = ImageDraw.Draw(template_img)

            # Process each detected tag
            for tag_info in template_config.get("detected_tags", []):
                tag = tag_info["tag"]

                # Get user value for this tag
                value = user_data.get(tag, "")
                if not value:
                    logger.warning(f"No value provided for tag: {tag}")
                    continue

                # Render text onto template
                self._render_text(
                    draw=draw,
                    text=value,
                    bbox=tag_info["bbox"],
                    font_size=tag_info.get("font_size", 36),
                    font_family=tag_info.get("font_family", "Montserrat"),
                    font_color=tag_info.get("font_color", "#000000"),
                    alignment=tag_info.get("alignment", "center")
                )

            # Convert to bytes
            output = io.BytesIO()
            template_img.save(output, format="PNG", optimize=True)
            output.seek(0)

            return output.read()

        except Exception as e:
            logger.error(f"Certificate generation failed: {e}")
            raise Exception(f"Failed to generate certificate: {str(e)}")

    async def _download_template(self, template_url: str) -> Image.Image:
        """
        Download template from R2.

        Args:
            template_url: URL to template

        Returns:
            PIL Image object
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(template_url)
                response.raise_for_status()

                img = Image.open(io.BytesIO(response.content))
                # Ensure RGBA for transparency support
                if img.mode != "RGBA":
                    img = img.convert("RGBA")

                return img

        except Exception as e:
            logger.error(f"Failed to download template from {template_url}: {e}")
            raise Exception(f"Failed to download template: {str(e)}")

    def _render_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        bbox: dict,
        font_size: int,
        font_family: str,
        font_color: str,
        alignment: str
    ):
        """
        Render text onto template with auto-scaling if needed.

        Args:
            draw: PIL ImageDraw object
            text: Text to render
            bbox: Bounding box dict with x, y, width, height
            font_size: Initial font size
            font_family: Font family name
            font_color: Hex color code
            alignment: Text alignment (left, center, right)
        """
        x, y, width, height = bbox['x'], bbox['y'], bbox['width'], bbox['height']

        # Load font
        font = self._load_font(font_family, font_size)

        # Check if text fits, scale down if needed
        scaled_font, final_text = self._fit_text_to_bbox(
            text=text,
            font=font,
            font_family=font_family,
            font_size=font_size,
            bbox_width=width,
            bbox_height=height
        )

        # Calculate position based on alignment
        text_bbox = draw.textbbox((0, 0), final_text, font=scaled_font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        if alignment == "center":
            text_x = x + (width - text_width) // 2
        elif alignment == "right":
            text_x = x + width - text_width
        else:  # left
            text_x = x

        # Vertically center in bbox
        text_y = y + (height - text_height) // 2

        # Draw text
        draw.text(
            (text_x, text_y),
            final_text,
            font=scaled_font,
            fill=font_color
        )

    def _fit_text_to_bbox(
        self,
        text: str,
        font: ImageFont.FreeTypeFont,
        font_family: str,
        font_size: int,
        bbox_width: int,
        bbox_height: int
    ) -> tuple[ImageFont.FreeTypeFont, str]:
        """
        Scale font down if text doesn't fit (minimum 80% of original).

        Args:
            text: Text to fit
            font: Initial font
            font_family: Font family name
            font_size: Initial font size
            bbox_width: Available width
            bbox_height: Available height

        Returns:
            Tuple of (scaled_font, text)
        """
        # Create temporary draw to measure text
        temp_img = Image.new("RGB", (1, 1))
        temp_draw = ImageDraw.Draw(temp_img)

        current_font = font
        current_size = font_size
        min_size = int(font_size * self.MIN_FONT_SCALE)

        # Try scaling down until text fits
        while current_size >= min_size:
            bbox = temp_draw.textbbox((0, 0), text, font=current_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            # Check if fits
            if text_width <= bbox_width and text_height <= bbox_height:
                return current_font, text

            # Scale down by 5%
            current_size = int(current_size * 0.95)
            if current_size < min_size:
                current_size = min_size

            current_font = self._load_font(font_family, current_size)

        # If still doesn't fit at minimum size, log warning and return
        logger.warning(
            f"Text '{text}' doesn't fit even at minimum scale. "
            f"Width: {text_width}/{bbox_width}, Height: {text_height}/{bbox_height}"
        )

        # Return with minimum font size
        return current_font, text

    def _load_font(
        self,
        font_family: str,
        font_size: int
    ) -> ImageFont.FreeTypeFont:
        """
        Load font from file system.

        Args:
            font_family: Font family name
            font_size: Font size in points

        Returns:
            PIL ImageFont object
        """
        try:
            # Get font file path
            font_info = self.FONT_FILES.get(font_family, self.FONT_FILES["Montserrat"])
            font_filename = font_info.get("regular", font_info.get("bold", "Montserrat-Regular.ttf"))
            font_path = self.FONTS_DIR / font_filename

            # Load font
            if font_path.exists():
                return ImageFont.truetype(str(font_path), font_size)
            else:
                logger.warning(f"Font not found: {font_path}. Using default.")
                # Fallback to default PIL font
                return ImageFont.load_default()

        except Exception as e:
            logger.error(f"Failed to load font {font_family}: {e}")
            return ImageFont.load_default()
