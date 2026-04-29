"""
ingestion/ocr_handler.py
Responsibility: Provide per-page OCR fallback for scanned or low-text pages using Tesseract.
Inputs: fitz.Page object
Outputs: Clean extracted text (str)
Dependencies: pytesseract, Pillow, pymupdf (fitz)
"""

import fitz
import pytesseract
import PIL.Image
import io
from logs.logger import get_logger

log = get_logger("ingestion.ocr_handler")

def extract_text_with_ocr(page: fitz.Page) -> str:
    """
    Minimal but functional OCR fallback for a single PDF page.
    Converts page to a high-DPI image and runs Tesseract OCR.
    """
    try:
        log.info("ocr_attempt_start", page_num=page.number + 1)

        # 1. Page to Image Conversion
        # Use Matrix with 2.0 scaling to get 144 DPI (approx) for better OCR accuracy.
        # Default 72 DPI is often insufficient for small text.
        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
        
        # 2. Memory Stream to PIL Image
        img_data = pix.tobytes("png")
        img = PIL.Image.open(io.BytesIO(img_data))
        
        # 3. OCR Execution
        # --psm 1: Automatic page segmentation with Orientation and Script Detection (OSD)
        # --oem 3: Default OCR engine mode
        text = pytesseract.image_to_string(img, config="--psm 1 --oem 3")
        
        # 4. Post-processing
        clean_text = text.strip()
        
        if len(clean_text) < 10:
            log.warning("ocr_result_minimal", page_num=page.number + 1, chars=len(clean_text))
        else:
            log.info("ocr_result_success", page_num=page.number + 1, chars=len(clean_text))
            
        return clean_text

    except Exception as e:
        # Graceful failure: return empty string so pipeline can continue or use previous text
        log.error("ocr_extraction_failed", page_num=page.number + 1, error=str(e))
        return ""

if __name__ == "__main__":
    # Integration Example Usage Snippet
    print("Integration Example:")
    print("from ingestion.ocr_handler import extract_text_with_ocr")
    print("if len(page_text) < 50:")
    print("    ocr_text = extract_text_with_ocr(fitz_page)")
    print("    if len(ocr_text) > len(page_text):")
    print("        page_text = ocr_text")
