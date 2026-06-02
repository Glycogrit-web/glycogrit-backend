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
        "{{PARTICIPANT_NAME}}": "Participant Name",
        "{{ACTIVITY_DISTANCE}}": "Activity Distance Completed",
        "{{ACTIVITY_NAME}}": "Activity Type",
        "{{EVENT_NAME}}": "Event/Challenge Name",
        # Legacy lowercase tags for backward compatibility
        "{{name}}": "Participant Name",
        "{{full_name}}": "Participant Full Name",
        "{{distance}}": "Distance Completed",
        "{{activity_name}}": "Activity Type",
        "{{challenge_name}}": "Challenge/Event Name",
        "{{event_name}}": "Event Name",
        "{{date}}": "Completion Date",
        "{{sport}}": "Sport Type",
        "{{certificate_number}}": "Certificate Number",
        "{{digital_signature}}": "Digital Signature",
        "{{registration_number}}": "Registration Number",
        "{{bib_number}}": "Bib Number",
    }

    # Required tags that MUST be present in every certificate template
    # Uses uppercase format as primary standard
    REQUIRED_TAGS = {
        "{{PARTICIPANT_NAME}}",   # User name
        "{{ACTIVITY_DISTANCE}}",  # Activity distance selected for tier registration
        "{{ACTIVITY_NAME}}",      # Activity name selected for tier registration
        "{{EVENT_NAME}}",         # Event name in which user registered
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

        detected_tags = template_config.get("detected_tags", [])

        # Validate that tags were detected
        if not detected_tags:
            raise ValueError(
                "No certificate tags detected in template. "
                "Ensure your template contains visible tags like {{PARTICIPANT_NAME}}, {{ACTIVITY_DISTANCE}}, etc."
            )

        # Validate that all required tags are present
        is_valid, missing_tags = self._validate_required_tags(detected_tags)
        if not is_valid:
            raise ValueError(
                f"Template is missing required tags: {', '.join(missing_tags)}. "
                f"Detected tags: {[tag['tag'] for tag in detected_tags]}. "
                f"Required tags: {{{{PARTICIPANT_NAME}}}}, {{{{ACTIVITY_DISTANCE}}}}, {{{{ACTIVITY_NAME}}}}, {{{{EVENT_NAME}}}}. "
                f"Please add the missing tags to your template and try again."
            )

        logger.info(
            f"✅ Template validation successful. "
            f"Detected {len(detected_tags)} tags including all required tags."
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

    async def reprocess_existing_template(
        self,
        event_id: int,
        template_url: str
    ) -> dict[str, Any]:
        """
        Reprocess existing template by downloading from R2 and re-running OCR.

        This method allows admins to re-analyze templates after OCR improvements
        are deployed, without requiring them to re-upload the template file.

        Args:
            event_id: Event ID (for validation and logging)
            template_url: URL to existing template in R2 storage

        Returns:
            Dict with detected_tags and updated template_config

        Raises:
            ValueError: If template download or OCR fails
            NotFoundException: If event not found
        """
        # Verify event exists
        event = self.db.query(Event).filter(Event.id == event_id).first()
        if not event:
            from app.core.exceptions import NotFoundException
            raise NotFoundException("Event", event_id)

        logger.info(f"🔄 Reprocessing template from URL: {template_url}")

        try:
            # Download template from R2
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(template_url)
                response.raise_for_status()
                file_content = response.content

            logger.info(f"✅ Downloaded template ({len(file_content)} bytes) for event {event_id}")

            # Perform OCR detection (reuse existing method)
            template_config = self._perform_ocr_detection(file_content)

            detected_tags = template_config.get("detected_tags", [])

            if not detected_tags:
                raise ValueError(
                    "No certificate tags detected in template during reprocessing. "
                    "This may indicate OCR issues or template design problems."
                )

            # Validate required tags
            is_valid, missing_tags = self._validate_required_tags(detected_tags)
            if not is_valid:
                raise ValueError(
                    f"Reprocessed template is missing required tags: {', '.join(missing_tags)}. "
                    f"The template may have been modified or OCR failed to detect some tags. "
                    f"Required: {{{{PARTICIPANT_NAME}}}}, {{{{ACTIVITY_DISTANCE}}}}, {{{{ACTIVITY_NAME}}}}, {{{{EVENT_NAME}}}}"
                )

            logger.info(
                f"✅ Reprocessing complete for event {event_id}. "
                f"Detected {len(template_config['detected_tags'])} tags."
            )

            return {
                "template_url": template_url,  # Return existing URL unchanged
                "detected_tags": template_config["detected_tags"],
                "template_config": template_config
            }

        except httpx.HTTPError as e:
            logger.error(f"Failed to download template from {template_url}: {e}")
            raise ValueError(f"Failed to download template from storage: {str(e)}")
        except Exception as e:
            logger.error(f"Template reprocessing failed: {e}")
            raise ValueError(f"Template reprocessing failed: {str(e)}")

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

            # Run Tesseract OCR with multiple PSM modes
            detected_tags = []

            logger.info(f"🔍 Running Tesseract OCR with multiple PSM modes...")

            for psm_mode in [11, 6, 3]:  # Sparse text, uniform block, fully automatic
                ocr_data = pytesseract.image_to_data(
                    img_array,
                    output_type=pytesseract.Output.DICT,
                    config=f'--psm {psm_mode}'
                )

                # Extract tags from this OCR run
                mode_tags = self._extract_tags_from_ocr(ocr_data, img_width, img_height)

                # Add new tags (avoid duplicates)
                for tag in mode_tags:
                    if tag["tag"] not in [t["tag"] for t in detected_tags]:
                        detected_tags.append(tag)
                        logger.info(
                            f"🏷️  PSM {psm_mode}: Detected tag '{tag['tag']}' "
                            f"at position ({tag['bbox']['x']}, {tag['bbox']['y']})"
                        )

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

    def _validate_required_tags(self, detected_tags: list[dict]) -> tuple[bool, list[str]]:
        """
        Validate that all required tags are present in detected tags.

        Supports both uppercase ({{ACTIVITY_NAME}}) and lowercase ({{activity_name}})
        variants for backward compatibility.

        Args:
            detected_tags: List of detected tag dictionaries

        Returns:
            Tuple of (is_valid, missing_tags)
            - is_valid: True if all required tags found, False otherwise
            - missing_tags: List of missing required tag names
        """
        detected_tag_names = {tag["tag"] for tag in detected_tags}

        # Map of uppercase required tags to their lowercase equivalents
        # Note: {{name}} and {{sport}} are blacklisted to prevent false positives
        tag_variants = {
            "{{PARTICIPANT_NAME}}": ["{{full_name}}"],  # {{name}} removed - blacklisted
            "{{ACTIVITY_DISTANCE}}": ["{{distance}}"],
            "{{ACTIVITY_NAME}}": ["{{activity_name}}"],  # {{sport}} removed - blacklisted
            "{{EVENT_NAME}}": ["{{event_name}}", "{{challenge_name}}"],
        }

        missing_tags = []
        for required_tag in self.REQUIRED_TAGS:
            # Check if either uppercase or any lowercase variant is present
            variants = [required_tag] + tag_variants.get(required_tag, [])
            if not any(variant in detected_tag_names for variant in variants):
                missing_tags.append(required_tag)

        if missing_tags:
            logger.warning(
                f"⚠️  Required tags missing: {missing_tags}. "
                f"Detected: {detected_tag_names}"
            )
            return False, sorted(missing_tags)

        logger.info(f"✅ All required tags detected (including variants): {self.REQUIRED_TAGS}")
        return True, []

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

    def _extract_tags_from_ocr(self, ocr_data: dict, img_width: int, img_height: int) -> list[dict]:
        """
        Extract certificate tags from OCR results with border noise filtering.

        Uses a two-pass strategy:
          1. Box-by-box accumulation – groups adjacent OCR boxes that look like
             tag fragments and tries to form a valid tag from each group.
          2. Full-text post-processing – joins all OCR text into a single string,
             normalises brace-like characters, and scans for tag patterns using
             regex and known-tag substring matching.  This catches tags whose
             braces or underscores were so badly misread that the box-by-box pass
             missed them entirely (e.g. "[{tchallenge" + "names}]").

        Args:
            ocr_data: Tesseract OCR output dictionary
            img_width: Template image width (for border filtering)
            img_height: Template image height (for border filtering)

        Returns:
            List of detected tag dictionaries
        """
        detected_tags = []

        # Calculate border margin to filter edge noise
        # This eliminates Tesseract hallucinations from decorative borders
        # Use larger margins for top/bottom (6%) as decorative elements are more common there
        margin_x = int(img_width * 0.03)   # Keep 3% for sides
        margin_y = int(img_height * 0.06)  # Increase to 6% for top/bottom

        logger.info(
            f"🔍 OCR extraction with border filter: "
            f"margin=({margin_x}px, {margin_y}px), image=({img_width}x{img_height})"
        )

        # ------------------------------------------------------------------ #
        # Pass 1 – box-by-box accumulation                                    #
        # ------------------------------------------------------------------ #
        n_boxes = len(ocr_data['text'])
        current_tag_parts = []
        current_bbox = None

        for i in range(n_boxes):
            text = ocr_data['text'][i].strip().lower()
            conf = int(ocr_data['conf'][i])

            # 1. CONFIDENCE THRESHOLD: Raise from 20 to 40 to eliminate hallucinations
            # Tesseract often assigns low confidence (15-30) to border noise
            if conf < 40 or not text:
                # Check if we have accumulated tag parts
                if current_tag_parts:
                    self._try_form_tag(current_tag_parts, current_bbox, detected_tags)
                    current_tag_parts = []
                    current_bbox = None
                continue

            # Get bounding box coordinates
            x, y, w, h = (
                ocr_data['left'][i],
                ocr_data['top'][i],
                ocr_data['width'][i],
                ocr_data['height'][i]
            )

            # 2. BORDER MARGIN FILTER: Ignore text in outer 3% margin
            # This eliminates Tesseract hallucinations from decorative gold/blue borders
            # Example: Intersecting border strokes → phantom tags like {{sport}}
            if (x < margin_x or
                y < margin_y or
                (x + w) > (img_width - margin_x) or
                (y + h) > (img_height - margin_y)):
                logger.debug(
                    f"⛔ Ignoring border noise at ({x}, {y}): '{text}' "
                    f"(conf={conf}, outside margin)"
                )
                # Check if we have accumulated tag parts before discarding
                if current_tag_parts:
                    self._try_form_tag(current_tag_parts, current_bbox, detected_tags)
                    current_tag_parts = []
                    current_bbox = None
                continue

            # DELIMITER DETECTION: Support multiple tag delimiter formats
            # - Standard: {{tag}}, [[tag]], ((tag))
            # - Alternative: #TAG#, <TAG>, __TAG__
            has_bracket_chars = any(char in text for char in ['[', ']', '{', '}', '(', ')'])
            has_hash_delim = text.count('#') >= 2  # #TAG#
            has_angle_delim = '<' in text or '>' in text  # <TAG>
            has_underscore_delim = text.count('_') >= 2  # __TAG__

            # Normalize common OCR errors and alternative delimiters
            # Convert everything to standard {{tag}} format for consistency
            normalized_text = text

            # Standard bracket normalizations (OCR often reads { as ( or [)
            normalized_text = normalized_text.replace('((', '{{').replace('))', '}}')
            normalized_text = normalized_text.replace('[[', '{{').replace(']]', '}}')
            normalized_text = normalized_text.replace('(', '{').replace(')', '}')
            normalized_text = normalized_text.replace('[', '{').replace(']', '}')

            # Alternative delimiter normalizations (convert to {{tag}} format)
            # #TAG# → {{tag}}
            if has_hash_delim:
                normalized_text = normalized_text.replace('#', '{{', 1).replace('#', '}}', 1)

            # <TAG> → {{tag}}
            if has_angle_delim:
                normalized_text = normalized_text.replace('<', '{{').replace('>', '}}')

            # __TAG__ → {{tag}} (requires at least 2 underscores on each side)
            if has_underscore_delim and normalized_text.startswith('__') and normalized_text.endswith('__'):
                normalized_text = '{{' + normalized_text.strip('_') + '}}'

            normalized_text = normalized_text.replace('|', '')  # Remove pipe characters

            # Check if this word is part of a tag:
            # 1. Contains standard bracket characters
            # 2. Contains alternative delimiters (#, <>, __)
            # 3. Contains braces after normalization
            # 4. Is alphabetic and we're already accumulating a tag (for multi-word tags)
            #
            # NOTE: We do NOT use keyword matching as a standalone condition because it causes
            # false positives (e.g., "sport" in regular text being treated as {{sport}} tag)

            is_part_of_tag = (
                has_bracket_chars or  # Standard delimiters
                has_hash_delim or     # Alternative: #TAG#
                has_angle_delim or    # Alternative: <TAG>
                has_underscore_delim or  # Alternative: __TAG__
                '{{' in normalized_text or
                '}}' in normalized_text or
                (current_tag_parts and text.replace('_', '').replace('-', '').isalpha())
            )

            # PROXIMITY CHECK for multi-word tags:
            # If we're accumulating tag parts and this word is close, treat it as part of the tag.
            # This helps with tags like {{challenge_name}}, {{digital_signature}},
            # or nested delimiters like [{{digital signature space}}].
            if current_bbox and not is_part_of_tag:
                horizontal_distance = x - (current_bbox['x'] + current_bbox['width'])
                vertical_distance = abs(y - current_bbox['y'])

                # Check if we're in a border zone (top/bottom 10% of image)
                # Border zones are prone to decorative noise, so disable keyword matching
                in_border_zone = (y < img_height * 0.10 or
                                 y > img_height * 0.90)

                # Check if this word contains tag-related keywords (helps with multi-word tags)
                # BUT: Skip keyword matching in border zones to prevent false positives
                contains_tag_keywords = False
                if not in_border_zone:
                    contains_tag_keywords = any(
                        keyword in normalized_text
                        for keyword in ['name', 'challenge', 'distance', 'date', 'activity',
                                       'signature', 'certificate', 'registration', 'bib', 'space']
                    )

                # Accept if:
                # 1. Horizontally close (< 200px) and vertically aligned (< 35px)
                # 2. Text is alphabetic, contains brackets, underscores, or is a tag keyword
                # 3. NOT in border zone if relying only on keyword match
                if (
                    horizontal_distance < 200
                    and vertical_distance < 35
                    and (text.replace('_', '').replace('-', '').isalpha()
                         or has_bracket_chars
                         or contains_tag_keywords)
                ):
                    is_part_of_tag = True

            if is_part_of_tag:
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

        # ------------------------------------------------------------------ #
        # Pass 2 – full-text post-processing                                  #
        # ------------------------------------------------------------------ #
        # Build a single string from all OCR boxes (regardless of confidence)
        # so we can search for tag patterns that were too fragmented for Pass 1.
        all_text_parts = [t.strip() for t in ocr_data['text'] if t.strip()]
        full_text = ' '.join(all_text_parts)

        # Collect bboxes indexed by their position in the box list so we can
        # build a rough bbox for any tag we find in the full text.
        box_bboxes = []
        for i in range(n_boxes):
            if ocr_data['text'][i].strip():
                box_bboxes.append({
                    'x': ocr_data['left'][i],
                    'y': ocr_data['top'][i],
                    'width': ocr_data['width'][i],
                    'height': ocr_data['height'][i],
                })

        # Use the image centre as a fallback bbox when we cannot pinpoint the
        # exact location of a tag found only in the full-text scan.
        if box_bboxes:
            fallback_bbox = {
                'x': min(b['x'] for b in box_bboxes),
                'y': min(b['y'] for b in box_bboxes),
                'width': max(b['x'] + b['width'] for b in box_bboxes) - min(b['x'] for b in box_bboxes),
                'height': max(b['y'] + b['height'] for b in box_bboxes) - min(b['y'] for b in box_bboxes),
            }
        else:
            fallback_bbox = {'x': 0, 'y': 0, 'width': 100, 'height': 20}

        already_found = {t['tag'] for t in detected_tags}
        new_tags = self._scan_full_text_for_tags(full_text, fallback_bbox, already_found)
        detected_tags.extend(new_tags)

        return detected_tags

    def _scan_full_text_for_tags(
        self,
        full_text: str,
        fallback_bbox: dict,
        already_found: set,
    ) -> list[dict]:
        """
        Scan the full concatenated OCR text for tag patterns that the
        box-by-box pass may have missed.

        Strategy
        --------
        1. Normalise brace-like characters in the full text.
        2. Use regex to find ``{{tag_name}}`` patterns (and common OCR
           variants such as ``((…))``, ``[[…]]``).
        3. For every supported tag not yet found, check whether a
           normalised (no-underscore, no-space) version of the tag name
           appears anywhere in the normalised full text.  This catches
           cases like "[{tchallenge" + "names}]" where the braces are
           garbled but the alphabetic content is present.

        Args:
            full_text: All OCR text joined into one string.
            fallback_bbox: Bbox to assign to tags found only here.
            already_found: Set of tag strings already detected (e.g.
                ``{"{{name}}", "{{distance}}"}``).

        Returns:
            List of newly detected tag dicts (not in *already_found*).
        """
        # BLACKLIST: Reject tags that cause false positives
        BLACKLISTED_TAGS = {'{{name}}', '{{sport}}'}

        new_tags: list[dict] = []

        # --- Step 1: normalise the full text ---
        norm = full_text.lower()
        norm = norm.replace('((', '{{').replace('))', '}}')
        norm = norm.replace('[[', '{{').replace(']]', '}}')
        norm = norm.replace('(', '{').replace(')', '}')
        norm = norm.replace('[', '{').replace(']', '}')
        norm = norm.replace('|', '')

        # --- Step 2: regex scan for well-formed {{tag}} patterns ---
        brace_pattern = re.compile(r'\{\{([a-z_]{2,30})\}\}')
        for m in brace_pattern.finditer(norm):
            candidate = m.group(1)
            # Try to match against supported tags (exact + normalised)
            matched_tag = self._match_tag_name(candidate)
            if matched_tag and matched_tag not in already_found:
                # Skip blacklisted tags
                if matched_tag in BLACKLISTED_TAGS:
                    logger.debug(f"⛔ Skipping blacklisted tag in full-text scan: {matched_tag}")
                    continue

                already_found.add(matched_tag)
                new_tags.append({
                    'tag': matched_tag,
                    'display_name': self.SUPPORTED_TAGS[matched_tag],
                    'bbox': fallback_bbox,
                    'confidence': 0.80,
                })
                logger.info(
                    f"✅ Full-text regex match: {matched_tag} "
                    f"from OCR fragment: '{m.group(0)}'"
                )

        # --- Step 3: substring scan for tags whose braces were garbled ---
        # Strip ALL non-alpha characters so we get a pure letter stream, then
        # check whether each supported tag's name (also stripped) appears in it.
        # Sort longest-first so "challenge_name" is checked before "name".
        alpha_only = re.sub(r'[^a-z]', '', norm)

        sorted_tags = sorted(
            self.SUPPORTED_TAGS.items(),
            key=lambda kv: len(kv[0]),
            reverse=True,
        )

        for supported_tag, display_name in sorted_tags:
            if supported_tag in already_found:
                continue

            # Skip blacklisted tags
            if supported_tag in BLACKLISTED_TAGS:
                continue

            tag_name = supported_tag.strip('{}')
            # Strip underscores for comparison
            tag_alpha = tag_name.replace('_', '')

            if tag_alpha in alpha_only:
                # Verify the match is not a false positive caused by a shorter
                # tag name being a substring of a longer one that we already
                # matched (e.g. "name" inside "challenge_name").
                # We do this by removing all already-matched tag alphas from the
                # alpha stream before checking.
                remaining = alpha_only
                for found_tag in already_found:
                    found_alpha = found_tag.strip('{}').replace('_', '')
                    remaining = remaining.replace(found_alpha, '', 1)

                if tag_alpha not in remaining:
                    continue

                already_found.add(supported_tag)
                new_tags.append({
                    'tag': supported_tag,
                    'display_name': display_name,
                    'bbox': fallback_bbox,
                    'confidence': 0.65,
                })
                logger.info(
                    f"✅ Full-text substring match: {supported_tag} "
                    f"(alpha key '{tag_alpha}' found in OCR stream)"
                )

        return new_tags

    def _match_tag_name(self, candidate: str) -> str | None:
        """
        Try to match a raw OCR candidate string to a supported tag name.

        Attempts (in order):
          1. Exact match.
          2. Normalised match (strip underscores/spaces, lowercase).
          3. Fuzzy match (common digit-to-letter substitutions).

        Args:
            candidate: Raw tag name extracted from OCR (no braces).

        Returns:
            The matching ``{{tag}}`` key from SUPPORTED_TAGS, or ``None``.
        """
        candidate = candidate.strip().lower()

        # Pass 1 – exact
        full = '{{' + candidate + '}}'
        if full in self.SUPPORTED_TAGS:
            return full

        # Pass 2 – normalised (ignore underscores/spaces)
        cand_norm = candidate.replace('_', '').replace(' ', '')
        for tag in sorted(self.SUPPORTED_TAGS, key=len, reverse=True):
            tag_norm = tag.strip('{}').replace('_', '').replace(' ', '')
            if cand_norm == tag_norm:
                return tag

        # Pass 3 – fuzzy (digit-to-letter substitutions)
        substitutions = {'0': 'o', '1': 'i', '5': 's', '8': 'b'}
        cand_fuzzy = candidate
        for digit, letter in substitutions.items():
            cand_fuzzy = cand_fuzzy.replace(digit, letter)
        for tag in sorted(self.SUPPORTED_TAGS, key=len, reverse=True):
            tag_name = tag.strip('{}')
            if cand_fuzzy == tag_name:
                return tag

        return None

    def _try_form_tag(
        self,
        parts: list[str],
        bbox: dict,
        detected_tags: list[dict]
    ):
        """
        Try to form a valid tag from accumulated parts using priority-based matching.

        Matching is attempted in three tiers to prevent shorter tag names (e.g.
        "name") from greedily consuming OCR text that belongs to a longer tag
        (e.g. "challenge_name" or "activity_name"):

          1. Exact match   – OCR content equals the tag name exactly.
          2. Fuzzy match   – OCR content equals the tag name after normalising
                             common OCR digit-to-letter substitutions.
          3. Partial match – Substring overlap, but only when the overlap covers
                             more than 70 % of the longer string (strict guard
                             against false positives).

        Args:
            parts: List of text parts
            bbox: Bounding box dictionary
            detected_tags: List to append valid tags to
        """
        # BLACKLIST: Reject standalone tags that cause too many false positives
        # from border noise and decorative elements. Use more specific alternatives:
        # - Use {{PARTICIPANT_NAME}} or {{full_name}} instead of {{name}}
        # - Use {{ACTIVITY_NAME}} or {{activity_name}} instead of {{sport}}
        BLACKLISTED_TAGS = {'{{name}}', '{{sport}}'}

        # ULTRA-CLEAN CANONICAL NORMALIZATION:
        # Join all parts and strip out ALL formatting wrappers, spaces, and special symbols
        # to create a pure alphanumeric core string for matching
        combined = ''.join(parts)

        # Step 1: Remove all spacing and pipe characters
        combined = combined.replace(' ', '').replace('|', '').replace('\t', '')

        # Step 2: Normalize all bracket variations to standard format
        # This handles mixed delimiters like [{{name}}], ((name)), [{name}], etc.
        combined = combined.replace('[[', '{{').replace(']]', '}}')
        combined = combined.replace('((', '{{').replace('))', '}}')
        combined = combined.replace('[', '{').replace(']', '}')
        combined = combined.replace('(', '{').replace(')', '}')

        # Step 3: Extract tag name by stripping ALL possible bracket variations
        # Handle nested delimiters: [{{name}}] → {{name}} → name
        tag_content = combined
        for delimiter in ['{', '}', '[', ']', '(', ')']:
            tag_content = tag_content.strip(delimiter)

        # Step 4: Ultra-clean - remove any remaining special characters
        tag_content = tag_content.replace('|', '').replace('*', '').replace('#', '')

        if not tag_content:
            return

        # --- Pass 0: Build candidate list with leading-noise variants ---
        # When OCR badly misreads the opening braces it may produce a prefix
        # like "t" or "tc" before the actual tag name (e.g. "{{tchallenge"
        # becomes "tchallenge" after brace-stripping).  We try removing up to
        # 3 leading characters so that "tchallenge_name" → "challenge_name".
        tag_content_candidates = [tag_content]
        for n in range(1, 4):
            if len(tag_content) > n:
                tag_content_candidates.append(tag_content[n:])

        # --- Pass 1: Exact match (highest priority) ---
        # Try the raw tag_content and all leading-noise-stripped variants.
        for candidate in tag_content_candidates:
            for supported_tag in self.SUPPORTED_TAGS:
                tag_name = supported_tag.strip('{}')
                if tag_name == candidate:
                    # Skip blacklisted tags (e.g., {{name}} which causes false positives)
                    if supported_tag in BLACKLISTED_TAGS:
                        logger.debug(f"⛔ Skipping blacklisted tag: {supported_tag}")
                        return

                    detected_tags.append({
                        "tag": supported_tag,
                        "display_name": self.SUPPORTED_TAGS[supported_tag],
                        "bbox": bbox,
                        "confidence": 0.95,
                    })
                    logger.info(
                        f"✅ Exact match: {supported_tag} from OCR text: '{tag_content}'"
                    )
                    return  # Early exit – no need to check further

        # --- Pass 1.5: ULTRA-CLEAN CANONICAL NORMALIZED MATCH ---
        # Sort by length (longest first) to prevent "name" from matching when "activity_name" should match.
        # This implements the ultra-clean normalization: strip ALL non-alphanumeric characters
        # to create a pure letter/digit stream for matching.
        # Example: [{{challenge name}}] → "challengename", {{challenge_name}} → "challengename"
        sorted_tags = sorted(self.SUPPORTED_TAGS.items(), key=lambda x: len(x[0]), reverse=True)
        for candidate in tag_content_candidates:
            # Ultra-clean: strip ALL non-alphanumeric characters
            content_alphanumeric = ''.join(c for c in candidate if c.isalnum()).lower()

            for supported_tag, display_name in sorted_tags:
                tag_name = supported_tag.strip('{}')
                # Ultra-clean: strip ALL non-alphanumeric characters from supported tag too
                tag_alphanumeric = ''.join(c for c in tag_name if c.isalnum()).lower()

                if tag_alphanumeric == content_alphanumeric:
                    # Skip blacklisted tags
                    if supported_tag in BLACKLISTED_TAGS:
                        logger.debug(f"⛔ Skipping blacklisted tag: {supported_tag}")
                        return

                    detected_tags.append({
                        "tag": supported_tag,
                        "display_name": display_name,
                        "bbox": bbox,
                        "confidence": 0.90,
                    })
                    logger.info(
                        f"✅ Ultra-clean normalized match: {supported_tag} from OCR text: '{tag_content}' "
                        f"(canonical: '{content_alphanumeric}' == '{tag_alphanumeric}')"
                    )
                    return  # Early exit

        # --- Pass 2: ENHANCED FUZZY MATCH with ultra-clean normalization ---
        # Apply digit-to-letter substitutions AFTER ultra-clean normalization
        # Sorted by length to prevent greedy matching
        sorted_tags_list = sorted(self.SUPPORTED_TAGS.items(), key=lambda x: len(x[0]), reverse=True)
        for candidate in tag_content_candidates:
            # Ultra-clean the candidate first
            content_alphanumeric = ''.join(c for c in candidate if c.isalnum()).lower()

            for supported_tag, display_name in sorted_tags_list:
                tag_name = supported_tag.strip('{}')
                tag_alphanumeric = ''.join(c for c in tag_name if c.isalnum()).lower()

                if self._fuzzy_tag_match(content_alphanumeric, tag_alphanumeric):
                    # Skip blacklisted tags
                    if supported_tag in BLACKLISTED_TAGS:
                        logger.debug(f"⛔ Skipping blacklisted tag: {supported_tag}")
                        return

                    detected_tags.append({
                        "tag": supported_tag,
                        "display_name": display_name,
                        "bbox": bbox,
                        "confidence": 0.85,
                    })
                    logger.info(
                        f"✅ Enhanced fuzzy match: {supported_tag} from OCR text: '{tag_content}' "
                        f"(after substitutions: '{content_alphanumeric}')"
                    )
                    return  # Early exit

        # --- Pass 3: SORTED PARTIAL MATCH (lowest priority, strict threshold) ---
        # Sort by length (longest first) to prevent shorter patterns from overriding longer ones
        # Example: Prevents "name" from matching when "activity_name" should match
        sorted_tags_list = sorted(self.SUPPORTED_TAGS.items(), key=lambda x: len(x[0]), reverse=True)
        for candidate in tag_content_candidates:
            for supported_tag, display_name in sorted_tags_list:
                tag_name = supported_tag.strip('{}')
                if self._is_strong_partial_match(candidate, tag_name):
                    # Skip blacklisted tags
                    if supported_tag in BLACKLISTED_TAGS:
                        logger.debug(f"⛔ Skipping blacklisted tag: {supported_tag}")
                        return

                    detected_tags.append({
                        "tag": supported_tag,
                        "display_name": display_name,
                        "bbox": bbox,
                        "confidence": 0.70,
                    })
                    logger.info(
                        f"✅ Sorted partial match: {supported_tag} from OCR text: '{tag_content}'"
                    )
                    return  # Early exit

        logger.debug(f"⚠️  No tag matched OCR text: '{tag_content}' (tried all passes with ultra-clean normalization)")

    def _fuzzy_tag_match(self, ocr_text: str, tag_name: str) -> bool:
        """
        Fuzzy match for common OCR digit-to-letter substitution errors.

        After normalising the OCR text the result must be an *exact* match for
        the tag name (not merely a substring).  This prevents "name" from
        fuzzy-matching "challenge_name" or "activity_name".

        Args:
            ocr_text: OCR detected text
            tag_name: Expected tag name

        Returns:
            True if the normalised OCR text exactly equals the tag name
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

        # Require an exact match after normalisation, not a substring match
        return normalized_ocr == tag_name

    def _is_strong_partial_match(self, ocr_text: str, tag_name: str) -> bool:
        """
        Partial match guard: only accept substring overlap when it covers more
        than 70 % of the longer of the two strings.

        This prevents a short tag like "name" (4 chars) from matching OCR text
        like "challenge_name" (14 chars) because 4/14 ≈ 28 %, well below the
        threshold.  Conversely, "challeng_name" (a plausible OCR mis-read of
        "challenge_name") would score 13/14 ≈ 93 % and pass.

        Args:
            ocr_text: OCR detected text
            tag_name: Expected tag name

        Returns:
            True only when the overlap ratio exceeds 70 %
        """
        longer_len = max(len(ocr_text), len(tag_name))
        if longer_len == 0:
            return False

        # Check both directions of substring containment
        if tag_name in ocr_text:
            overlap = len(tag_name)
        elif ocr_text in tag_name:
            overlap = len(ocr_text)
        else:
            return False

        ratio = overlap / longer_len
        return ratio > 0.70

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
