"""
OCR module for extracting text from both digital and scanned PDFs.
Uses hybrid approach: fitz for digital PDFs, EasyOCR for scanned images.
"""

import fitz
from PIL import Image
import logging
from typing import Tuple
import numpy as np

# Initialize logger
logger = logging.getLogger(__name__)

_ocr_reader = None


def _is_gpu_available() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


def get_ocr_reader():
    global _ocr_reader
    if _ocr_reader is None:
        try:
            import easyocr
            gpu = _is_gpu_available()
            logger.info(f"Initializing EasyOCR reader ({'GPU' if gpu else 'CPU'} mode)...")
            _ocr_reader = easyocr.Reader(['en'], gpu=gpu)
            logger.info(f"EasyOCR reader initialized ({'GPU' if gpu else 'CPU'})")
        except ImportError:
            logger.warning("EasyOCR not installed - OCR unavailable")
            _ocr_reader = None
    return _ocr_reader


def extract_text_with_ocr(page, page_num: int = 0) -> str:
    try:
        reader = get_ocr_reader()
        if reader is None:
            return ""
        logger.info(f"Running OCR on page {page_num}...")
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        img_array = np.array(img)
        results = reader.readtext(img_array)
        ocr_text = "\n".join([text for (_, text, _) in results])
        logger.info(f"OCR page {page_num}: {len(ocr_text.split())} words")
        return ocr_text
    except Exception as e:
        logger.error(f"OCR error on page {page_num}: {str(e)}")
        return ""


def extract_text_hybrid(page, page_num: int = 0, use_ocr: bool = True) -> Tuple[str, str]:
    """
    Extract text using fitz first; fall back to OCR only when use_ocr=True and fitz yields little text.
    """
    try:
        text = page.get_text().strip()
        if text and len(text.split()) > 5:
            return text, "fitz"
    except Exception as e:
        logger.warning(f"Fitz extraction failed on page {page_num}: {str(e)}")

    if not use_ocr:
        # Return whatever fitz gave (even if sparse), no OCR fallback
        try:
            return page.get_text().strip(), "fitz"
        except Exception:
            return "", "failed"

    # OCR fallback
    try:
        ocr_text = extract_text_with_ocr(page, page_num=page_num)
        if ocr_text.strip():
            return ocr_text, "ocr"
    except Exception as e:
        logger.error(f"OCR extraction failed on page {page_num}: {str(e)}")

    logger.warning(f"Could not extract text from page {page_num}")
    return "", "failed"
