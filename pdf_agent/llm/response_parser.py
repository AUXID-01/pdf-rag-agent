"""
llm/response_parser.py
Responsibility: Parses, validates, and if possible repairs LLM output.
Enforces citation presence. Detects special signals.
"""

import re
from dataclasses import dataclass

@dataclass
class ParsedResponse:
    status: str          # "answered", "insufficient", "contradicted", "error", "uncited"
    answer: str          # Final answer text shown to user
    has_citations: bool  # True if at least one valid [Page X | Section Y] found
    citation_count: int  # Number of citations found
    raw: str             # Original LLM output for trace/debug

# Pattern requires both page number AND section name
FULL_CITATION_PATTERN = re.compile(r'\[Page \d+ \| Section .+?\]')

# Loose pattern — catches page-only citations like [Page 2]
LOOSE_CITATION_PATTERN = re.compile(r'\[Page \d+\]|\(Page \d+\)')

def parse_response(raw: str) -> ParsedResponse:
    """
    Validates LLM output and returns a structured response object.
    Distinguishes between properly cited, loosely cited, and uncited answers.
    """
    if not raw or not raw.strip():
        return ParsedResponse(
            status="error",
            answer="The model returned an empty response. Please try again.",
            has_citations=False,
            citation_count=0,
            raw=raw or ""
        )

    stripped = raw.strip()

    # Check for special signals first
    if "INSUFFICIENT_CONTEXT" in stripped:
        return ParsedResponse(
            status="insufficient",
            answer="The document does not contain enough information to answer this question.",
            has_citations=False,
            citation_count=0,
            raw=raw
        )

    if "CONTRADICTED_BY_DOCUMENT" in stripped:
        return ParsedResponse(
            status="contradicted",
            answer="The premise of your question appears to contradict what the document states.",
            has_citations=False,
            citation_count=0,
            raw=raw
        )

    # Check for full citations [Page X | Section Y]
    full_citations = FULL_CITATION_PATTERN.findall(stripped)
    
    if full_citations:
        return ParsedResponse(
            status="answered",
            answer=stripped,
            has_citations=True,
            citation_count=len(full_citations),
            raw=raw
        )

    # Check for loose citations [Page X] — answer exists but format is wrong
    loose_citations = LOOSE_CITATION_PATTERN.findall(stripped)
    
    if loose_citations:
        return ParsedResponse(
            status="uncited",
            answer=stripped,
            has_citations=False,
            citation_count=0,
            raw=raw
        )

    # No citations at all
    return ParsedResponse(
        status="uncited",
        answer=stripped,
        has_citations=False,
        citation_count=0,
        raw=raw
    )
