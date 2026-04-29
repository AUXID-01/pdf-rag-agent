"""
llm/response_parser.py
Responsibility: Parse LLM response string into AnswerObject with citations extracted.
"""

from typing import List, Dict
from logs.schema import AnswerObject, RetrievalHit

from logs.schema import ParsedResponse

def parse_response(raw_text: str, hits: List[Dict] = None) -> ParsedResponse:
    """
    Parses the raw text from the LLM and identifies its status.
    """
    text = raw_text.strip()
    
    # 1. Detect Status
    status = "answered"
    if "does not contain information" in text.lower() or "insufficient" in text.lower():
        status = "insufficient"
    elif "contradict" in text.lower():
        status = "contradicted"
    elif not text:
        status = "error"

    # 2. Extract Citations (simplified)
    has_citations = "[" in text and "]" in text and "Page" in text
    
    return ParsedResponse(
        status=status,
        answer=text,
        has_citations=has_citations,
        citations=hits or []
    )
