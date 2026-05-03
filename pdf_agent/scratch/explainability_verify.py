import os
import sys
import json
from typing import List, Dict

PROJECT_ROOT = r"e:\Stair Digital Assignment\pdf_agent"
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from logs.trace import build_trace
from retrieval.hallucination_gate import GateResult

def test_explainability():
    # Mock data for "List them"
    query_1 = "List them"
    rewrite_result_1 = {
        "rewritten_query": "List the inflation risks mentioned in the document",
        "was_rewritten": True,
        "needs_clarification": False,
        "original_query": query_1
    }
    hits_1 = [{"rerank_score": 0.7, "page": 1, "section": "Inflation", "preview": "..."}]
    gate_result_1 = GateResult(
        state="ANSWERABLE",
        reason="Inflation risks are found.",
        message=json.dumps({"supported_parts": ["inflation risks"], "missing_parts": []}),
        hits=hits_1,
        best_similarity=0.7,
        nearest_topic="Inflation"
    )
    
    trace_1 = build_trace(
        query=query_1,
        rewrite_result=rewrite_result_1,
        hits=hits_1,
        gate_result=gate_result_1,
        response_type="answer",
        citations=[(1, "Inflation")]
    )
    
    print("\n--- Test 1: 'List them' ---")
    exp_1 = trace_1["explainability"]
    print(f"Query Type: {exp_1['query_analysis']['type']} (Expected: REFERENCE)")
    print(f"Rewrite Applied: {exp_1['rewrite']['applied']} (Expected: True)")
    print(f"Decision: {exp_1['decision_engine']['state']} (Expected: ANSWERABLE)")
    print(f"LLM Called: {exp_1['generation']['llm_called']} (Expected: True)")

    # Mock data for "Explain crypto"
    query_2 = "Explain crypto"
    rewrite_result_2 = {
        "rewritten_query": "Explain crypto",
        "was_rewritten": False,
        "needs_clarification": False,
        "original_query": query_2
    }
    hits_2 = [{"rerank_score": 0.1, "page": 1, "section": "Intro", "preview": "..."}]
    gate_result_2 = GateResult(
        state="OUT_OF_SCOPE",
        reason="Crypto is not mentioned in the RBI document.",
        message=json.dumps({"supported_parts": [], "missing_parts": ["crypto"]}),
        hits=hits_2,
        best_similarity=0.1,
        nearest_topic="None"
    )
    
    trace_2 = build_trace(
        query=query_2,
        rewrite_result=rewrite_result_2,
        hits=hits_2,
        gate_result=gate_result_2,
        response_type="refusal",
        citations=[]
    )
    
    print("\n--- Test 2: 'Explain crypto' ---")
    exp_2 = trace_2["explainability"]
    print(f"Query Type: {exp_2['query_analysis']['type']} (Expected: SHIFT)")
    print(f"Decision: {exp_2['decision_engine']['state']} (Expected: OUT_OF_SCOPE)")
    print(f"LLM Called: {exp_2['generation']['llm_called']} (Expected: False)")

if __name__ == "__main__":
    test_explainability()
