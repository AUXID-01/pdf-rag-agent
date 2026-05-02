import os
import sys

PROJECT_ROOT = r"e:\Stair Digital Assignment\pdf_agent"
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from retrieval.searcher import search_query
from config import RERANKER_THRESHOLD

doc_id = "RBI-Monetary-Policy-October-2023.pdf"
query = "What is the repo rate?"

print(f"Testing retrieval for doc: {doc_id} with query: '{query}'")
hits = search_query(query, doc_id=doc_id, top_k=5)

print(f"Found {len(hits)} hits.")
for i, hit in enumerate(hits):
    print(f"Hit {i+1}:")
    print(f"  Distance: {hit['distance']}")
    print(f"  Page: {hit['page']}")
    print(f"  Preview: {hit['preview']}")
    print("-" * 20)

print(f"Threshold is: {RERANKER_THRESHOLD}")
