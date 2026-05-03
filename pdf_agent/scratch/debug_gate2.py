import sys
PROJECT_ROOT = r"e:\Stair Digital Assignment\pdf_agent"
sys.path.append(PROJECT_ROOT)
from llm.gate2_checker import validate_citations_against_chunks
from llm.response_parser import ParsedResponse, Citation

def debug_gate2():
    parsed = ParsedResponse(
        answer_text="I am not sure about the answer. [ID: chunk_1 | Page 1 | Section Intro]",
        citations=[Citation(chunk_id="chunk_1", page=1, section="Intro")],
        is_valid=True
    )
    hits = [{"chunk_id": "chunk_1", "page": 1, "text": "The repo rate is 6.5%"}]
    
    result = validate_citations_against_chunks(parsed, hits)
    print(f"Gate 2 Result: {result}")

if __name__ == "__main__":
    debug_gate2()
