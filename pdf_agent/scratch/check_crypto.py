import sys
PROJECT_ROOT = r"e:\Stair Digital Assignment\pdf_agent"
sys.path.append(PROJECT_ROOT)
from retrieval.hallucination_gate import evaluate
from retrieval.searcher import search_query
from retrieval.reranker import rerank

hits = search_query("crypto stance", "RBI-Monetary-Policy-October-2023.pdf")
gate = evaluate(hits, "What is the repo rate and what is the crypto stance?")
print(gate)
