from typing import List, Dict, Tuple
from ingestion.metadata import clean_section_title

def build_clean_citations(hits: List[Dict]) -> List[Tuple[int, str]]:
    """
    Extracts, sanitizes, deduplicates, and limits citations from retrieval hits.
    Priority: Highest rerank_score if available.
    """
    if not hits:
        return []

    seen = set()
    cleaned = []

    for hit in hits:
        # MANDATORY SECOND LAYER OF SANITIZATION
        # Pass the chunk text to enable inference if section is invalid
        section = clean_section_title(
            hit.get('section', 'General'), 
            text=hit.get('text', '')
        )
        page = hit.get('page', 0)
        key = (page, section)

        if key not in seen:
            seen.add(key)
            cleaned.append((page, section))

    # Sort by relevance if available (rerank_score)
    # Using .get() for dictionary access
    if 'rerank_score' in hits[0]:
        cleaned = sorted(
            cleaned,
            key=lambda x: next(
                (h.get('rerank_score', 0) for h in hits if h.get('page') == x[0]),
                0
            ),
            reverse=True
        )

    return cleaned[:2] # Limit to max 2 citations as per requirement
