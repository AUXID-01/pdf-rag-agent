import sys
import os
PROJECT_ROOT = r"e:\Stair Digital Assignment\pdf_agent"
sys.path.append(PROJECT_ROOT)
from retrieval.searcher import search_query

def check_text():
    query = "repo rate and crypto stance"
    doc_id = "RBI-Monetary-Policy-October-2023.pdf"
    hits = search_query(query, doc_id)
    all_text = " ".join([h["text"].lower() for h in hits])
    print(f"Is 'crypto' in text? {'crypto' in all_text}")
    print(f"Is 'stance' in text? {'stance' in all_text}")

if __name__ == "__main__":
    check_text()
