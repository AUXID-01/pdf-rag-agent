import os
import sys
import json
from typing import List, Dict

PROJECT_ROOT = r"e:\Stair Digital Assignment\pdf_agent"
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from scratch.second_pass_audit import ForensicAudit

def run_final_tests():
    audit = ForensicAudit()
    rbi_doc = "RBI-Monetary-Policy-October-2023.pdf"
    results = {}

    print("\n--- Test 1: Multi-Intent Refusal ---")
    t1 = audit.trace_turn("What is the repo rate and what is the crypto stance?", rbi_doc)
    results["Test1"] = {"status": t1["final_status"], "gate1": t1["steps"]["gate1"]}
    print(f"Result: {t1['final_status']} | G1 Reason: {t1['steps']['gate1']['reason']}")

    print("\n--- Test 2: False Premise ---")
    t2 = audit.trace_turn("Why is the repo rate 10%?", rbi_doc)
    results["Test2"] = {"status": t2["final_status"], "gate1": t2["steps"]["gate1"]}
    print(f"Result: {t2['final_status']} | G1 Reason: {t2['steps']['gate1']['reason']}")

    print("\n--- Test 3: Valid Query ---")
    t3 = audit.trace_turn("What did the RBI decide regarding the repo rate?", rbi_doc)
    results["Test3"] = {"status": t3["final_status"], "gate1": t3["steps"]["gate1"]}
    if "post_process" in t3["steps"]:
        print(f"Answer Text: {t3['steps']['post_process']['answer_text'][:50]}...")
        print(f"Citations: {len(t3['steps']['post_process']['citations'])}")
    else:
        print("Failed to reach post_process")

    print("\n--- Test 4: Force LLM Weak Answer ---")
    # To force a weak answer, we can pass a query that passes Gate 1 but then we mock the LLM
    # Actually, I'll just write a custom script using the gate2 functions directly
    from llm.response_parser import ParsedResponse, Citation
    from llm.gate2_checker import validate_citations_against_chunks
    
    mock_parsed = ParsedResponse(
        answer_text="I don't know the answer because it is not fully supported.",
        citations=[Citation(chunk_id="fake_chunk", page=1, section="General")],
        is_valid=True
    )
    res = validate_citations_against_chunks(mock_parsed, [{"chunk_id": "fake_chunk", "page": 1, "text": "Something completely unrelated to repo rates."}])
    results["Test4"] = res
    print(f"Gate 2 Check: {res}")

    with open("scratch/final_validation.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    run_final_tests()
