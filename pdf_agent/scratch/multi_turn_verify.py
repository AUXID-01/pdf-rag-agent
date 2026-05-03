import os
import sys
import json
from typing import List, Dict

PROJECT_ROOT = r"e:\Stair Digital Assignment\pdf_agent"
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from conversation.query_rewriter import rewrite_query

def test_multi_turn():
    # Test A1: What are the risks?
    history_a1 = [
        {"role": "user", "content": "What is inflation?"},
        {"role": "assistant", "content": "Inflation is the rate at which the general level of prices for goods and services is rising."}
    ]
    res_a1 = rewrite_query("What are the risks?", history_a1)
    print("\n--- Test A1: 'What are the risks?' ---")
    print(f"Type: {res_a1.get('q_type')}")
    print(f"Rewritten: {res_a1['rewritten_query']}")
    print(f"Reuse Context: {res_a1.get('reuse_context')}")

    # Test B1: Explain crypto
    res_b1 = rewrite_query("Explain crypto", history_a1)
    print("\n--- Test B1: 'Explain crypto' ---")
    print(f"Type: {res_b1.get('q_type')}")
    print(f"Reuse Context: {res_b1.get('reuse_context')}")

    # Test B3: How does it affect Bitcoin?
    res_b3 = rewrite_query("How does it affect Bitcoin?", history_a1)
    print("\n--- Test B3: 'How does it affect Bitcoin?' ---")
    print(f"Type: {res_b3.get('q_type')}")
    print(f"Reuse Context: {res_b3.get('reuse_context')}")

    # Test C2: Why?
    res_c2 = rewrite_query("Why?", history_a1)
    print("\n--- Test C2: 'Why?' ---")
    print(f"Type: {res_c2.get('q_type')}")
    print(f"Rewritten: {res_c2['rewritten_query']}")
    print(f"Reuse Context: {res_c2.get('reuse_context')}")

if __name__ == "__main__":
    test_multi_turn()
