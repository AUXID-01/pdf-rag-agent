import sys
import numpy as np
PROJECT_ROOT = r"e:\Stair Digital Assignment\pdf_agent"
sys.path.append(PROJECT_ROOT)
from indexing.embedder import get_model

embedder = get_model()
intent = "crypto stance"
context_text = "policy stance hawkish stance repo rate unchanged"
intent_emb = embedder.encode(intent)
context_emb = embedder.encode(context_text)
score = np.dot(intent_emb, context_emb) / (np.linalg.norm(intent_emb) * np.linalg.norm(context_emb))

print(f"Score: {score}")

significant_words = [w for w in intent.lower().split() if len(w) > 3]
lexical_match = any(w in context_text.lower() for w in significant_words) if significant_words else True
print(f"Lexical Match: {lexical_match}")
