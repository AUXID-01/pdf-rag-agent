import sys
import numpy as np
PROJECT_ROOT = r"e:\Stair Digital Assignment\pdf_agent"
sys.path.append(PROJECT_ROOT)
from indexing.embedder import get_model
from retrieval.hallucination_gate import clean_intent

embedder = get_model()
intent = clean_intent("What did the RBI decide regarding the repo rate?")
context_text = "The MPC unanimously voted to keep the repo rate unchanged at 6.50% for the fourth consecutive meeting."
intent_emb = embedder.encode(intent)
context_emb = embedder.encode(context_text)
score = np.dot(intent_emb, context_emb) / (np.linalg.norm(intent_emb) * np.linalg.norm(context_emb))

print(f"Intent: {intent}")
print(f"Score: {score}")
