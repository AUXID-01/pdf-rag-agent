from typing import List, Dict, Any, Optional

def build_trace(
    query: str,
    rewrite_result: Dict[str, Any],
    hits: List[Dict],
    gate_result: Any,
    response_type: str,
    citations: List[Any]
) -> Dict[str, Any]:
    """
    Constructs a structured trace object for evaluation-grade traceability.
    """
    # retrieval_hits: top 3 hits
    retrieval_hits = []
    for hit in hits[:3]:
        retrieval_hits.append({
            "page": hit.get("page", 0),
            "section": hit.get("section", "General"),
            "score": hit.get("rerank_score", 1.0 - hit.get("distance", 1.0)),
            "text_preview": hit.get("preview", "")
        })

    # top_score: hits[0].rerank_score
    top_score = hits[0].get("rerank_score", 0.0) if hits else 0.0

    trace = {
        "query": query,
        "rewritten_query": rewrite_result.get("rewritten_query", query),
        "is_followup": rewrite_result.get("was_rewritten", False),
        "retrieval_hits": retrieval_hits,
        "top_score": top_score,
        "gate_decision": "PASS" if gate_result.state == "ANSWERABLE" else "FAIL",
        "gate_reason": gate_result.reason,
        "response_type": response_type,
        "citations": citations,
        # PHASE 13 — OCR TRACE
        "ocr_used": any(h.get("ocr_quality") != "good" for h in hits) if hits else False,
        "ocr_quality": "low" if any(h.get("ocr_quality") == "low" for h in hits) else "good",
        # PHASE 14 — RERANK TRACE
        "reranked": True,
        "top_score": top_score,
        "scores": [h.get("score", 0.0) for h in retrieval_hits]
    }
    
    return trace
