import sys
import json
PROJECT_ROOT = r"e:\Stair Digital Assignment\pdf_agent"
sys.path.append(PROJECT_ROOT)
from scratch.audit_suite import AuditSuite

suite = AuditSuite()

output = ""

# Phase 2
history = [
    {"role": "user", "content": "What is the repo rate?"},
    {"role": "assistant", "content": "The repo rate is 6.50% [ID: 1 | Page 1 | Section A]."}
]
q2 = "And how does that affect baking a cake?"
res2 = suite.run_turn(q2, suite.rbi_doc, chat_history=history)
output += f"Phase 2 Answer:\n{res2.get('answer', res2.get('reason'))}\n\n"

# Phase 5
q5 = "Why did the RBI increase the repo rate to 10%?"
res5 = suite.run_turn(q5, suite.rbi_doc)
output += f"Phase 5 Answer:\n{res5.get('answer', res5.get('reason'))}\n\n"

# Phase 3
q3 = "What is the repo rate and how do I bake a chocolate cake?"
res3 = suite.run_turn(q3, suite.rbi_doc)
output += f"Phase 3 Status/Reason: {res3['status']} / {res3.get('reason')}\n"

with open("scratch/failure_details.txt", "w") as f:
    f.write(output)
