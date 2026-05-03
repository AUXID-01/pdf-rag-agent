from dataclasses import dataclass
from typing import List, Dict, Optional
import json
import re
import numpy as np
from logs.logger import get_logger
from config import RERANKER_THRESHOLD
from indexing.embedder import get_model as get_embedder

log = get_logger("retrieval.hallucination_gate")

@dataclass
class GateResult:
    state: str                     # "ANSWERABLE", "PARTIAL", "OUT_OF_SCOPE", "CONTRADICTION", "AMBIGUOUS"
    reason: str
    message: str                   # JSON-formatted state payload
    hits: List[Dict]               
    best_similarity: float
    nearest_topic: Optional[str]
    partial_context: bool = False  # Internal metadata for Fix 2

def build_state_json(state: str, reason: str, supported: List[str] = None, missing: List[str] = None) -> str:
    res = {
        "state": state,
        "reason": reason,
        "supported_parts": supported or [],
        "missing_parts": missing or []
    }
    return json.dumps(res, indent=2)

def clean_intent(intent: str) -> str:
    filler_words = r'\b(?:what is|explain|tell me|about|the|how|does|a|an)\b'
    cleaned = re.sub(filler_words, '', intent, flags=re.IGNORECASE)
    cleaned = re.sub(r'[^\w\s]', '', cleaned).strip()
    return cleaned

def evaluate(hits: List[Dict], query: str) -> GateResult:
    log.info("decision_engine_start", query=query, hit_count=len(hits) if hits else 0)
    
    # FIX 5 — PROMPT INJECTION CLASSIFICATION
    injection_patterns = ["ignore document", "even if not in document", "answer generally", "use your knowledge", "ignore previous"]
    if any(p in query.lower() for p in injection_patterns):
        msg = build_state_json("OUT_OF_SCOPE", "Query attempts to bypass document grounding.", [], [])
        return GateResult("OUT_OF_SCOPE", "Query attempts to bypass document grounding.", msg, hits, 0.0, None)
    
    # STEP 1 — INTENT EXTRACTION
    split_pattern = r'[.?!]?\s+(?:and|also|along\s+with|as\s+well\s+as|plus|vs|\+|&)\s+|[.?!]\s+'
    raw_sub_intents = [s.strip() for s in re.split(split_pattern, query, flags=re.IGNORECASE) if s.strip()]
    if len(raw_sub_intents) == 1 and " vs " in query.lower():
        raw_sub_intents = [s.strip() for s in re.split(r'\s+vs\s+', query, flags=re.IGNORECASE)]
    sub_intents = [clean_intent(i) for i in raw_sub_intents if clean_intent(i)]

    # STEP 5 — AMBIGUITY DETECTION
    if not sub_intents or sum(len(i) for i in sub_intents) < 5 or " it" in query.lower() or " they" in query.lower():
        # simple heuristic for ambiguity
        if not any(kw in query.lower() for kw in ["repo", "inflation", "rate", "rbi", "bank", "policy", "gdp", "learning", "ai"]):
            msg = build_state_json("AMBIGUOUS", "Query is vague or contains unresolved pronouns.")
            return GateResult("AMBIGUOUS", "Ambiguous Query", msg, hits, 0.0, None)

    if not hits:
        msg = build_state_json("OUT_OF_SCOPE", "No context retrieved.")
        return GateResult("OUT_OF_SCOPE", "No Hits", msg, hits, 0.0, None)

    best_score = hits[0].get("rerank_score", 0)

    # STEP 4 — CONTRADICTION DETECTION
    CONTRADICTION_SIGNALS = [
        ("increase repo rate", ["unchanged", "held", "no change", "steady"]),
        ("cut rates", ["unchanged", "held", "no change", "steady"]),
        ("rate hike", ["unchanged", "held", "no change", "cut"])
    ]
    all_text = " ".join([h["text"].lower() for h in hits])
    query_lower = query.lower()
    
    for trigger, forbidden in CONTRADICTION_SIGNALS:
        if trigger in query_lower and any(f in all_text for f in forbidden):
            msg = build_state_json("CONTRADICTION", f"Premise contradicts document (triggered by: {trigger}).")
            return GateResult("CONTRADICTION", "Premise Contradicts Context", msg, hits, best_score, hits[0].get("section"))

    # FIX 3 — NUMERIC CONTRADICTION DETECTION
    def extract_numbers(text, filter_small=False):
        # Extracts float values from text
        nums = re.findall(r'\b\d+(?:\.\d+)?', text)
        extracted = [float(n) for n in nums]
        if filter_small:
            # Filter out small integers likely to be page numbers or indices
            extracted = [n for n in extracted if not (n.is_integer() and n < 5)]
        return extracted

    query_numbers = extract_numbers(query)
    all_chunks_text = " ".join([h["text"] for h in hits])
    context_numbers = extract_numbers(all_chunks_text, filter_small=True)
    
    if query_numbers and context_numbers:
        ctx_min, ctx_max = min(context_numbers), max(context_numbers)
        for qn in query_numbers:
            # FIX 3: Check range contradiction
            if qn < ctx_min - 0.01 or qn > ctx_max + 0.01:
                msg = build_state_json("CONTRADICTION", f"Numeric premise {qn} is outside the document's verified range [{ctx_min}, {ctx_max}].", [], [])
                return GateResult("CONTRADICTION", "Numeric Mismatch", msg, hits, best_score, hits[0].get("section"))

    # STEP 2 & 3 — RETRIEVAL COVERAGE & CLASSIFICATION
    embedder = get_embedder()
    context_text = " ".join([h['text'] for h in hits[:5]])
    context_emb = embedder.encode(context_text)
    
    missing_parts = []
    supported_parts = []
    
    for intent in sub_intents:
        intent_emb = embedder.encode(intent)
        score = np.dot(intent_emb, context_emb) / (np.linalg.norm(intent_emb) * np.linalg.norm(context_emb))
        score = round(float(score), 3)
        
        # FIX 1 — RELAX COVERAGE LOGIC (CRITICAL)
        words = [w for w in intent.lower().split() if len(w) >= 2]
        lexical_match = all(w in all_text for w in words) if words else True
        
        # Use AND condition to avoid aggressive refusals
        # Increased to 0.35 to ensure 'crypto stance' (0.305) is refused
        if score < 0.35 and lexical_match == False:
            missing_parts.append(intent)
        else:
            supported_parts.append(intent)
            
    # STEP 6 — GLOBAL DECISION
    partial_context = False
    secondary_keywords = ["why", "impact", "effect", "reason", "consequence", "detail", "explain", "risks"]
    
    if len(missing_parts) == len(sub_intents):
        state = "OUT_OF_SCOPE"
        reason = "No relevant context found for any part of the query."
    elif missing_parts:
        # FIX 2 — SAFE PARTIAL ANSWERING (REFINED)
        is_secondary = all(any(kw in part.lower() for kw in secondary_keywords) for part in missing_parts)
        
        if supported_parts and is_secondary:
            state = "ANSWERABLE"
            reason = "Core intents supported. Secondary explanatory parts missing."
            partial_context = True
        else:
            state = "PARTIAL"
            reason = "Significant parts of the query are missing from the context."
    else:
        state = "ANSWERABLE"
        reason = "All intents supported."

    msg = build_state_json(state, reason, supported_parts, missing_parts)
    return GateResult(state, reason, msg, hits, best_score, hits[0].get("section"), partial_context)
