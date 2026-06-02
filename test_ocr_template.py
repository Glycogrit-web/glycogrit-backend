#!/usr/bin/env python3
"""
Test script to verify OCR tag detection on certificate template
"""

import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.modules.certificates.services.template_service import TemplateService
from unittest.mock import MagicMock

def test_template_ocr(image_path: str):
    """
    Test OCR detection on a certificate template

    Args:
        image_path: Path to certificate template image
    """
    print(f"\n{'='*80}")
    print(f"Testing OCR on: {image_path}")
    print(f"{'='*80}\n")

    # Read image file
    with open(image_path, 'rb') as f:
        file_content = f.read()

    print(f"✅ Loaded image: {len(file_content)} bytes\n")

    # Create mock database session
    mock_db = MagicMock()

    # Create template service
    service = TemplateService(mock_db)

    # Perform OCR detection
    print("🔍 Running OCR detection...\n")
    try:
        config = service._perform_ocr_detection(file_content)

        # Display results
        print(f"{'='*80}")
        print("OCR RESULTS")
        print(f"{'='*80}\n")

        print(f"Image dimensions: {config['template_dimensions']['width']}x{config['template_dimensions']['height']}")
        print(f"Format: {config['template_dimensions']['format']}")
        print(f"OCR version: {config['ocr_version']}")
        print(f"Total tags detected: {len(config['detected_tags'])}\n")

        print(f"{'='*80}")
        print("DETECTED TAGS")
        print(f"{'='*80}\n")

        for i, tag in enumerate(config['detected_tags'], 1):
            print(f"{i}. Tag: {tag['tag']}")
            print(f"   Display name: {tag['display_name']}")
            print(f"   Position: ({tag['bbox']['x']}, {tag['bbox']['y']})")
            print(f"   Size: {tag['bbox']['width']}x{tag['bbox']['height']}")
            print(f"   Font size: {tag.get('font_size', 'N/A')}")
            print(f"   Font color: {tag.get('font_color', 'N/A')}")
            print(f"   Confidence: {tag.get('confidence', 'N/A')}")
            print()

        # Check required tags
        print(f"{'='*80}")
        print("REQUIRED TAG VALIDATION")
        print(f"{'='*80}\n")

        detected_tags = config['detected_tags']
        is_valid, missing_tags = service._validate_required_tags(detected_tags)

        if is_valid:
            print("✅ SUCCESS: All required tags detected!")
            print(f"\nRequired tags found:")
            for tag in service.REQUIRED_TAGS:
                print(f"  ✓ {tag}")
        else:
            print("❌ FAILED: Missing required tags!")
            print(f"\nMissing tags:")
            for tag in missing_tags:
                print(f"  ✗ {tag}")
            print(f"\nDetected tags:")
            for tag in [t['tag'] for t in detected_tags]:
                print(f"  • {tag}")

        print(f"\n{'='*80}\n")

        return config, is_valid

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None, False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_ocr_template.py <path_to_image>")
        sys.exit(1)

    image_path = sys.argv[1]

    if not os.path.exists(image_path):
        print(f"Error: File not found: {image_path}")
        sys.exit(1)

    config, is_valid = test_template_ocr(image_path)

    # Exit with status code
    sys.exit(0 if is_valid else 1)
