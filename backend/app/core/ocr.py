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

# Initialize EasyOCR reader (singleton pattern - initialized once)
_ocr_reader = None

def get_ocr_reader():
    """Get or initialize EasyOCR reader (lazy loading)."""
    global _ocr_reader
    if _ocr_reader is None:
        try:
            import easyocr
            logger.info("Initializing EasyOCR reader (CPU mode)...")
            _ocr_reader = easyocr.Reader(['en'], gpu=False)
            logger.info("EasyOCR reader initialized successfully")
        except ImportError:
            logger.warning("EasyOCR not installed - OCR for scanned images will be unavailable")
            _ocr_reader = None
    return _ocr_reader


def extract_text_with_ocr(page, page_num: int = 0) -> str:
    """
    Extract text from a PDF page using OCR (for scanned images).
    
    Args:
        page: PyMuPDF page object
        page_num: Page number for logging
    
    Returns:
        Extracted text string
    """
    try:
        reader = get_ocr_reader()
        if reader is None:
            logger.warning("OCR reader not available")
            return ""
        
        logger.info(f"Running OCR on page {page_num} (may take 30-120 seconds on CPU)...")
        
        # Convert page to image
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x resolution for better OCR
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        
        # Convert PIL Image to numpy array for EasyOCR
        img_array = np.array(img)
        
        # Run OCR
        results = reader.readtext(img_array)
        
        # Extract text from results
        ocr_text = "\n".join([text for (bbox, text, conf) in results])
        
        logger.debug(f"OCR extracted {len(ocr_text)} characters from page {page_num}")
        logger.info(f"OCR page {page_num} result: {len(ocr_text.split())} words")
        return ocr_text
    except Exception as e:
        logger.error(f"Error during OCR extraction: {str(e)}")
        return ""


def extract_text_hybrid(page, page_num: int = 0) -> Tuple[str, str]:
    """
    Smart text extraction: Use fitz first (fast), fallback to OCR for scanned images.
    
    This hybrid approach:
    1. Tries fitz for digital PDFs (instant)
    2. Falls back to OCR for scanned images (slower)
    3. Returns (text, method_used)
    
    Args:
        page: PyMuPDF page object
        page_num: Page number for logging
    
    Returns:
        Tuple of (extracted_text, extraction_method)
        Methods: "fitz", "ocr", "failed"
    """
    
    # Phase 1: Try fast text extraction (digital PDF)
    try:
        text = page.get_text().strip()
        if text and len(text.split()) > 50:  # Only accept if substantial text found
            logger.debug("Text extracted using fitz")
            return text, "fitz"
    except Exception as e:
        logger.warning(f"Fitz extraction failed: {str(e)}")
    
    # Phase 2: Fallback to OCR (scanned image or low-quality PDF)
    try:
        ocr_text = extract_text_with_ocr(page, page_num=page_num)
        if ocr_text.strip():
            logger.debug("Text extracted using OCR")
            return ocr_text, "ocr"
    except Exception as e:
        logger.error(f"OCR extraction failed: {str(e)}")
    
    # Phase 3: Failed
    logger.warning("Could not extract text from page")
    return "", "failed"
