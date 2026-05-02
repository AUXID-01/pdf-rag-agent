import os
import sys
import json
from typing import List, Dict

PROJECT_ROOT = r"e:\Stair Digital Assignment\pdf_agent"
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from retrieval.searcher import search_query
from retrieval.reranker import rerank
from retrieval.hallucination_gate import evaluate, GateResult
from conversation.query_rewriter import rewrite_query
from llm.prompt_builder import build_messages, SYSTEM_PROMPT
from llm.groq_client import call_llm
from llm.response_parser import parse_llm_response
from llm.gate2_checker import validate_citations_against_chunks, post_process_answer

class ForensicAudit:
    def __init__(self):
        self.rbi_doc = "RBI-Monetary-Policy-October-2023.pdf"
        self.results = {}

    def trace_turn(self, query: str, doc_id: str, chat_history: List[Dict] = None) -> Dict:
        """Runs a turn and captures a detailed pipeline trace."""
        if chat_history is None:
            chat_history = []
            
        trace = {"query": query, "steps": {}}
        
        # 1. Rewrite
        rewrite_result = rewrite_query(query, chat_history)
        retrieval_query = rewrite_result["rewritten_query"]
        trace["steps"]["rewrite"] = rewrite_result
        
        # 2. Retrieval & Rerank
        raw_hits = search_query(retrieval_query, doc_id=doc_id, top_k=8)
        hits = rerank(query=retrieval_query, hits=raw_hits, is_followup=rewrite_result["was_rewritten"])
        trace["steps"]["retrieval"] = {"top_score": hits[0]["rerank_score"] if hits else 0, "hit_count": len(hits)}
        
        # 3. Gate 1
        gate1_result: GateResult = evaluate(hits=hits, query=retrieval_query)
        trace["steps"]["gate1"] = {
            "passed": gate1_result.state == "ANSWERABLE",
            "reason": gate1_result.reason,
            "best_similarity": gate1_result.best_similarity
        }
        
        if gate1_result.state != "ANSWERABLE":
            trace["final_status"] = f"REFUSED_GATE1_{gate1_result.reason}"
            return trace
            
        # 4. LLM
        messages = build_messages(query=retrieval_query, hits=gate1_result.hits)
        raw_answer = call_llm(system_prompt=SYSTEM_PROMPT, messages=messages)
        trace["steps"]["llm"] = {"raw_output": raw_answer}
        
        # 5. Parse & Gate 2
        parsed = parse_llm_response(raw_answer)
        trace["steps"]["parse"] = {
            "answer_text": parsed.answer_text,
            "citations": [{"chunk_id": c.chunk_id, "page": c.page} for c in parsed.citations],
            "is_valid": parsed.is_valid
        }
        
        gate2_result = validate_citations_against_chunks(parsed, gate1_result.hits)
        trace["steps"]["gate2"] = gate2_result
        
        if not gate2_result["passed"]:
            trace["final_status"] = "REFUSED_GATE2"
            return trace
            
        # 6. Post-process
        final_answer = post_process_answer(parsed)
        trace["steps"]["post_process"] = final_answer
        trace["final_status"] = "SUCCESS"
        
        return trace

    def phase1_reproducibility(self):
        print("\n--- Phase 1: Failure Reproducibility ---")
        query = "Why did the RBI increase the repo rate to 10%?"
        outcomes = []
        for i in range(5):
            print(f"Run {i+1}...")
            t = self.trace_turn(query, self.rbi_doc)
            outcomes.append(t["final_status"])
        
        failures = outcomes.count("SUCCESS")  # It should REFUSE, so SUCCESS is a failure
        print(f"Reproducibility: {failures}/5 ({failures/5 * 100}%) returned SUCCESS for a false premise.")
        self.results["phase1"] = {"query": query, "outcomes": outcomes, "reproducibility": failures/5}

    def phase2_threshold_sensitivity(self):
        print("\n--- Phase 2: Threshold Sensitivity ---")
        queries = [
            "increase repo rate to 10%",
            "why repo rate 10%",
            "reason for 10% repo rate",
            "repo rate 10 percent explanation"
        ]
        results = {}
        for q in queries:
            t = self.trace_turn(q, self.rbi_doc)
            g1 = t["steps"].get("gate1", {})
            results[q] = {
                "score": g1.get("best_similarity", 0),
                "g1_reason": g1.get("reason", "N/A"),
                "final": t["final_status"]
            }
            print(f"Q: '{q}' -> Score: {results[q]['score']:.3f} | G1: {results[q]['g1_reason']} | Final: {results[q]['final']}")
        self.results["phase2"] = results

    def phase3_false_refusals(self):
        print("\n--- Phase 3: False Refusal Test ---")
        # Valid queries phrased loosely
        queries = [
            "what's up with the inflation target stuff",
            "did they change the rates or keep them same",
            "tell me about the central bank's stance"
        ]
        results = {}
        for q in queries:
            t = self.trace_turn(q, self.rbi_doc)
            results[q] = t["final_status"]
            print(f"Q: '{q}' -> Final: {t['final_status']}")
        self.results["phase3"] = results

    def phase4_pipeline_trace(self):
        print("\n--- Phase 4: Pipeline Trace Validation ---")
        q = "Why did the RBI increase the repo rate to 10%?"
        t = self.trace_turn(q, self.rbi_doc)
        
        print("Trace for 'Invisible Answer' bypass:")
        print(f"1. G1 Score: {t['steps']['gate1']['best_similarity']:.3f} (Passed: {t['steps']['gate1']['passed']})")
        
        if "llm" in t["steps"]:
            raw = t["steps"]["llm"]["raw_output"].replace('\n', ' ')
            print(f"2. LLM Raw: {raw[:100]}...")
            
        if "parse" in t["steps"]:
            print(f"3. Parsed Citations: {t['steps']['parse']['citations']}")
            
        if "gate2" in t["steps"]:
            print(f"4. Gate 2 Passed: {t['steps']['gate2']['passed']} ({t['steps']['gate2']['reason']})")
            
        if "post_process" in t["steps"]:
            print(f"5. Final Answer Text: '{t['steps']['post_process']['answer_text']}'")
            
        self.results["phase4"] = t

    def run_all(self):
        self.phase1_reproducibility()
        self.phase2_threshold_sensitivity()
        self.phase3_false_refusals()
        self.phase4_pipeline_trace()
        
        with open("scratch/forensic_results.json", "w") as f:
            json.dump(self.results, f, indent=2)

if __name__ == "__main__":
    audit = ForensicAudit()
    audit.run_all()
