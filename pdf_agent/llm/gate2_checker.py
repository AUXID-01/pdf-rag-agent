from typing import List, Dict
import re
from llm.response_parser import ParsedResponse, Citation
from logs.logger import get_logger
from indexing.embedder import get_model as get_embedder
import numpy as np

log = get_logger("llm.gate2_checker")

def validate_citations_against_chunks(
    parsed: ParsedResponse,
    retrieved_chunks: List[dict]
) -> dict:
    """
    STRICT PRODUCTION VALIDATION:
    1. Answer is not empty
    2. At least one citation exists
    3. Each cited chunk_id exists in retrieved chunks
    4. Each cited page exactly matches the source chunk's page
    """

    if not parsed.answer_text.strip():
        return {"passed": False, "reason": "Empty answer"}

    if not parsed.citations:
        return {"passed": False, "reason": "No citations found in response."}

    refusal_phrases = ["cannot answer", "don't know", "insufficient context", "not mentioned", "not fully supported"]
    if any(p in parsed.answer_text.lower() for p in refusal_phrases):
        return {"passed": False, "reason": "LLM attempted refusal"}

    # Map retrieved chunks by ID for O(1) lookup
    retrieved_map = {c["chunk_id"]: c for c in retrieved_chunks if "chunk_id" in c}
    
    unverified = []
    for citation in parsed.citations:
        # 1. Verify chunk_id exists in retrieved set
        if citation.chunk_id not in retrieved_map:
            unverified.append(f"Invalid Chunk ID: {citation.chunk_id}")
            continue
            
        source_chunk = retrieved_map[citation.chunk_id]
        
        # 2. Verify Page EXACT match
        if citation.page != source_chunk.get("page"):
            unverified.append(f"Page mismatch for {citation.chunk_id}: Cited {citation.page} vs Source {source_chunk.get('page')}")

        # 3. Semantic Validation (Gate 2 Upgrade)
        embedder = get_embedder()
        answer_emb = embedder.encode(parsed.answer_text)
        chunk_emb = embedder.encode(source_chunk["text"])
        score = np.dot(answer_emb, chunk_emb) / (np.linalg.norm(answer_emb) * np.linalg.norm(chunk_emb))
        
        if score < 0.25:
            return {"passed": False, "reason": "Ungrounded answer"}

    if unverified:
        return {
            "passed": False,
            "reason": f"Grounding failure: {', '.join(unverified)}"
        }

    return {"passed": True, "reason": "All citations strictly verified."}

def post_process_answer(parsed: ParsedResponse) -> Dict:
    """
    FIX 1 & 3: Clean up the answer text and citations.
    - Aggressively deduplicates semantically identical sentences.
    - Normalizes numeric values.
    - Filters citations to only those present in text (Max 2).
    """
    text = parsed.answer_text
    
    # 1. Normalize values (e.g., 6.50% -> 6.5%)
    text = re.sub(r'(\d+)\.0+%', r'\1%', text)
    text = re.sub(r'(\d+\.\d*[1-9])0+%', r'\1%', text)
    
    # 2. Aggressive Deduplication (FIX 1)
    # Split by common sentence delimiters
    raw_sentences = re.split(r'(?<=[.!?])\s+', text)
    seen_normalized = set()
    unique_sentences = []
    
    citation_regex = re.compile(r'\[ID:\s*.*?\|.*?\|.*?\]')
    
    for s in raw_sentences:
        # Strip citations and non-alphanumeric for a "semantic" comparison
        s_no_cite = citation_regex.sub('', s).strip()
        s_norm = re.sub(r'[^\w\s]', '', s_no_cite).lower().strip()
        
        if s_norm and s_norm not in seen_normalized:
            unique_sentences.append(s.strip())
            seen_normalized.add(s_norm)
    
    clean_text = " ".join(unique_sentences)
    
    # 3. Filter Citations (FIX 3)
    filtered_citations = []
    seen_ids = set()
    for citation in parsed.citations:
        if citation.chunk_id in clean_text and citation.chunk_id not in seen_ids:
            filtered_citations.append(citation)
            seen_ids.add(citation.chunk_id)
        if len(filtered_citations) >= 2:
            break
            
    if not clean_text or not filtered_citations:
        raise ValueError("Post-processing resulted in empty answer or no citations")
            
    return {
        "answer_text": clean_text,
        "citations": filtered_citations
    }
