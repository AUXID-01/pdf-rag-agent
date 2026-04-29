import os
import sys
sys.path.append(os.getcwd())

from retrieval.searcher import search_query
from retrieval.reranker import rerank
from retrieval.hallucination_gate import evaluate

def inspect_repo_rate():
    query = "What is the repo rate decided in the October 2023 MPC meeting?"
    doc_id = "RBI-Monetary-Policy-October-2023.pdf"
    
    print(f"Retrieving for: {query}")
    hits = search_query(query=query, doc_id=doc_id, top_k=20)
    hits = rerank(query=query, hits=hits)
    
    if not hits:
        print("No hits found!")
        return

    scores = [h.get("rerank_score", 0) for h in hits]
    print(f"Rerank scores: {scores}")
    
    result = evaluate(hits, query)
    print(f"Gate decision: {result.reason} | best_sim: {result.best_similarity}")
    print(f"Passed: {result.passed}")
    if not result.passed:
        print(f"Message: {result.message}")

if __name__ == "__main__":
    inspect_repo_rate()
