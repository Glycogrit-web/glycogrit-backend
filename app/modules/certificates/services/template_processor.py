"""
Certificate Template Processor

Handles rendering user data onto certificate templates.
"""

import io
import logging
import re
import threading
import time
from pathlib import Path
from typing import Any

import httpx
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


class TemplateProcessor:
    """Processes certificate templates by overlaying user data"""

    # Font cache: {(font_family, font_size): ImageFont.FreeTypeFont}
    _font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}
    _font_cache_lock = threading.Lock()

    # Template image cache: {template_url: (Image.Image, timestamp)}
    _template_cache: dict[str, tuple[Image.Image, float]] = {}
    _template_cache_lock = threading.Lock()
    _template_cache_ttl = 3600  # Cache for 1 hour (3600 seconds)

    # Regex patterns for tag extraction from various delimiter formats
    REGEX_DOUBLE_CURLY = re.compile(r'\{\{([^}]+)\}\}')  # Matches {{content}}
    REGEX_SINGLE_SQUARE = re.compile(r'\[([^\]]+)\]')   # Matches [content]
    REGEX_SINGLE_PAREN = re.compile(r'\(([^)]+)\)')     # Matches (content)

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

    def _preprocess_tags(self, detected_tags: list[dict]) -> list[dict]:
        """
        Normalize OCR-detected tags for flexible matching.

        Handles various delimiter formats and normalizes tag names:
        - [{{digital signature space}}] → base_name: "digital_signature_space"
        - {{full name}} → base_name: "full_name"
        - ((NAME)) → base_name: "name"
        - {{distance}} → base_name: "distance"

        Args:
            detected_tags: List of tag dictionaries with 'tag' field from OCR

        Returns:
            Enhanced tag list with 'base_name' and 'delimiter_type' fields
        """
        preprocessed = []

        for tag_info in detected_tags:
            original_tag = tag_info["tag"]

            # Extract content from delimiters using regex patterns
            content = original_tag
            delimiter_type = "clean"

            # Try each pattern in order
            for pattern_name, pattern in [
                ("double_curly", self.REGEX_DOUBLE_CURLY),
                ("single_square", self.REGEX_SINGLE_SQUARE),
                ("single_paren", self.REGEX_SINGLE_PAREN)
            ]:
                match = pattern.search(content)
                if match:
                    content = match.group(1)
                    delimiter_type = pattern_name
                    # Continue searching in extracted content (for nested delimiters)

            # Normalize to base_name
            base_name = content.strip()
            base_name = base_name.replace(' ', '_')   # Spaces to underscores
            base_name = base_name.replace('-', '_')   # Hyphens to underscores
            base_name = base_name.lower()             # Lowercase for case-insensitive matching

            # Skip empty tags
            if not base_name:
                logger.warning(f"Skipping empty tag after normalization: '{original_tag}'")
                continue

            # Enhanced tag info with normalization
            tag_info_copy = tag_info.copy()
            tag_info_copy["base_name"] = base_name
            tag_info_copy["delimiter_type"] = delimiter_type
            tag_info_copy["original_content"] = content

            preprocessed.append(tag_info_copy)

            logger.info(
                f"🔧 Normalized tag: '{original_tag}' → base_name: '{base_name}' "
                f"(delimiter: {delimiter_type})"
            )

        return preprocessed

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

            # Preprocess tags for flexible matching
            detected_tags = self._preprocess_tags(template_config.get("detected_tags", []))

            # Normalize user_data keys to base_name format
            normalized_user_data = {}
            for key, value in user_data.items():
                # Extract base_name from user_data keys (e.g., "{{name}}" → "name")
                base_key = key.strip('{}[]() ')
                base_key = base_key.replace(' ', '_')
                base_key = base_key.replace('-', '_')
                base_key = base_key.lower()
                normalized_user_data[base_key] = value

            logger.info(f"🔍 Normalized {len(normalized_user_data)} user_data keys for matching")

            # Match tags using base_name
            matched_count = 0
            for tag_info in detected_tags:
                base_name = tag_info["base_name"]
                original_tag = tag_info["tag"]

                # Try matching with base_name
                value = normalized_user_data.get(base_name, "")

                if not value:
                    logger.warning(
                        f"⚠️  No value for tag '{original_tag}' (base_name: '{base_name}'). "
                        f"Available keys: {list(normalized_user_data.keys())}"
                    )
                    continue

                matched_count += 1
                logger.info(f"✅ Matched '{original_tag}' → '{value}' (via base_name: '{base_name}')")

                # Render text onto template
                logger.info(
                    f"🖊️  Rendering tag {matched_count}/{len(detected_tags)}: '{original_tag}' "
                    f"at position ({tag_info['bbox']['x']}, {tag_info['bbox']['y']}) "
                    f"with size {tag_info['bbox']['width']}x{tag_info['bbox']['height']}"
                )
                self._render_text(
                    draw=draw,
                    text=value,
                    bbox=tag_info["bbox"],
                    font_size=tag_info.get("font_size", 36),
                    font_family=tag_info.get("font_family", "Montserrat"),
                    font_color=tag_info.get("font_color", "#000000"),
                    alignment=tag_info.get("alignment", "center")
                )
                logger.info(f"✅ Completed rendering '{original_tag}'")

            logger.info(f"🎨 Rendered {matched_count}/{len(detected_tags)} tags onto certificate")

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
        Download and cache template image for performance.

        Templates are cached for 1 hour to avoid repeated R2 downloads.
        Cache is cleared automatically after TTL expires.

        Args:
            template_url: URL to template

        Returns:
            PIL Image object
        """
        current_time = time.time()

        # Check cache first
        with self._template_cache_lock:
            if template_url in self._template_cache:
                cached_img, cached_time = self._template_cache[template_url]

                # Check if cache is still valid
                if (current_time - cached_time) < self._template_cache_ttl:
                    logger.debug(f"✅ Using cached template: {template_url}")
                    # Return a copy to prevent mutations affecting cached version
                    return cached_img.copy()
                else:
                    # Cache expired, remove it
                    del self._template_cache[template_url]
                    logger.debug(f"🔄 Template cache expired, re-downloading: {template_url}")

        # Cache miss or expired - download template
        try:
            # Use shared HTTP client for connection pooling
            from app.modules.gallery.services.storage_service import StorageService
            client = await StorageService.get_shared_http_client()

            response = await client.get(template_url)
            response.raise_for_status()

            img = Image.open(io.BytesIO(response.content))

            # Ensure RGBA for transparency support
            if img.mode != "RGBA":
                img = img.convert("RGBA")

            # Cache the template
            with self._template_cache_lock:
                self._template_cache[template_url] = (img.copy(), current_time)
                logger.info(f"✅ Downloaded and cached template: {template_url}")

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
        logger.debug(
            f"🎨 _render_text called: text='{text}', bbox={bbox}, "
            f"font_size={font_size}, font_family='{font_family}', "
            f"alignment='{alignment}', color='{font_color}'"
        )

        x, y, width, height = bbox['x'], bbox['y'], bbox['width'], bbox['height']

        # Load font
        logger.debug(f"Loading font: {font_family} at size {font_size}")
        font = self._load_font(font_family, font_size)

        # Check if text fits, scale down if needed
        logger.debug(f"Fitting text to bbox: {width}x{height}")
        scaled_font, final_text = self._fit_text_to_bbox(
            text=text,
            font=font,
            font_family=font_family,
            font_size=font_size,
            bbox_width=width,
            bbox_height=height
        )
        logger.debug(f"Text fitted successfully")

        # Calculate position based on alignment
        text_bbox = draw.textbbox((0, 0), final_text, font=scaled_font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        logger.debug(f"Text dimensions: {text_width}x{text_height}")

        if alignment == "center":
            text_x = x + (width - text_width) // 2
        elif alignment == "right":
            text_x = x + width - text_width
        else:  # left
            text_x = x

        # Vertically center in bbox
        text_y = y + (height - text_height) // 2

        logger.debug(f"Drawing text at position ({text_x}, {text_y}) with alignment '{alignment}'")

        # Draw text
        draw.text(
            (text_x, text_y),
            final_text,
            font=scaled_font,
            fill=font_color
        )

        logger.debug(f"✅ Text '{final_text}' rendered successfully at ({text_x}, {text_y})")

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

        # Initialize text dimensions
        text_width = 0
        text_height = 0

        # Safety counter to prevent infinite loops (max 100 iterations)
        max_iterations = 100
        iteration = 0

        # Try scaling down until text fits
        while current_size >= min_size and iteration < max_iterations:
            iteration += 1
            bbox = temp_draw.textbbox((0, 0), text, font=current_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            # Check if fits
            if text_width <= bbox_width and text_height <= bbox_height:
                logger.debug(f"Text fit at size {current_size} after {iteration} iterations")
                return current_font, text

            # Scale down by 5%
            new_size = int(current_size * 0.95)
            if new_size < min_size:
                # Reached minimum size, try one final time and then exit
                current_size = min_size
                current_font = self._load_font(font_family, current_size)
                bbox = temp_draw.textbbox((0, 0), text, font=current_font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                if text_width <= bbox_width and text_height <= bbox_height:
                    return current_font, text
                break  # Exit loop after trying minimum size

            current_size = new_size
            current_font = self._load_font(font_family, current_size)

        # If still doesn't fit at minimum size, log warning and return
        logger.warning(
            f"Text '{text}' doesn't fit even at minimum scale (iterations: {iteration}). "
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
        Load font with caching for performance.

        Fonts are cached by (font_family, font_size) to avoid repeated disk I/O.
        Thread-safe with lock for concurrent access.

        Args:
            font_family: Font family name
            font_size: Font size in points

        Returns:
            PIL ImageFont object
        """
        cache_key = (font_family, font_size)

        # Check cache first (fast path, no lock needed for read)
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]

        # Cache miss - load font with lock
        with self._font_cache_lock:
            # Double-check after acquiring lock (another thread might have loaded it)
            if cache_key in self._font_cache:
                return self._font_cache[cache_key]

            # Load font from disk
            try:
                # Get font file path
                font_info = self.FONT_FILES.get(font_family, self.FONT_FILES["Montserrat"])
                font_filename = font_info.get("regular", font_info.get("bold", "Montserrat-Regular.ttf"))
                font_path = self.FONTS_DIR / font_filename

                # Load font
                if font_path.exists():
                    font = ImageFont.truetype(str(font_path), font_size)
                else:
                    logger.warning(f"Font not found: {font_path}. Using default.")
                    font = ImageFont.load_default()

                # Cache for future use
                self._font_cache[cache_key] = font
                logger.debug(f"✅ Loaded and cached font: {font_family} size {font_size}")

                return font

            except Exception as e:
                logger.error(f"Failed to load font {font_family}: {e}")
                return ImageFont.load_default()
