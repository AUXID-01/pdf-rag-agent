import sys
import os
import json

# Add project root to path
sys.path.append(os.getcwd())

from retrieval.searcher import search_query
from retrieval.reranker import rerank
from retrieval.hallucination_gate import evaluate

def run_eval(name, query, doc_id="finance.pdf"):
    print(f"\n--- TEST: {name} ---")
    print(f"Query: {query}")
    
    hits = search_query(query, doc_id=doc_id, top_k=5)
    hits = rerank(query, hits)
    gate = evaluate(hits, query)
    
    if not gate.passed:
        print(f"RESULT: REFUSED")
        print(f"Reason: {gate.reason}")
        print(f"Structured Details:\n{gate.message}")
    else:
        print(f"RESULT: PASS")

# Test 1: Mixed Intent (Supported + French Capital)
run_eval("Test 1: Mixed Intent (Supported + French Capital)", "What is the repo rate and what is the capital of France?")

# Test 2: Mixed Intent (Supported + Crypto)
run_eval("Test 2: Mixed Intent (Repo Rate + Crypto)", "What is the repo rate and what is the RBI stance on cryptocurrency?")

# Test 3: Fully Supported (Single)
run_eval("Test 3: Fully Supported (Single)", "What is the inflation forecast?")

# Test 4: Fully Unsupported (Single)
run_eval("Test 4: Fully Unsupported (Single)", "What is the capital of France?")

# Test 5: Fully Supported (Multi)
run_eval("Test 5: Fully Supported (Multi)", "What is inflation and GDP growth?")
