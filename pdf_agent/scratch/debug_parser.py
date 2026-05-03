import sys
PROJECT_ROOT = r"e:\Stair Digital Assignment\pdf_agent"
sys.path.append(PROJECT_ROOT)
from llm.response_parser import parse_llm_response

raw = "I am not sure about the answer. [ID: chunk_1 | Page 1 | Section Intro]\n\nCITATIONS:\n- ID: chunk_1 | Page 1 | Section Intro"
parsed = parse_llm_response(raw)

print(f"Answer: '{parsed.answer_text}'")
print(f"Citations: {parsed.citations}")
print(f"Is Valid: {parsed.is_valid}")

refusal_phrases = ["not sure"]
print(f"Refusal Detected: {any(p in parsed.answer_text.lower() for p in refusal_phrases)}")
