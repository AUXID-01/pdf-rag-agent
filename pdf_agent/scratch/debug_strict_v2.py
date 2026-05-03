import sys
import numpy as np
import re
PROJECT_ROOT = r"e:\Stair Digital Assignment\pdf_agent"
sys.path.append(PROJECT_ROOT)
from retrieval.hallucination_gate import evaluate, clean_intent
from retrieval.searcher import search_query
from indexing.embedder import get_model

embedder = get_model()

def debug_intent(query, doc_id):
    hits = search_query(query, doc_id)
    all_text = " ".join([h["text"].lower() for h in hits])
    context_emb = embedder.encode(all_text)
    
    # Intent Extraction
    split_pattern = r'[.?!]?\s+(?:and|also|along\s+with|as\s+well\s+as|plus|vs|\+|&)\s+|[.?!]\s+'
    raw_sub_intents = [s.strip() for s in re.split(split_pattern, query, flags=re.IGNORECASE) if s.strip()]
    sub_intents = [clean_intent(i) for i in raw_sub_intents if clean_intent(i)]
    
    print(f"\n--- Debugging Query: {query} ---")
    for intent in sub_intents:
        intent_emb = embedder.encode(intent)
        score = np.dot(intent_emb, context_emb) / (np.linalg.norm(intent_emb) * np.linalg.norm(context_emb))
        
        words = [w for w in intent.lower().split() if len(w) >= 2]
        lexical_match = all(w in all_text for w in words) if words else True
        chunk_support = sum(1 for h in hits[:3] if intent.lower() in h["text"].lower())
        
        coverage = score + (0.1 if lexical_match else 0) + (0.05 * min(chunk_support, 2))
        
        print(f"Intent: '{intent}'")
        print(f"  Score: {score:.3f}")
        print(f"  Lexical Match (ALL, len>=2): {lexical_match} (Words: {words})")
        print(f"  Chunk Support: {chunk_support}")
        print(f"  Coverage: {coverage:.3f}")

debug_intent("What does the document say about AI regulation?", "RBI-Monetary-Policy-October-2023.pdf")
debug_intent("Why did the RBI reduce the repo rate to 4%?", "RBI-Monetary-Policy-October-2023.pdf")
debug_intent("Compare inflation, growth, and fiscal policy", "RBI-Monetary-Policy-October-2023.pdf")
debug_intent("Explain inflation risks in detail", "RBI-Monetary-Policy-October-2023.pdf")
