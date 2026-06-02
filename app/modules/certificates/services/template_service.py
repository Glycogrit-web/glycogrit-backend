"""
Certificate Template Service

Handles template upload, OCR processing, and configuration management.
"""

import io
import logging
import re
from datetime import datetime
from typing import Any

import cv2
import numpy as np
import pytesseract
from PIL import Image
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.modules.events.domain.event import Event
from app.modules.gallery.services.storage_service import StorageService
from app.services.base import BaseService

logger = logging.getLogger(__name__)


class TemplateService(BaseService):
    """Service for certificate template operations"""

    # Supported tags with their display names
    SUPPORTED_TAGS = {
        "{{name}}": "Participant Name",
        "{{full_name}}": "Participant Full Name",
        "{{challenge_name}}": "Challenge/Event Name",
        "{{event_name}}": "Event Name",
        "{{distance}}": "Distance Completed",
        "{{date}}": "Completion Date",
        "{{activity_name}}": "Activity Type",
        "{{sport}}": "Sport Type",
        "{{certificate_number}}": "Certificate Number",
        "{{digital_signature}}": "Digital Signature",
        "{{registration_number}}": "Registration Number",
        "{{bib_number}}": "Bib Number",
    }

    def __init__(self, db: Session):
        super().__init__(db)
        self.storage_service = StorageService()

    async def upload_and_process_template(
        self,
        event_id: int,
        file_content: bytes,
        filename: str
    ) -> dict[str, Any]:
        """
        Upload template, perform OCR, and save configuration.

        Args:
            event_id: Event ID
            file_content: Template image bytes
            filename: Original filename

        Returns:
            Dict with template_url, detected_tags, and template_config

        Raises:
            ValueError: If template invalid or OCR fails
            NotFoundException: If event not found
        """
        # Verify event exists
        event = self.db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise NotFoundException("Event", event_id)

        # Upload template to R2
        template_url = await self.storage_service.upload_certificate_template(
            file_content=file_content,
            event_id=event_id,
            filename=filename
        )

        if not template_url:
            raise ValueError("Failed to upload template to storage")

        # Perform OCR to detect tags
        logger.info(f"Starting OCR processing for template: {template_url}")
        template_config = self._perform_ocr_detection(file_content)

        if not template_config.get("detected_tags"):
            raise ValueError(
                "No certificate tags detected in template. "
                "Ensure your template contains visible tags like {{name}}, {{distance}}, etc."
            )

        # Update event with template configuration
        event.certificate_template_url = template_url
        event.certificate_template_config = template_config
        event.uses_custom_template = True
        self.db.commit()

        logger.info(
            f"✅ Template processed successfully for event {event_id}. "
            f"Detected {len(template_config['detected_tags'])} tags."
        )

        return {
            "template_url": template_url,
            "detected_tags": template_config["detected_tags"],
            "template_config": template_config
        }

    def _perform_ocr_detection(self, file_content: bytes) -> dict[str, Any]:
        """
        Perform OCR on template to detect tag positions and properties.

        Args:
            file_content: Template image bytes

        Returns:
            Configuration dict with detected tags and metadata
        """
        try:
            # Load image
            img = Image.open(io.BytesIO(file_content))
            img_width, img_height = img.size

            # Convert to numpy array for OpenCV processing
            img_array = np.array(img)

            # Run Tesseract OCR with multiple PSM modes for better tag detection
            # Note: Using original image works better than preprocessing for this certificate style
            # PSM 11 (sparse text) for sparse tags, PSM 6 (uniform block) for dense text, PSM 3 (automatic)
            detected_tags = []

            logger.info(f"🔍 Running OCR on original image with multiple PSM modes...")

            for psm_mode in [11, 6, 3]:  # Sparse text, uniform block, fully automatic
                ocr_data = pytesseract.image_to_data(
                    img_array,  # Use original image (preprocessing destroys decorative fonts)
                    output_type=pytesseract.Output.DICT,
                    config=f'--psm {psm_mode}'
                )

                # Debug: Log what OCR actually detected (keep for troubleshooting)
                detected_text = [text for text in ocr_data['text'] if text.strip()]
                logger.info(f"PSM {psm_mode}: OCR detected {len(detected_text)} text elements")
                if detected_text and len(detected_tags) < 5:  # Only log if we haven't found all tags yet
                    # Log first 30 elements to see what OCR is reading
                    sample = detected_text[:30]
                    logger.info(f"PSM {psm_mode}: Sample OCR text: {sample}")

                # Extract tags from this OCR run
                mode_tags = self._extract_tags_from_ocr(ocr_data)

                # Add new tags (avoid duplicates)
                for tag in mode_tags:
                    if tag["tag"] not in [t["tag"] for t in detected_tags]:
                        detected_tags.append(tag)

                logger.info(f"PSM {psm_mode}: Found {len(mode_tags)} tags (total unique: {len(detected_tags)})")

            # Estimate font properties for each tag
            for tag_info in detected_tags:
                tag_info.update(self._estimate_font_properties(
                    img_array,
                    tag_info["bbox"]
                ))

            # Build configuration
            config = {
                "template_dimensions": {
                    "width": img_width,
                    "height": img_height,
                    "format": img.format or "PNG"
                },
                "detected_tags": detected_tags,
                "ocr_performed_at": datetime.utcnow().isoformat(),
                "ocr_version": "pytesseract-0.3.10"
            }

            return config

        except Exception as e:
            logger.error(f"OCR detection failed: {e}")
            raise ValueError(f"OCR processing failed: {str(e)}")

    def _preprocess_for_ocr(self, img_array: np.ndarray) -> np.ndarray:
        """
        Preprocess image for better OCR accuracy.

        Enhanced preprocessing to handle:
        - Decorative/cursive fonts (like {{name}}, {{challenge_name}})
        - Low contrast text (brown on beige)
        - Various text colors and backgrounds

        Args:
            img_array: Image as numpy array

        Returns:
            Preprocessed image array
        """
        # Convert to grayscale if needed
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
        else:
            gray = img_array

        # Increase contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)
        # This helps with brown text on beige backgrounds
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # Apply adaptive thresholding for better text detection
        binary = cv2.adaptiveThreshold(
            enhanced,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            15,  # Increased block size for larger decorative fonts
            3
        )

        # Denoise
        denoised = cv2.fastNlMeansDenoising(binary, h=10)

        return denoised

    def _extract_tags_from_ocr(self, ocr_data: dict) -> list[dict]:
        """
        Extract certificate tags from OCR results.

        Args:
            ocr_data: Tesseract OCR output dictionary

        Returns:
            List of detected tag dictionaries
        """
        detected_tags = []
        tag_pattern = re.compile(r'\{\{[a-z_]+\}\}')

        # Combine words into potential tags
        n_boxes = len(ocr_data['text'])
        current_tag_parts = []
        current_bbox = None

        for i in range(n_boxes):
            text = ocr_data['text'][i].strip().lower()
            conf = int(ocr_data['conf'][i])

            # Skip low confidence or empty results
            if conf < 20 or not text:  # Lowered threshold to catch more potential tags
                # Check if we have accumulated tag parts
                if current_tag_parts:
                    self._try_form_tag(current_tag_parts, current_bbox, detected_tags)
                    current_tag_parts = []
                    current_bbox = None
                continue

            # Normalize common OCR errors for braces
            # OCR often reads { as ( or [ and } as ) or ]
            normalized_text = text
            normalized_text = normalized_text.replace('((', '{{').replace('))', '}}')
            normalized_text = normalized_text.replace('[[', '{{').replace(']]', '}}')
            normalized_text = normalized_text.replace('(', '{').replace(')', '}')
            normalized_text = normalized_text.replace('[', '{').replace(']', '}')
            normalized_text = normalized_text.replace('|', '')  # Remove pipe characters

            # Check if this could be part of a tag (including normalized braces)
            if '{{' in normalized_text or '}}' in normalized_text or (current_tag_parts and text.replace('_', '').replace('-', '').isalpha()):
                x, y, w, h = (
                    ocr_data['left'][i],
                    ocr_data['top'][i],
                    ocr_data['width'][i],
                    ocr_data['height'][i]
                )

                if not current_bbox:
                    current_bbox = {'x': x, 'y': y, 'width': w, 'height': h}
                else:
                    # Expand bbox to include this word
                    right = max(current_bbox['x'] + current_bbox['width'], x + w)
                    bottom = max(current_bbox['y'] + current_bbox['height'], y + h)
                    current_bbox['x'] = min(current_bbox['x'], x)
                    current_bbox['y'] = min(current_bbox['y'], y)
                    current_bbox['width'] = right - current_bbox['x']
                    current_bbox['height'] = bottom - current_bbox['y']

                # Store normalized text for better matching
                current_tag_parts.append(normalized_text)
            else:
                # Not a tag part, check if we have accumulated parts
                if current_tag_parts:
                    self._try_form_tag(current_tag_parts, current_bbox, detected_tags)
                    current_tag_parts = []
                    current_bbox = None

        # Check final accumulated parts
        if current_tag_parts:
            self._try_form_tag(current_tag_parts, current_bbox, detected_tags)

        return detected_tags

    def _try_form_tag(
        self,
        parts: list[str],
        bbox: dict,
        detected_tags: list[dict]
    ):
        """
        Try to form a valid tag from accumulated parts.

        Args:
            parts: List of text parts
            bbox: Bounding box dictionary
            detected_tags: List to append valid tags to
        """
        # Join parts and clean (remove spaces, pipes, and normalize braces)
        combined = ''.join(parts).replace(' ', '').replace('|', '')

        # Extract just the tag name (between braces)
        # Handle both {{ }} and normalized (( )), [[ ]]
        tag_content = combined.strip('{}').strip('()').strip('[]')

        # Try to match supported tags - prioritize longer matches first
        # This prevents "name" from matching when it's part of "activity_name"
        sorted_tags = sorted(self.SUPPORTED_TAGS.items(), key=lambda x: len(x[0]), reverse=True)

        for supported_tag, display_name in sorted_tags:
            # Remove {{ }} for comparison
            tag_name = supported_tag.strip('{}')

            # Multiple matching strategies (in order of precision):
            # 1. Exact match (highest priority)
            # 2. Exact match with underscores removed (challenge_name vs challengename)
            # 3. Fuzzy match for OCR errors
            # 4. Content starts/ends with tag_name (for partial reads)

            tag_name_no_underscore = tag_name.replace('_', '')
            content_no_underscore = tag_content.replace('_', '')

            if (tag_name == tag_content or
                tag_name_no_underscore == content_no_underscore or
                self._fuzzy_tag_match(tag_content, tag_name) or
                (len(tag_name) > 4 and (tag_content.startswith(tag_name) or tag_content.endswith(tag_name)))):
                detected_tags.append({
                    "tag": supported_tag,
                    "display_name": display_name,
                    "bbox": bbox,
                    "confidence": 0.85  # Default confidence
                })
                logger.info(f"✅ Matched tag: {supported_tag} from OCR text: {tag_content}")
                break

    def _fuzzy_tag_match(self, ocr_text: str, tag_name: str) -> bool:
        """
        Fuzzy match for common OCR errors.

        Args:
            ocr_text: OCR detected text
            tag_name: Expected tag name

        Returns:
            True if fuzzy match found
        """
        # Common OCR substitutions
        substitutions = {
            '0': 'o',
            '1': 'i',
            '5': 's',
            '8': 'b',
        }

        normalized_ocr = ocr_text.lower()
        for digit, letter in substitutions.items():
            normalized_ocr = normalized_ocr.replace(digit, letter)

        return tag_name in normalized_ocr

    def _estimate_font_properties(
        self,
        img_array: np.ndarray,
        bbox: dict
    ) -> dict[str, Any]:
        """
        Estimate font properties from bounding box region.

        Args:
            img_array: Full image array
            bbox: Tag bounding box

        Returns:
            Dict with font_size, font_color, alignment estimates
        """
        # Extract region
        x, y, w, h = bbox['x'], bbox['y'], bbox['width'], bbox['height']

        # Estimate font size from height (approximate)
        font_size = int(h * 0.75)  # Font size is typically 75% of bbox height

        # Extract dominant color in region
        region = img_array[y:y+h, x:x+w]
        if len(region.shape) == 3:
            # Convert to RGB if needed
            if region.shape[2] == 4:  # RGBA
                region = region[:, :, :3]

            # Find darkest color (likely text color)
            pixels = region.reshape(-1, region.shape[-1])
            # Filter out very light pixels (likely background)
            dark_pixels = pixels[pixels.mean(axis=1) < 200]

            if len(dark_pixels) > 0:
                avg_color = dark_pixels.mean(axis=0).astype(int)
                font_color = f"#{avg_color[0]:02x}{avg_color[1]:02x}{avg_color[2]:02x}"
            else:
                font_color = "#000000"
        else:
            # Grayscale
            font_color = "#000000"

        # Estimate alignment based on position
        # (This is a simple heuristic - center if bbox is roughly centered)
        img_center = img_array.shape[1] // 2
        bbox_center = x + w // 2

        if abs(bbox_center - img_center) < img_array.shape[1] * 0.1:
            alignment = "center"
        elif bbox_center < img_center:
            alignment = "left"
        else:
            alignment = "right"

        # Default font family (will be overridden in generation based on style)
        font_family = "Montserrat"

        return {
            "font_size": font_size,
            "font_color": font_color,
            "font_family": font_family,
            "alignment": alignment
        }
