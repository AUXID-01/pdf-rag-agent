"""
ingestion/cleaner.py
Responsibility: Strip headers, footers, page numbers, and noise from extracted page text.
Inputs: List[ParsedPage]
Outputs: List[ParsedPage] (cleaned)
Dependencies: config.py, logs/schema.py
"""

import re
from typing import List
from collections import Counter
from logs.logger import get_logger
from logs.schema import ParsedPage, ParsedDocument

log = get_logger("ingestion.cleaner")

def clean_pages(doc: ParsedDocument) -> ParsedDocument:
    """
    Applies several cleaning steps to each page's raw_text in the document.
    """
    pages = doc.pages
    # Build frequency map for repeated lines across all pages
    all_lines = []
    for page in pages:
        all_lines.extend([line.strip() for line in page.text.split("\n") if line.strip()])
    
    line_counts = Counter(all_lines)
    repeated_lines = {line for line, count in line_counts.items() if count >= 3}
    
    log.info("repeated_noise_detected", repeated_line_count=len(repeated_lines))

    # Regex patterns
    RE_PAGE_NUM = re.compile(r"^\s*\d+\s*$")
    RE_NON_ALNUM = re.compile(r"^[^a-zA-Z0-9]*$")
    RE_TRIPLE_NEWLINE = re.compile(r"\n{3,}")

    cleaned_pages = []

    for page in pages:
        chars_before = len(page.text)
        lines = page.text.split("\n")
        lines_before = len(lines)
        
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            
            # STEP 1: Remove page number lines
            if RE_PAGE_NUM.match(line):
                continue
            
            # STEP 2: Remove repeated header/footer noise
            if stripped in repeated_lines:
                continue
            
            # STEP 4: Remove lines that are purely non-alphanumeric
            # Note: This also filters empty lines if the regex is ^[^a-zA-Z0-9]*$
            # but if we want to keep some structure, maybe we only remove if it has NO alphanumeric
            if RE_NON_ALNUM.match(line) and stripped != "":
                continue

            cleaned_lines.append(line)

        # Rejoin and apply STEP 3: Strip excessive whitespace
        temp_text = "\n".join(cleaned_lines)
        temp_text = RE_TRIPLE_NEWLINE.sub("\n\n", temp_text)
        raw_text_cleaned = temp_text.strip()
        
        chars_after = len(raw_text_cleaned)
        lines_after = len(raw_text_cleaned.split("\n")) if raw_text_cleaned else 0
        lines_removed = lines_before - lines_after

        log.info(
            "page_cleaned", 
            page_number=page.page_number, 
            chars_before=chars_before, 
            chars_after=chars_after, 
            lines_removed=lines_removed
        )

        cleaned_pages.append(
            ParsedPage(
                page_number=page.page_number,
                text=raw_text_cleaned,
                blocks=page.blocks
            )
        )

    doc.pages = cleaned_pages
    return doc
