"""
ingestion/metadata.py
Responsibility: Tag each page with high-quality, validated section titles for better retrieval/citations.
Inputs: ParsedDocument (un-enriched)
Outputs: ParsedDocument (enriched with validated section titles)
Dependencies: logs/schema.py, logs/logger.py
"""

import re
from typing import List, Optional
from logs.logger import get_logger
from logs.schema import ParsedPage, ParsedDocument

# Add this at the top of the file, after the imports
KNOWN_SECTION_PATTERNS = [
    "RBI continues with hawkish policy stance",
    "RBI continues to remain cautious on inflation",
    "RBI retains growth forecast",
    "RBI likely to undertake OMO",
    "No rate cut expected",
    "Regulation and Supervision",
    "Payment and Settlement Systems",
    "Consumer Protection",
    "Systemic Liquidity",
    "inflation forecast",
    "growth forecast",
]
log = get_logger("ingestion.metadata")

# Regex for common heading patterns (Numbered: 1.1, Section 2, etc.)
RE_SECTION_NUM = re.compile(r"^(Section|Chapter|Appendix|Part)?\s*\d+(\.\d+)*", re.IGNORECASE)

def is_valid_section_title(text: str) -> bool:
    """
    Validates if a text candidate is a high-quality section title.
    Enforces constraints on length, word count, and formatting.
    """
    if not text or not text.strip():
        return False
    
    val = text.strip()
    words = val.split()
    
    # 1. Basic length and word count constraints (Requirement 3 & 4)
    if len(val) > 80:
        return False
    if len(words) > 12 or len(words) < 1:
        return False
        
    # 2. Punctuation checks
    if val.endswith(","):
        return False
    if ";" in val:
        return False
        
    # Excess periods check (avoid paragraph fragments)
    period_count = val.count(".")
    if period_count > 1:
        # Allow if it looks like a numbered section (e.g., 1.2.3)
        if not RE_SECTION_NUM.match(val):
            return False
            
    # 3. Sentence / Formatting heuristics
    # Reject if it contains more than one sentence (multiple ending punctuations)
    if period_count > 0 and not val.endswith(".") and not RE_SECTION_NUM.match(val):
        # A period in the middle of a non-numbered title usually indicates multiple sentences
        return False
    
    # Reject if it starts with lowercase (likely paragraph continuation)
    if val[0].islower():
        return False
        
    # Reject "mostly lowercase running prose" (Requirement 4)
    if len(words) > 4:
        alpha_chars = [c for c in val if c.isalpha()]
        if alpha_chars:
            lower_ratio = sum(1 for c in alpha_chars if c.islower()) / len(alpha_chars)
            # Headings usually have many capitalized words. Prose has ~90% lowercase.
            if lower_ratio > 0.85:
                return False

    return True

def detect_section(page: ParsedPage, prev_section: str = "General") -> str:
    """
    Detects the likely section title for a given page using heuristics.
    Priority order:
      1. Known section pattern match (fast, exact for this PDF type)
      2. Structural patterns (numbered, ALL CAPS, Title Case)
      3. First bold-like line heuristic (short, starts uppercase)
      4. Fallback to previous section
    """
    lines = [line.strip() for line in page.text.split("\n") if line.strip()]
    if not lines:
        return prev_section

    # PRIORITY 1 — Known section pattern match
    # Scan every line for a known heading substring (case-insensitive)
    for line in lines:
        for pattern in KNOWN_SECTION_PATTERNS:
            if pattern.lower() in line.lower():
                # Truncate to 80 chars max for clean citation display
                clean = line.strip()[:80].rstrip(";:,")
                log.info("section_known_pattern_match",
                         page_number=page.page_number,
                         section=clean)
                return clean

    # PRIORITY 2 — Structural patterns (numbered, ALL CAPS, Title Case)
    candidates = []
    for line in lines:
        # Skip lines that are clearly dates or page numbers
        if re.match(r"^\d{1,2}\s+\w+\s+\d{4}$", line):   # e.g. "06 October 2023"
            continue
        if re.match(r"^\d+$", line):                        # standalone page number
            continue

        is_match = False
        if RE_SECTION_NUM.match(line) and len(line) <= 80:
            is_match = True
        elif 4 <= len(line) <= 80 and line.isupper() and len(line.split()) >= 2:
            is_match = True
        elif 4 <= len(line) <= 80 and line.istitle() and not line.endswith((".", ",")):
            is_match = True

        if is_match:
            candidates.append(line)

    valid_candidates = [c for c in candidates if is_valid_section_title(c)]
    if valid_candidates:
        best = min(valid_candidates[:2], key=len)
        log.info("section_structural_match",
                 page_number=page.page_number,
                 section=best)
        return best

    # PRIORITY 3 — First short uppercase-starting line that isn't a date/number
    for line in lines[:5]:   # only look at top 5 lines of page
        if re.match(r"^\d{1,2}\s+\w+\s+\d{4}$", line):
            continue
        if re.match(r"^\d+$", line):
            continue
        if len(line) >= 8 and len(line) <= 80 and line[0].isupper():
            clean = line.strip()[:80].rstrip(";:,")
            log.info("section_first_line_heuristic",
                     page_number=page.page_number,
                     section=clean)
            return clean

    # PRIORITY 4 — Fallback to previous section
    log.info("section_fallback_used",
             page_number=page.page_number,
             fallback=prev_section)
    return prev_section

def enrich_metadata(doc: ParsedDocument) -> ParsedDocument:
    """
    Assigns high-quality section titles to all pages in the document.
    """
    log.info("enrichment_start", filename=doc.filename)
    current_section = "General"
    
    for page in doc.pages:
        # Statefully track section content
        current_section = detect_section(page, current_section)
        page.section_title = current_section
        
    log.info("enrichment_complete", filename=doc.filename)
    return doc
