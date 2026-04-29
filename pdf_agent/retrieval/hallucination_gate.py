from dataclasses import dataclass
from typing import List, Dict, Optional
from logs.logger import get_logger
from config import SIMILARITY_THRESHOLD, SCATTER_THRESHOLD, RERANKER_THRESHOLD

log = get_logger("retrieval.hallucination_gate")

@dataclass
class GateResult:
    passed: bool
    reason: str                    # "PASS", "NO_RESULTS", "LOW_CONFIDENCE", "SCATTERED_RESULTS"
    message: str                   # Human-readable explanation
    hits: List[Dict]               # Empty list if refused, original hits if passed
    best_similarity: float         # 0.0 if no hits
    nearest_topic: Optional[str]   # Section title of best hit even on refusal, None if no hits

REFUSAL_TEMPLATE = (
    "Your question asks about: '{query_topic}'.\n\n"
    "I searched the uploaded document across all sections and found no sufficiently relevant content.\n"
    "{nearest_hint}"
    "Please ask about topics explicitly covered in the document."
)

def evaluate(hits: List[Dict], query: str) -> GateResult:
    log.info("gate_evaluation_start", query=query, hit_count=len(hits) if hits else 0)
    
    if not hits:
        nearest_hint = ""
        message = REFUSAL_TEMPLATE.format(query_topic=query, nearest_hint=nearest_hint)
        
        result = GateResult(
            passed=False,
            reason="NO_RESULTS",
            message=message,
            hits=[],
            best_similarity=0.0,
            nearest_topic=None
        )
        log.info("gate_result", passed=result.passed, reason=result.reason, best_sim=result.best_similarity)
        return result
        
    similarities = [1.0 - hit.get("distance", 1.0) for hit in hits]
    best_similarity = max(similarities)
    best_hit = hits[similarities.index(best_similarity)]
    
    nearest_topic = best_hit.get("section")
    page = best_hit.get("page")
    
    nearest_hint = f"The closest content found was in **Page {page}**, Section **{nearest_topic}** \u2014 but it does not directly answer your question.\n\n"
    
    # Rule 2 — CrossEncoder Score Gate
    # After reranking, hits carry rerank_score (higher = better)
    # If top reranked chunk is below threshold, refuse
    best_score = hits[0].get("rerank_score", None)

    if best_score is None:
        # Reranker did not run — fall back to similarity check
        best_similarity = 1 - hits[0]["distance"]
        if best_similarity < SIMILARITY_THRESHOLD:
            result = GateResult(
                passed=False,
                reason="LOW_CONFIDENCE",
                message=REFUSAL_TEMPLATE.format(query_topic=query, nearest_hint=nearest_hint),
                hits=[],
                best_similarity=best_similarity,
                nearest_topic=hits[0].get("section")
            )
            log.info("gate_result", passed=result.passed, reason=result.reason, best_sim=result.best_similarity)
            return result
    else:
        best_similarity = best_score
        if best_score < RERANKER_THRESHOLD:
            result = GateResult(
                passed=False,
                reason="LOW_CONFIDENCE",
                message=REFUSAL_TEMPLATE.format(query_topic=query, nearest_hint=nearest_hint),
                hits=[],
                best_similarity=best_score,
                nearest_topic=hits[0].get("section")
            )
            log.info("gate_result", passed=result.passed, reason=result.reason, best_sim=result.best_similarity)
            return result
        
    # Rule 2B — Assertion Gate
    # If query contains a strong factual claim phrased as established truth,
    # check if the top chunk text contradicts it directly.
    CONTRADICTION_SIGNALS = [
        ("cut rates", ["unchanged", "held", "no change", "status quo"]),
        ("rate hike", ["unchanged", "held", "no change", "cut"]),
        ("reduced", ["unchanged", "increased", "raised"]),
    ]

    all_text = " ".join([h["text"].lower() for h in hits])
    query_lower = query.lower()

    for trigger_phrase, contradiction_words in CONTRADICTION_SIGNALS:
        if trigger_phrase in query_lower:
            if any(word in all_text for word in contradiction_words):
                nearest = hits[0].get("section", "Unknown Section")
                page = hits[0].get("page", "?")
                result = GateResult(
                    passed=False,
                    reason="CONTRADICTED_PREMISE",
                    message=REFUSAL_TEMPLATE.format(
                        query_topic=query[:80],
                        nearest_hint=f"The document content in **Page {page}**, Section **{nearest}** appears to contradict the premise of your question.\n\n"
                    ),
                    hits=[],
                    best_similarity=best_similarity,
                    nearest_topic=nearest
                )
                log.info("gate_result", passed=result.passed, reason=result.reason, best_sim=result.best_similarity)
                return result
        
    # Rule 3 — Scatter Check
    # Only refuse if the TOP chunk is strong but MOST chunks are weak.
    # A single strong hit is still useful. Refuse only if median is also weak.
    if len(hits) >= 3:
        scores = sorted([h.get("rerank_score", 0) for h in hits], reverse=True)
        top_score = scores[0]
        median_score = scores[len(scores) // 2]
        
        if top_score > RERANKER_THRESHOLD and median_score < SCATTER_THRESHOLD:
            nearest = hits[0].get("section", "Unknown")
            page = hits[0].get("page", "?")
            result = GateResult(
                passed=False,
                reason="SCATTERED_RESULTS",
                message=REFUSAL_TEMPLATE.format(
                    query_topic=query[:80],
                    nearest_hint=f"The closest content found was in **Page {page}**, Section **{nearest}** — but it does not directly answer your question.\n\n"
                ),
                hits=[],
                best_similarity=top_score,
                nearest_topic=nearest
            )
            log.info("gate_result", passed=result.passed, reason=result.reason, best_sim=result.best_similarity)
            return result
        
    result = GateResult(
        passed=True,
        reason="PASS",
        message="",
        hits=hits,
        best_similarity=best_similarity,
        nearest_topic=nearest_topic
    )
    log.info("gate_result", passed=result.passed, reason=result.reason, best_sim=result.best_similarity)
    return result
