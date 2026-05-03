from typing import List, Dict, Any, Optional

def build_trace(
    query: str,
    rewrite_result: Dict[str, Any],
    hits: List[Dict],
    gate_result: Any,
    response_type: str,
    citations: List[Any],
    gate2_result: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Constructs a structured trace object for evaluation-grade traceability.
    """
    import json
    
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

    # Categorize query type
    query_type = "SHIFT"
    query_reason = "Query is self-contained or a new topic."
    
    if rewrite_result.get("needs_clarification"):
        query_type = "AMBIGUOUS"
        query_reason = "Query is too vague to resolve contextually."
    elif rewrite_result.get("was_rewritten"):
        query_lower = query.lower()
        pronouns = ["it", "its", "they", "them", "their", "this", "that", "there", "those", "these"]
        shorthand = ["that section", "that part", "the same", "the above", "the previous"]
        continuation = ["what about", "tell me more", "explain further", "summarize it", "go on"]
        
        if any(p in query_lower for p in pronouns) or any(s in query_lower for s in shorthand):
            query_type = "REFERENCE"
            query_reason = "Query references previous entities or sections."
        elif any(c in query_lower for c in continuation):
            query_type = "CONTINUATION"
            query_reason = "Query is a follow-up request for detail or continuation."
        else:
            query_type = "CONTINUATION"
            query_reason = "Query was rewritten based on history."

    # Parse gate message for parts
    try:
        gate_data = json.loads(gate_result.message)
    except:
        gate_data = {}

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
        "scores": [h.get("rerank_score", 0.0) for h in retrieval_hits],
        
        # NEW: EXPLAINABILITY LAYER
        "explainability": {
            "query_analysis": {
                "is_followup": rewrite_result.get("was_rewritten", False),
                "type": query_type,
                "reason": query_reason
            },
            "rewrite": {
                "original": query,
                "rewritten": rewrite_result.get("rewritten_query", query),
                "applied": rewrite_result.get("was_rewritten", False),
                "confidence": None,
                "reason": "Contextual resolution required" if rewrite_result.get("was_rewritten") else "Self-contained query"
            },
            "retrieval": {
                "top_score": top_score,
                "score_distribution": [h.get("rerank_score", 0.0) for h in hits[:5]],
                "sections": list(set([h.get("section", "General") for h in hits])),
                "coverage": "HIGH" if top_score > 0.6 else "MEDIUM" if top_score > 0.4 else "LOW",
                "reason": "Top rerank score indicates sufficient grounding" if top_score > 0.4 else "Retrieved context has low semantic relevance"
            },
            "decision_engine": {
                "state": gate_result.state,
                "supported_parts": gate_data.get("supported_parts", []),
                "missing_parts": gate_data.get("missing_parts", []),
                "reason": gate_result.reason
            },
            "generation": {
                "llm_called": response_type == "answer",
                "partial_context": getattr(gate_result, "partial_context", False),
                "reason": "Sufficient context to attempt generation" if gate_result.state == "ANSWERABLE" else "Generation blocked by Gate 1"
            },
            "validation": {
                "gate2_passed": gate2_result.get("passed", False) if gate2_result else False,
                "reason": gate2_result.get("reason", "Not validated") if gate2_result else "Not validated"
            }
        }
    }
    
    return trace
