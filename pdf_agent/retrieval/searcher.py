"""
retrieval/searcher.py
Responsibility: Phase 6 Retrieval. Performs semantic search against ChromaDB using query embeddings.
Enforces strict document-level filtering to ensure results only come from the active document.
"""

from typing import List, Dict, Optional
import re
from indexing.embedder import Embedder
from indexing.vector_store import VectorStore
from config import TOP_K
from logs.logger import get_logger

log = get_logger("retrieval.searcher")

def build_preview(text: str, max_chars: int = 280) -> str:
    """
    Cleans and truncates a chunk of text for UI preview.
    Normalizes whitespace and avoids cutting words in half.
    """
    if not text or not isinstance(text, str) or not text.strip():
        return "No preview available."
    
    clean_text = " ".join(text.split()).strip()
    
    if len(clean_text) <= max_chars:
        return clean_text
    
    truncated = clean_text[:max_chars]
    last_space = truncated.rfind(" ")
    if last_space > int(max_chars * 0.85):
        truncated = truncated[:last_space]
        
    return truncated.rstrip() + "..."

def search_query(query: str, doc_id: Optional[str] = None, top_k: int = TOP_K) -> List[Dict]:
    """
    Encodes the input query and retrieves the most relevant chunks.
    Strictly filters results by document identity if doc_id is provided.
    
    Args:
        query: The user's natural language question.
        doc_id: Optional unique identifier (filename or doc_id) to restrict the search.
        top_k: Number of nearest neighbors to retrieve.
        
    Returns:
        A validated list of retrieval hits for the active document.
    """
    if not query or not query.strip():
        log.warning("retrieval_skip_empty_query")
        return []

    try:
        log.info("retrieval_start", query=query, doc_id=doc_id, top_k=top_k)

        # 1. Encode Query
        embedder = Embedder()
        query_embeddings = embedder.embed_text([query])
        
        if not query_embeddings:
            log.error("retrieval_failure", error="Embedding generation failed")
            return []
            
        query_vector = query_embeddings[0]
        log.info("retrieval_query_embedded")

        # 2. Open Persistent Store
        vector_store = VectorStore()
        vector_store.initialize()
        
        if not vector_store.collection:
            log.error("retrieval_failure", error="Vector store collection not initialized")
            return []

        # 3. Handle Filtering Strategy
        where_filter = None
        if doc_id:
            # We attempt filtering on 'source_doc' which is our project standard.
            # We also ensure the filter is valid for Chroma.
            where_filter = {"source_doc": doc_id}
            log.info("retrieval_filter_applied", doc_id=doc_id, field="source_doc")

        # 4. Query Collection
        try:
            results = vector_store.collection.query(
                query_embeddings=[query_vector],
                n_results=top_k,
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )
        except Exception as filter_err:
            log.warning("retrieval_filter_fallback", error=str(filter_err), doc_id=doc_id)
            # Fallback: Query all documents and rely on Python post-filtering
            results = vector_store.collection.query(
                query_embeddings=[query_vector],
                n_results=top_k * 2,  # Increase sample size for post-filtering
                include=["documents", "metadatas", "distances"]
            )

        # 5. Normalize and Strictly Verify Hits
        hits = []
        total_preview_len = 0
        
        if results and results.get("documents") and results["documents"]:
            documents = results["documents"][0]
            metadatas = results["metadatas"][0]
            distances = results["distances"][0]
            chroma_ids = results["ids"][0]

            for i in range(len(documents)):
                meta = metadatas[i]
                
                # Strict identification check (Requirement 3 & 4)
                # We check both 'source_doc' (modern) and 'doc_id' (legacy/alternative)
                actual_doc = meta.get("source_doc") or meta.get("doc_id")
                
                if doc_id and actual_doc != doc_id:
                    log.warning("retrieval_cross_doc_filtered", 
                                expected=doc_id, 
                                actual=actual_doc)
                    continue

                text_content = documents[i]
                preview_text = build_preview(text_content)
                total_preview_len += len(preview_text)
                
                hits.append({
                    "chunk_id": meta.get("chunk_id", chroma_ids[i]),
                    "text": text_content,
                    "preview": preview_text,
                    "distance": float(distances[i]),
                    "page": meta.get("page_start"),
                    "section": meta.get("section_title"),
                    "doc_id": actual_doc
                })

        # Final truncation to requested top_k after post-filtering
        hits = hits[:top_k]

        log.info("retrieval_complete", 
                 hit_count=len(hits), 
                 preview_length=total_preview_len)
        return hits

    except Exception as e:
        log.error("retrieval_failure", error=str(e))
        return []
