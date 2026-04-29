import os
import sys
from dotenv import load_dotenv

# Add current dir to path
sys.path.append(os.getcwd())

from config import SCATTER_THRESHOLD
from conversation.query_rewriter import rewrite_query, needs_rewriting
from llm.prompt_builder import SYSTEM_PROMPT
from llm.response_parser import parse_response

def test_scatter_threshold():
    print(f"Testing Scatter Threshold: {SCATTER_THRESHOLD}")
    assert SCATTER_THRESHOLD == 0.70
    print("DONE: Scatter Threshold correct")

def test_query_rewriter():
    print("Testing Query Rewriter...")
    
    # Test case 1: Needs rewriting
    q1 = "what about that?"
    history = [
        {"role": "user", "content": "What is the repo rate?"},
        {"role": "assistant", "content": "The repo rate is 6.5%."}
    ]
    assert needs_rewriting(q1) == True
    print(f"Needs rewriting 'what about that?': {needs_rewriting(q1)}")
    
    # Test case 2: Long query, doesn't need rewriting
    q2 = "Explain the regulatory measures for payment systems in detail please."
    assert needs_rewriting(q2) == False
    print(f"Needs rewriting long query: {needs_rewriting(q2)}")

    # We won't call the LLM here to avoid consuming credits/tokens and needing API key in this script
    # but the logic checks out.
    print("DONE: Query Rewriter logic correct")

def test_citation_enforcement():
    print("Testing Citation Enforcement...")
    
    # Correct format
    raw1 = "The rate is 6.5% [Page 1 | Section Intro]."
    p1 = parse_response(raw1)
    assert p1.status == "answered"
    assert p1.has_citations == True
    assert p1.citation_count == 1
    
    # Loose format (wrong)
    raw2 = "The rate is 6.5% [Page 1]."
    p2 = parse_response(raw2)
    assert p2.status == "uncited"
    assert p2.has_citations == False
    
    # INSUFFICIENT_CONTEXT
    raw3 = "INSUFFICIENT_CONTEXT"
    p3 = parse_response(raw3)
    assert p3.status == "insufficient"
    
    # CONTRADICTED_BY_DOCUMENT
    raw4 = "CONTRADICTED_BY_DOCUMENT"
    p4 = parse_response(raw4)
    assert p4.status == "contradicted"

    print("DONE: Citation Parser logic correct")

if __name__ == "__main__":
    try:
        test_scatter_threshold()
        test_query_rewriter()
        test_citation_enforcement()
        print("\nALL LOGIC CHECKS PASSED!")
    except Exception as e:
        print(f"\nFAILED: {e}")
        sys.exit(1)
