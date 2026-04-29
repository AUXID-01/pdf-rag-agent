"""
ingestion/parser.py
Responsibility: Extract raw text and block-level structure from PDF pages using PyMuPDF.
Inputs: PDF file path (str)
Outputs: List[ParsedPage]
Dependencies: config.py, logs/schema.py
"""

import os
import fitz
from typing import List
from logs.logger import get_logger
from logs.schema import ParsedPage, ParsedDocument

log = get_logger("ingestion.parser")

def _parse_with_pymupdf(pdf_path: str) -> List[ParsedPage]:
    """Extracts text using PyMuPDF."""
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        log.error("pymupdf_open_failed", path=pdf_path, error=str(e))
        return []

    parsed_pages = []
    for i, page in enumerate(doc):
        raw_blocks = page.get_text("blocks")
        page_blocks = []
        block_texts = []
        
        for b in raw_blocks:
            x0, y0, x1, y1, text, block_no, block_type = b
            if not text.strip():
                continue
                
            page_blocks.append({
                "block_no": int(block_no),
                "text": text,
                "bbox": [x0, y0, x1, y1],
                "type": "text" if block_type == 0 else "image",
                "line_count": len(text.strip().split("\n"))
            })
            block_texts.append(text)
        
        parsed_pages.append(ParsedPage(
            page_number=i + 1,
            text="\n".join(block_texts),
            blocks=page_blocks
        ))
    doc.close()
    return parsed_pages

def _parse_with_pdfplumber(pdf_path: str) -> List[ParsedPage]:
    """Fallback 1: Extract text using pdfplumber."""
    import pdfplumber
    parsed_pages = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                parsed_pages.append(ParsedPage(
                    page_number=i + 1,
                    text=text,
                    blocks=[{"text": text}] if text else []
                ))
    except Exception as e:
        log.error("pdfplumber_failed", error=str(e))
    return parsed_pages

def _parse_with_ocr(pdf_path: str) -> List[ParsedPage]:
    """Fallback 2: Extract text using OCR (Tesseract)."""
    import pytesseract
    from pdf2image import convert_from_path
    parsed_pages = []
    try:
        images = convert_from_path(pdf_path)
        for i, image in enumerate(images):
            text = pytesseract.image_to_string(image)
            parsed_pages.append(ParsedPage(
                page_number=i + 1,
                text=text,
                blocks=[{"text": text}] if text else []
            ))
    except Exception as e:
        log.error("ocr_failed", error=str(e))
    return parsed_pages

def parse_pdf(pdf_path: str) -> ParsedDocument:
    """
    Parses a PDF file into a ParsedDocument object using a tiered fallback strategy.
    """
    if not os.path.exists(pdf_path):
        log.error("pdf_not_found", path=pdf_path)
        raise ValueError(f"PDF file not found: {pdf_path}")

    log.info("parse_start", path=pdf_path)

    # Tier 1: PyMuPDF
    result_pages = _parse_with_pymupdf(pdf_path)
    avg_chars = sum(len(p.text) for p in result_pages) / max(len(result_pages), 1)
    ocr_used = False

    # Tier 2 Fallback: pdfplumber
    if avg_chars < 150:
        log.warning("parser_fallback_pdfplumber", avg_chars=avg_chars)
        result_pages = _parse_with_pdfplumber(pdf_path)
        avg_chars = sum(len(p.text) for p in result_pages) / max(len(result_pages), 1)

    # Tier 3 Fallback: OCR
    if avg_chars < 150:
        log.warning("parser_fallback_ocr", avg_chars=avg_chars)
        result_pages = _parse_with_ocr(pdf_path)
        avg_chars = sum(len(p.text) for p in result_pages) / max(len(result_pages), 1)
        ocr_used = True

    if not result_pages:
        raise ValueError(f"Failed to extract any text from PDF: {pdf_path}")

    # PHASE 13 — OCR QUALITY CHECK
    low_quality_ocr = False
    if ocr_used and avg_chars < 100:
        log.warning("low_quality_ocr_detected", avg_chars=avg_chars)
        low_quality_ocr = True

    parsed_doc = ParsedDocument(
        source_path=pdf_path,
        filename=os.path.basename(pdf_path),
        total_pages=len(result_pages),
        pages=result_pages,
        low_quality_ocr=low_quality_ocr,
        ocr_used=ocr_used
    )

    log.info("parse_complete", total_pages=len(result_pages))
    return parsed_doc
