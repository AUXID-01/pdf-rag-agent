"""
ingestion/chunker.py
Responsibility: Split cleaned pages into section-aware chunks with max token budget.
Inputs: List[ParsedPage] (expected to be enriched with section_title)
Outputs: List[Chunk]
Dependencies: config.py, logs/schema.py
"""

from typing import List
from logs.logger import get_logger
from logs.schema import ParsedPage, Chunk, ParsedDocument
from config import CHUNK_SIZE, CHUNK_OVERLAP

log = get_logger("ingestion.chunker")

def chunk_pages(doc: ParsedDocument) -> List[Chunk]:
    """
    Splits cleaned and enriched pages into chunks.
    Ensures each chunk carries the correct section metadata from the page.
    """
    doc_id = doc.filename.lower().replace(" ", "_").rsplit(".", 1)[0]
    pages = doc.pages
    
    log.info("chunk_start", source_doc=doc_id, page_count=len(pages))
    
    chunks = []
    global_chunk_idx = 0
    total_chars = 0
    
    for page in pages:
        # metadata.enrich_metadata identifies the section_title before this step
        section_title = page.section_title or "General"
        text = page.raw_text
        
        page_chunks = []
        
        if not text:
            log.warning("empty_page_skip", page_no=page.page_no)
            continue
            
        if len(text) <= CHUNK_SIZE:
            # Single chunk for short pages
            new_chunk = Chunk(
                chunk_id=f"{doc_id}_p{page.page_no}_c{global_chunk_idx}",
                page_start=page.page_no,
                page_end=page.page_no,
                section_title=section_title,
                source_doc=doc_id,
                text=text,
                char_count=len(text)
            )
            page_chunks.append(new_chunk)
            global_chunk_idx += 1
            total_chars += len(text)
        else:
            # Sliding window sub-chunking for longer pages
            start = 0
            while start < len(text):
                end = start + CHUNK_SIZE
                chunk_text = text[start:end]
                
                new_chunk = Chunk(
                    chunk_id=f"{doc_id}_p{page.page_no}_c{global_chunk_idx}",
                    page_start=page.page_no,
                    page_end=page.page_no,
                    section_title=section_title,
                    source_doc=doc_id,
                    text=chunk_text,
                    char_count=len(chunk_text)
                )
                page_chunks.append(new_chunk)
                global_chunk_idx += 1
                total_chars += len(chunk_text)
                
                # Advance window by stride (size - overlap)
                start += (CHUNK_SIZE - CHUNK_OVERLAP)
                
                if start >= len(text):
                    break

        chunks.extend(page_chunks)
        log.info("page_chunked", page_no=page.page_no, section_title=section_title, num_chunks=len(page_chunks))

    avg_size = total_chars / len(chunks) if chunks else 0
    log.info("chunk_complete", total_chunks=len(chunks), avg_chunk_size=round(avg_size, 2))
    
    return chunks
