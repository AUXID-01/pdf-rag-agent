from dataclasses import dataclass
from typing import List, Dict, Optional
from logs.logger import get_logger
from config import SIMILARITY_THRESHOLD, SCATTER_THRESHOLD, RERANKER_THRESHOLD
from ingestion.metadata import clean_section_title

log = get_logger("retrieval.hallucination_gate")

@dataclass
class GateResult:
    passed: bool
    reason: str                    # "PASS", "NO_RESULTS", "LOW_CONFIDENCE", "SCATTERED_RESULTS"
    message: str                   # Human-readable explanation
    hits: List[Dict]               # Empty list if refused, original hits if passed
    best_similarity: float         # 0.0 if no hits
    nearest_topic: Optional[str]   # Section title of best hit even on refusal, None if no hits

def build_refusal_response(query: str, hits: List[Dict], gate_reason: str) -> str:
    """
    Upgraded refusal system that classifies failures into specific types:
    - OUT_OF_SCOPE: No relevant content at all.
    - FALSE_ASSUMPTION: Query contains "how/why/when did" but doc doesn't support it.
    - PARTIAL_MATCH: Related content found but not specific enough.
    """
    query_lower = query.lower()
    
    # 1. Classification Logic
    if gate_reason == "NO_RESULTS" or (hits and hits[0].get('rerank_score', 0) < 0.15):
        refusal_type = "OUT_OF_SCOPE"
    elif any(kw in query_lower for kw in ["why did", "when did", "how did"]) or gate_reason == "CONTRADICTED_PREMISE":
        refusal_type = "FALSE_ASSUMPTION"
    else:
        refusal_type = "PARTIAL_MATCH"

    # 2. Template Generation
    response = f"Your question asks about: '{query}'.\n\n"

    if refusal_type == "OUT_OF_SCOPE":
        response += "This topic is not covered in the uploaded document.\n\n"
        response += "I searched across all sections but found no relevant content.\n\n"
        response += "Please ask about topics explicitly discussed in the document."

    elif refusal_type == "FALSE_ASSUMPTION":
        response += "However, this assumes something that is not supported by the document.\n\n"
        response += "I searched across all sections but found no evidence for this claim.\n\n"
        if hits:
            best_hit = hits[0]
            page = best_hit.get("page", "?")
            section = clean_section_title(best_hit.get("section"), best_hit.get("text", ""))
            response += f"The closest related content appears in Page {page}, Section {section}, but it does not support this assumption.\n\n"
        response += "Please verify the premise or ask about content directly present in the document."

    else:  # PARTIAL_MATCH
        response += "I searched the document and found related content, but it does not directly answer your question.\n\n"
        if hits:
            best_hit = hits[0]
            page = best_hit.get("page", "?")
            section = clean_section_title(best_hit.get("section"), best_hit.get("text", ""))
            response += f"The closest related content appears in Page {page}, Section {section}.\n\n"
        response += "Please refine your query based on the document content."

    return response

# Legacy template (for reference, but now handled by build_refusal_response)
REFUSAL_TEMPLATE = ""

def evaluate(hits: List[Dict], query: str) -> GateResult:
    log.info("gate_evaluation_start", query=query, hit_count=len(hits) if hits else 0)
    
    if not hits:
        message = build_refusal_response(query, [], "NO_RESULTS")
        
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
    
    # PHASE 13 — OCR QUALITY CONFIDENCE ADJUSTMENT
    ocr_low_hits = [h for h in hits if h.get("ocr_quality") == "low"]
    if ocr_low_hits:
        # Apply a 20% penalty to similarities if the content is low-quality OCR
        # This increases likelihood of refusal for noisy/scanned content
        similarities = [s * 0.8 if hits[i].get("ocr_quality") == "low" else s for i, s in enumerate(similarities)]
        log.warning("gate_ocr_penalty_applied", count=len(ocr_low_hits))

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
                message=build_refusal_response(query, hits, "LOW_CONFIDENCE"),
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
                message=build_refusal_response(query, hits, "LOW_CONFIDENCE"),
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
                result = GateResult(
                    passed=False,
                    reason="CONTRADICTED_PREMISE",
                    message=build_refusal_response(query, hits, "CONTRADICTED_PREMISE"),
                    hits=[],
                    best_similarity=best_similarity,
                    nearest_topic=hits[0].get("section")
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
            result = GateResult(
                passed=False,
                reason="SCATTERED_RESULTS",
                message=build_refusal_response(query, hits, "SCATTERED_RESULTS"),
                hits=[],
                best_similarity=top_score,
                nearest_topic=hits[0].get("section")
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
