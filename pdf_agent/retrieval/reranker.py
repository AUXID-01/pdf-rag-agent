"""
retrieval/reranker.py
Responsibility: Stage 2 retrieval. Re-scores top-k chunks using CrossEncoder.
Input: top-20 chunks from ChromaDB.
Output: top-5 reranked chunks with rerank_score attached.
"""

from typing import List, Dict
from sentence_transformers import CrossEncoder
from config import RERANKER_MODEL, RERANKER_TOP_K
from logs.logger import get_logger

log = get_logger("retrieval.reranker")

import streamlit as st

@st.cache_resource
def get_reranker() -> CrossEncoder:
    log.info("reranker_load_start", model=RERANKER_MODEL)
    reranker = CrossEncoder(RERANKER_MODEL)
    log.info("reranker_load_complete")
    return reranker

def rerank(query: str, hits: List[Dict]) -> List[Dict]:
    """
    Re-scores hits using CrossEncoder and returns top RERANKER_TOP_K results.
    Attaches rerank_score to each hit.
    """
    if not hits:
        return []

    try:
        reranker = get_reranker()
        pairs = [(query, hit["text"]) for hit in hits]
        
        log.info("rerank_start", candidate_count=len(pairs))
        import numpy as np
        raw_scores = reranker.predict(pairs)
        # Sigmoid normalization: converts raw logits to 0-1 probability space
        scores = 1 / (1 + np.exp(-raw_scores))
        log.info("rerank_complete")

        for i, hit in enumerate(hits):
            hit["rerank_score"] = float(scores[i])

        reranked = sorted(hits, key=lambda x: x["rerank_score"], reverse=True)
        return reranked[:RERANKER_TOP_K]

    except Exception as e:
        log.error("rerank_failure", error=str(e))
        # Fallback: return original hits unmodified
        return hits[:RERANKER_TOP_K]
