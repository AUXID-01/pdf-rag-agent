import sys
import numpy as np
import re
PROJECT_ROOT = r"e:\Stair Digital Assignment\pdf_agent"
sys.path.append(PROJECT_ROOT)
from retrieval.hallucination_gate import evaluate, clean_intent
from retrieval.searcher import search_query
from indexing.embedder import get_model

embedder = get_model()

def debug_regression_intent(query, doc_id):
    hits = search_query(query, doc_id)
    all_text = " ".join([h["text"].lower() for h in hits])
    context_emb = embedder.encode(all_text)
    
    # Intent Extraction
    split_pattern = r'[.?!]?\s+(?:and|also|along\s+with|as\s+well\s+as|plus|vs|\+|&)\s+|[.?!]\s+'
    raw_sub_intents = [s.strip() for s in re.split(split_pattern, query, flags=re.IGNORECASE) if s.strip()]
    sub_intents = [clean_intent(i) for i in raw_sub_intents if clean_intent(i)]
    
    print(f"\n--- Debugging Query: {query} ---")
    missing_parts = []
    supported_parts = []
    for intent in sub_intents:
        intent_emb = embedder.encode(intent)
        score = np.dot(intent_emb, context_emb) / (np.linalg.norm(intent_emb) * np.linalg.norm(context_emb))
        
        words = [w for w in intent.lower().split() if len(w) >= 2]
        lex_ratio = sum(1 for w in words if w in all_text) / len(words) if words else 1.0
        
        print(f"Intent: '{intent}'")
        print(f"  Score: {score:.3f}")
        print(f"  Lex Ratio: {lex_ratio:.3f}")
        
        if score < 0.25 and lex_ratio == 0:
            missing_parts.append(intent)
            print("  -> Marked MISSING")
        else:
            supported_parts.append(intent)
            print("  -> Marked SUPPORTED")

    gate = evaluate(hits, query)
    print(f"Final State: {gate.state}")
    print(f"Reason: {gate.reason}")

debug_regression_intent("repo rate and crypto stance", "RBI-Monetary-Policy-October-2023.pdf")
