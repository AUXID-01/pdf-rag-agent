from typing import List, Dict
from logs.logger import get_logger
from logs.schema import ParsedPage, ParsedDocument
from config import CHUNK_SIZE, CHUNK_OVERLAP

log = get_logger("ingestion.chunker")

def chunk_pages(doc: ParsedDocument) -> List[Dict]:
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
    
    # PHASE 13 — OCR QUALITY ADJUSTMENTS
    chunk_limit = CHUNK_SIZE
    overlap_limit = CHUNK_OVERLAP
    ocr_quality = "good"

    if doc.low_quality_ocr:
        # Smaller chunks for low-quality OCR text - help keep noisy context atomic
        chunk_limit = 150
        overlap_limit = 50
        ocr_quality = "low"
        log.warning("chunking_low_quality_ocr", source_doc=doc_id, chunk_size=chunk_limit)

    for page in pages:
        # metadata.enrich_metadata identifies the section_title before this step
        section_title = page.section_title or "General"
        text = page.text
        
        page_chunks = []
        
        if not text:
            log.warning("empty_page_skip", page_number=page.page_number)
            continue
            
        if len(text) <= chunk_limit:
            # Single chunk for short pages
            new_chunk = {
                "chunk_id": f"{doc_id}_p{page.page_number}_c{global_chunk_idx}",
                "page": page.page_number,
                "page_end": page.page_number,
                "section_title": section_title,
                "source_doc": doc_id,
                "text": text,
                "char_count": len(text),
                "ocr_quality": ocr_quality
            }
            page_chunks.append(new_chunk)
            global_chunk_idx += 1
            total_chars += len(text)
        else:
            # Sliding window sub-chunking for longer pages
            start = 0
            while start < len(text):
                end = start + chunk_limit
                chunk_text = text[start:end]
                
                new_chunk = {
                    "chunk_id": f"{doc_id}_p{page.page_number}_c{global_chunk_idx}",
                    "page": page.page_number,
                    "page_end": page.page_number,
                    "section_title": section_title,
                    "source_doc": doc_id,
                    "text": chunk_text,
                    "char_count": len(chunk_text),
                    "ocr_quality": ocr_quality
                }
                page_chunks.append(new_chunk)
                global_chunk_idx += 1
                total_chars += len(chunk_text)
                
                # Advance window by stride (size - overlap)
                start += (chunk_limit - overlap_limit)
                
                if start >= len(text):
                    break

        chunks.extend(page_chunks)
        log.info("page_chunked", page_number=page.page_number, section_title=section_title, num_chunks=len(page_chunks))

    avg_size = total_chars / len(chunks) if chunks else 0
    log.info("chunk_complete", total_chunks=len(chunks), avg_chunk_size=round(avg_size, 2))
    
    return chunks
