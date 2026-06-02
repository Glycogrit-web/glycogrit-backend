"""
EasyOCR Wrapper Service

Provides deep learning-based OCR for certificate templates.
Designed for scene text, stylized fonts, and complex backgrounds.
"""

import logging
from typing import Any

import easyocr
import numpy as np

logger = logging.getLogger(__name__)


class EasyOCRService:
    """Wrapper for EasyOCR with caching and error handling"""

    def __init__(self):
        """Initialize EasyOCR reader (loads models on first use)"""
        self._reader = None

    @property
    def reader(self) -> easyocr.Reader:
        """Lazy-load EasyOCR reader to avoid startup overhead"""
        if self._reader is None:
            logger.info("🔍 Initializing EasyOCR reader (first-time model download)...")
            # gpu=False for Railway (CPU-only)
            # model_storage_directory caches models locally
            self._reader = easyocr.Reader(
                ['en'],
                gpu=False,
                model_storage_directory='/tmp/easyocr_models',
                download_enabled=True,
                verbose=False
            )
            logger.info("✅ EasyOCR reader initialized successfully")
        return self._reader

    def detect_text(self, img_array: np.ndarray) -> list[dict]:
        """
        Detect text in image using EasyOCR.

        Args:
            img_array: Image as numpy array (RGB format)

        Returns:
            List of detection dicts with format:
            {
                'text': 'detected text',
                'bbox': {'x': int, 'y': int, 'width': int, 'height': int},
                'confidence': float (0.0-1.0)
            }
        """
        try:
            # EasyOCR.readtext() returns: [(bbox, text, confidence), ...]
            # bbox format: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            results = self.reader.readtext(img_array, detail=1)

            detections = []
            for (bbox_points, text, conf) in results:
                # Convert EasyOCR bbox (4 corner points) to standard bbox (x, y, w, h)
                xs = [pt[0] for pt in bbox_points]
                ys = [pt[1] for pt in bbox_points]

                x = int(min(xs))
                y = int(min(ys))
                width = int(max(xs) - min(xs))
                height = int(max(ys) - min(ys))

                detections.append({
                    'text': text.strip(),
                    'bbox': {'x': x, 'y': y, 'width': width, 'height': height},
                    'confidence': float(conf)
                })

                logger.debug(
                    f"EasyOCR detected: '{text}' at ({x}, {y}) "
                    f"size ({width}x{height}) conf={conf:.2f}"
                )

            logger.info(f"✅ EasyOCR detected {len(detections)} text regions")
            return detections

        except Exception as e:
            logger.error(f"❌ EasyOCR detection failed: {e}")
            raise ValueError(f"EasyOCR failed: {str(e)}")


# Global singleton instance
_easyocr_service = None


def get_easyocr_service() -> EasyOCRService:
    """Get or create global EasyOCR service instance"""
    global _easyocr_service
    if _easyocr_service is None:
        _easyocr_service = EasyOCRService()
    return _easyocr_service
