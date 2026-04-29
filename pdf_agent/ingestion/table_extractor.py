"""
ingestion/table_extractor.py
Responsibility: Detect and extract tables from PDF pages using pdfplumber.
Inputs: ParsedDocument (enriched with metadata)
Outputs: List[dict] — each dict is one extracted table as a structured text chunk
Dependencies: pdfplumber, logs/schema.py, logs/logger.py
"""

import pdfplumber
import uuid
from typing import List, Dict, Any
from logs.logger import get_logger
from logs.schema import ParsedDocument

log = get_logger("ingestion.table_extractor")

def format_table_as_text(table: List[List[Any]], page_num: int) -> str:
    """
    Converts a nested list table to a structured text block.
    Format:
    [Table | Page X]
    Column1 | Column2 | ...
    Row1Val | Row2Val | ...
    """
    if not table:
        return ""
    
    rows = []
    rows.append(f"[Table | Page {page_num}]")
    
    for row in table:
        # Clean multi-line cells: replace newlines with spaces and strip
        # Handle None values by converting to empty string
        cleaned_row = [
            str(cell).replace("\n", " ").strip() if cell is not None else "" 
            for cell in row
        ]
        
        # Only add the row if it contains at least one non-empty cell
        if any(cleaned_row):
            rows.append(" | ".join(cleaned_row))
            
    return "\n".join(rows)

def extract_tables(doc: ParsedDocument) -> List[Dict[str, Any]]:
    """
    Extracts all tables from the PDF and converts them into searchable chunks.
    
    Args:
        doc: The ParsedDocument object containing the source path and enriched metadata.
        
    Returns:
        A list of chunk dictionaries compatible with the indexing pipeline.
    """
    log.info("table_extraction_start", filename=doc.filename)
    table_chunks = []
    
    try:
        # We use a doc-level ID prefix for chunk consistency
        doc_prefix = doc.filename.lower().replace(" ", "_").rsplit(".", 1)[0]
        
        with pdfplumber.open(doc.source_path) as pdf:
            for i, page in enumerate(pdf.pages):
                # pdfplumber's extract_tables is generally robust for simple and medium complexity tables
                tables = page.extract_tables()
                
                if not tables:
                    continue
                
                # Fetch section title from enriched metadata if available
                # doc.pages uses 0-based indexing matching pdf.pages
                section_title = "Unknown"
                if i < len(doc.pages):
                    section_title = doc.pages[i].section_title or "General"

                for table_idx, table in enumerate(tables):
                    # Edge Case: Ignore empty or essentially empty (header-only) tables
                    if not table or len(table) < 2:
                        continue
                    
                    # Edge Case: Truncate massive tables to avoid LLM context overflow
                    # A 50-row table is already quite large for a single chunk
                    if len(table) > 50:
                        log.warning("table_truncated", page=i+1, table_idx=table_idx, rows=len(table))
                        table = table[:50]

                    # Convert to structured string
                    table_text = format_table_as_text(table, i + 1)
                    
                    if not table_text.strip():
                        continue
                        
                    # Build chunk dict matching ingestion/chunker.py schema
                    table_chunks.append({
                        "chunk_id": f"{doc_prefix}_tbl_p{i+1}_{table_idx}",
                        "page": i + 1,
                        "page_end": i + 1,
                        "section_title": section_title,
                        "source_doc": doc.filename,
                        "text": table_text,
                        "char_count": len(table_text),
                        "ocr_quality": "good",
                        "chunk_type": "table"  # Useful for downstream filtering/priority
                    })

        log.info("table_extraction_complete", count=len(table_chunks))
    except Exception as e:
        log.error("table_extraction_failed", error=str(e))
        
    return table_chunks

if __name__ == "__main__":
    # Example Usage Snippet
    print("Example Usage:")
    print("from ingestion.table_extractor import extract_tables")
    print("table_chunks = extract_tables(parsed_doc)")
    print("all_chunks = text_chunks + table_chunks")
