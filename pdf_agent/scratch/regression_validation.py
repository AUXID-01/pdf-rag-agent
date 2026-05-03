import os
import sys
import json
from typing import List, Dict

PROJECT_ROOT = r"e:\Stair Digital Assignment\pdf_agent"
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from scratch.second_pass_audit import ForensicAudit

def run_regression_validation():
    audit = ForensicAudit()
    rbi_doc = "RBI-Monetary-Policy-October-2023.pdf"
    results = {}

    print("\n--- Test 1: What is inflation? (Valid Query) ---")
    t1 = audit.trace_turn("What is inflation?", rbi_doc)
    results["Test1"] = {"status": t1["final_status"], "expected": "SUCCESS"}
    print(f"Result: {t1['final_status']}")

    print("\n--- Test 2: Explain inflation risks in detail (Partial Allowed) ---")
    t2 = audit.trace_turn("Explain inflation risks in detail", rbi_doc)
    # Should be SUCCESS because 'in detail' is secondary
    results["Test2"] = {"status": t2["final_status"], "expected": "SUCCESS"}
    print(f"Result: {t2['final_status']}")

    print("\n--- Test 3: Repo Rate and Crypto Stance (Strict Refusal) ---")
    t3 = audit.trace_turn("What is the repo rate and what is the crypto stance?", rbi_doc)
    # Should be REFUSED_GATE1 because 'crypto' is not explanatory
    results["Test3"] = {"status": t3["final_status"], "expected": "REFUSED_GATE1_Significant parts of the query are missing from the context."}
    print(f"Result: {t3['final_status']}")

    print("\n--- Test 4: Force LLM Weak Answer (Gate 2 Block) ---")
    # Mocking LLM to return a weak answer
    from unittest.mock import patch
    # Patching the reference used in second_pass_audit
    with patch('scratch.second_pass_audit.call_llm') as mock_llm:
        mock_llm.return_value = "I am not sure about the answer. [ID: chunk_1 | Page 1 | Section Intro]\n\nCITATIONS:\n- ID: chunk_1 | Page 1 | Section Intro"
        t4 = audit.trace_turn("What is the repo rate?", rbi_doc)
        # Should be REFUSED_GATE2
        results["Test4"] = {"status": t4["final_status"], "expected": "REFUSED_GATE2"}
        print(f"Result: {t4['final_status']}")

    with open("scratch/regression_results.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    run_regression_validation()
