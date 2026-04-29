from typing import List
import difflib
from llm.response_parser import ParsedResponse, Citation

def validate_citations_against_chunks(
    parsed: ParsedResponse,
    retrieved_chunks: List[dict]  # each dict must have 'page' and 'section' keys
) -> dict:
    """
    Validates that:
    1. Answer is not empty
    2. At least one citation exists
    3. Each cited page exists in retrieved chunks (within ±1 page tolerance)

    Returns a result dict with 'passed' bool and 'reason' string.
    """

    if not parsed.answer_text:
        return {"passed": False, "reason": "Answer body is empty."}

    if not parsed.citations:
        return {"passed": False, "reason": "No citations found in response."}

    retrieved = []
    for chunk in retrieved_chunks:
        page = chunk.get("page") or chunk.get("page_start")
        section = chunk.get("section_title") or chunk.get("section") or ""
        if page:
            retrieved.append({"page": int(page), "section": section.lower()})

    retrieved_pages = {r["page"] for r in retrieved}
    retrieved_sections = [r["section"] for r in retrieved]

    unverified = []
    for citation in parsed.citations:
        neighbours = {citation.page - 1, citation.page, citation.page + 1}

        if not neighbours.intersection(retrieved_pages):
            unverified.append(f"Page {citation.page} not in retrieved chunks")
            continue

        matches = difflib.get_close_matches(
            citation.section.lower(),
            retrieved_sections,
            n=1,
            cutoff=0.35
        )
        if not matches:
            unverified.append(
                f"Section '{citation.section}' not grounded in retrieved chunks"
            )

    if unverified:
        return {
            "passed": False,
            "reason": f"Citations not grounded in retrieved chunks: {unverified}"
        }

    return {"passed": True, "reason": "All citations verified."}
