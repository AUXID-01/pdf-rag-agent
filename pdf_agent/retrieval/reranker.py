from typing import List, Dict
from sentence_transformers import SentenceTransformer, util
from config import RERANKER_MODEL, RERANKER_TOP_K, RERANKER_THRESHOLD
from logs.logger import get_logger
import streamlit as st

log = get_logger("retrieval.reranker")

@st.cache_resource
def get_bi_encoder() -> SentenceTransformer:
    log.info("bi_encoder_load_start", model=RERANKER_MODEL)
    model = SentenceTransformer(RERANKER_MODEL)
    log.info("bi_encoder_load_complete")
    return model

def rerank(query: str, hits: List[Dict], is_followup: bool = False) -> List[Dict]:
    """
    Improved Phase 14 Reranker with Stability Fixes:
    1. Adaptive thresholds for follow-ups
    2. Guaranteed minimum recall (no empty results)
    3. Detailed debug tracing
    """
    if not hits:
        return []

    try:
        model = get_bi_encoder()
        query_emb = model.encode(query, convert_to_tensor=True)
        
        raw_hits = hits.copy()
        
        # 1. Scoring & Boosting
        for hit in hits:
            hit_emb = model.encode(hit["text"], convert_to_tensor=True)
            score = util.cos_sim(query_emb, hit_emb).item()
            
            # Metadata Boost
            query_lower = query.lower()
            section_lower = hit.get("section", "").lower()
            boost_keywords = ["inflation", "growth", "liquidity", "rate", "repo", "policy"]
            for kw in boost_keywords:
                if kw in query_lower and kw in section_lower:
                    score += 0.1
                    break
            
            hit["rerank_score"] = score

        # 2. Adaptive Thresholding
        effective_threshold = 0.15 if is_followup else RERANKER_THRESHOLD
        
        # 3. Sort & Filter
        hits = sorted(hits, key=lambda x: x["rerank_score"], reverse=True)
        filtered_hits = [h for h in hits if h["rerank_score"] >= effective_threshold]
        
        # 4. Guarantee Minimum Retrieval (CRITICAL)
        if not filtered_hits:
            log.warning("rerank_threshold_all_filtered", threshold=effective_threshold)
            filtered_hits = hits[:2] if len(hits) >= 2 else hits[:1]

        # 5. Mandatory Debug Tracing
        log.info("rerank_debug",
                 raw_count=len(raw_hits),
                 after_rerank=len(hits),
                 after_filter=len(filtered_hits),
                 top_score=hits[0]["rerank_score"] if hits else None,
                 effective_threshold=effective_threshold,
                 is_followup=is_followup)
        
        return filtered_hits[:RERANKER_TOP_K]

    except Exception as e:
        log.error("rerank_failure", error=str(e))
        return hits[:RERANKER_TOP_K]
