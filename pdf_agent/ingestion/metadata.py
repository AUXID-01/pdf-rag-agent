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
    Implements validation and fallback strategies.
    """
    lines = [line.strip() for line in page.raw_text.split("\n") if line.strip()]
    if not lines:
        return prev_section

    candidates = []
    
    # HEURISTIC 1 & 2: Structural patterns (Numbered, ALL CAPS, Title Case)
    for line in lines:
        is_pattern_match = False
        
        # Pattern 1: Numbered Match
        if RE_SECTION_NUM.match(line) and len(line) <= 80:
            is_pattern_match = True
        # Pattern 2: ALL CAPS heading
        elif 4 <= len(line) <= 80 and line.isupper() and len(line.split()) >= 2:
            is_pattern_match = True
        # Pattern 3: Title Case heading
        elif 4 <= len(line) <= 80 and line.istitle() and not line.endswith((".", ",")):
            is_pattern_match = True
            
        if is_pattern_match:
            candidates.append(line)

    # HEURISTIC 4: Also consider the very first non-empty line as a candidate
    if lines and lines[0] not in candidates and len(lines[0]) <= 80:
        candidates.append(lines[0])

    # Filter candidates by quality
    valid_candidates = []
    for cand in candidates:
        if is_valid_section_title(cand):
            valid_candidates.append(cand)
        else:
            log.info("section_candidate_rejected", page_no=page.page_no, rejected=cand)

    # Selection & Fallback Logic (Requirement 5)
    if valid_candidates:
        # Prefer "nearby shorter heading candidate" (Requirement 5)
        # We take the first valid one found (nearby start of page), 
        # but if there are multiple, we pick the shortest one among them to avoid fragments.
        # Here we just take the shortest of the first 2 candidates for a balance.
        best_candidate = min(valid_candidates[:2], key=len)
        log.info("section_title_finalized", page_no=page.page_no, section=best_candidate)
        return best_candidate

    # Use previous valid section or absolute fallback
    log.info("section_fallback_used", page_no=page.page_no, fallback=prev_section)
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
