import sys
PROJECT_ROOT = r"e:\Stair Digital Assignment\pdf_agent"
sys.path.append(PROJECT_ROOT)
from scratch.audit_suite import AuditSuite

suite = AuditSuite()
history = [
    {"role": "user", "content": "What is the repo rate?"},
    {"role": "assistant", "content": "The repo rate is 6.50% [ID: 1 | Page 1 | Section A]."}
]
q2 = "And how does that affect baking a cake?"
rewrite_result = suite.run_turn(q2, suite.rbi_doc, chat_history=history)

with open("scratch/debug_output.txt", "w") as f:
    f.write(str(rewrite_result))
