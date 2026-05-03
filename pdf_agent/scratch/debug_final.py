import sys
import os
PROJECT_ROOT = r"e:\Stair Digital Assignment\pdf_agent"
sys.path.append(PROJECT_ROOT)
from retrieval.hallucination_gate import evaluate
from retrieval.searcher import search_query

def debug_final():
    query = "repo rate and crypto stance"
    doc_id = "RBI-Monetary-Policy-October-2023.pdf"
    hits = search_query(query, doc_id)
    gate = evaluate(hits, query)
    print(f"Query: {query}")
    print(f"State: {gate.state}")
    print(f"Reason: {gate.reason}")

if __name__ == "__main__":
    debug_final()
