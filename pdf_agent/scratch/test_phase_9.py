from llm.response_parser import parse_llm_response
from llm.gate2_checker import validate_citations_against_chunks

raw_llm_response = """The repo rate was held at 6.5%.

CITATIONS:
- Page 1 | Section Overview
- Page 2 | Section Details"""

print("Testing parse_llm_response...")
parsed = parse_llm_response(raw_llm_response)
print(f"Is valid? {parsed.is_valid}")
print(f"Answer text: {parsed.answer_text}")
print("Citations:")
for c in parsed.citations:
    print(f"  - Page {c.page}, Section {c.section}")

chunks = [
    {"page": 1, "section": "Overview"},
    {"page_start": 3, "section": "Conclusion"}
]

print("\nTesting validate_citations_against_chunks (Expected failure because Page 2 is missing)...")
result_fail = validate_citations_against_chunks(parsed, chunks)
print(f"Passed? {result_fail['passed']}")
print(f"Reason: {result_fail['reason']}")

chunks_pass = [
    {"page": 1, "section": "Overview"},
    {"page": 2, "section": "Details"}
]

print("\nTesting validate_citations_against_chunks (Expected success)...")
result_pass = validate_citations_against_chunks(parsed, chunks_pass)
print(f"Passed? {result_pass['passed']}")
print(f"Reason: {result_pass['reason']}")
