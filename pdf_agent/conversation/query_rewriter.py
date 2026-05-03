from conversation.history import get_recent_history, format_history_for_rewriter, is_followup
from llm.groq_client import call_llm
from config import MAX_CHAT_HISTORY
import re
from logs.logger import get_logger

log = get_logger("conversation.query_rewriter")

REWRITER_SYSTEM_PROMPT = """
You are a query rewriting assistant for a document Q&A system.
You will be given a conversation history and a follow-up question.
Your job is to rewrite the follow-up into a fully self-contained search query
that can be understood without the conversation history.

Rules:
- Resolve all pronouns and references using the history.
- Keep the rewritten query concise — one sentence, under 30 words.
- Do not answer the question. Only rewrite it.
- If the follow-up is already self-contained, return it unchanged.
- If the reference is completely ambiguous and cannot be resolved even
  with the history, return exactly this string and nothing else:
  CLARIFICATION_NEEDED
- Never add explanation, preamble, or apology. Return only the rewritten
  query or CLARIFICATION_NEEDED.
"""

def classify_query(query: str, chat_history: list) -> str:
    """
    Classifies the query into REFERENCE, CONTINUATION, SHIFT, or AMBIGUOUS.
    """
    query_lower = query.lower().strip()
    
    # 1. SHIFT Detection (Step 3)
    # If query contains tokens that are radically different from previous context
    out_of_domain = ["crypto", "bitcoin", "france", "ethereum", "blockchain"]
    if any(token in query_lower for token in out_of_domain):
        return "SHIFT"
        
    # 2. "WHY" Handling (Step 4)
    if query_lower == "why" or query_lower.startswith("why "):
        if chat_history and len(chat_history) > 1:
            return "CONTINUATION"
        return "AMBIGUOUS"

    # 3. REFERENCE Detection
    pronouns = ["it", "they", "them", "that", "those", "these", "this"]
    if any(re.search(r'\b' + p + r'\b', query_lower) for p in pronouns):
        return "REFERENCE"
        
    # Dependency check for short "the" queries
    if chat_history and (query_lower.startswith("what are the ") or query_lower.startswith("explain the ")):
        return "REFERENCE"
        
    # 4. CONTINUATION Detection
    continuation_phrases = ["why", "how", "explain more", "detail", "tell me more", "summarize"]
    if any(phrase in query_lower for phrase in continuation_phrases):
        return "CONTINUATION"

    # 5. Default follow-up check
    if not is_followup(query, chat_history):
        return "SHIFT"
        
    # 6. AMBIGUOUS fallback
    if len(query_lower.split()) < 3 and not chat_history:
        return "AMBIGUOUS"
        
    return "REFERENCE" # Default for follow-ups

def rewrite_query(
    user_query: str,
    chat_history: list,
    max_turns: int = MAX_CHAT_HISTORY
) -> dict:
    """
    Rewrites a follow-up query into a self-contained query with multi-turn intelligence.
    """
    # Step 1: Classify
    q_type = classify_query(user_query, chat_history)
    
    # Step 5: Context Reuse Control
    reuse_context = q_type in ["REFERENCE", "CONTINUATION"]
    
    # Step 2: Rewrite Rules
    if q_type == "SHIFT":
        return {
            "rewritten_query": user_query,
            "was_rewritten": False,
            "needs_clarification": False,
            "original_query": user_query,
            "q_type": "SHIFT",
            "reuse_context": False
        }
        
    if q_type == "AMBIGUOUS":
        return {
            "rewritten_query": user_query,
            "was_rewritten": False,
            "needs_clarification": True,
            "original_query": user_query,
            "q_type": "AMBIGUOUS",
            "reuse_context": False
        }

    # For REFERENCE and CONTINUATION, use LLM to rewrite
    recent_history = get_recent_history(chat_history, max_turns)
    if not recent_history:
        return {
            "rewritten_query": user_query,
            "was_rewritten": False,
            "needs_clarification": False,
            "original_query": user_query,
            "q_type": "SHIFT",
            "reuse_context": False
        }
        
    history_block = format_history_for_rewriter(recent_history)
    
    # Specialized prompt instructions based on type
    type_instruction = ""
    if q_type == "REFERENCE":
        type_instruction = "Inject the specific entity or topic being referred to (e.g. 'them' -> 'inflation risks')."
    elif q_type == "CONTINUATION":
        type_instruction = "Expand the query to include the context of the previous answer (e.g. 'Why?' -> 'Why is policy stance withdrawal of accommodation?')."

    user_message = f"""Conversation so far:
{history_block}

Follow-up question: {user_query}

Rewrite the follow-up into a self-contained search query. 
Instruction: {type_instruction}"""

    try:
        response = call_llm(
            system_prompt=REWRITER_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
            max_tokens=80,
            temperature=0.0
        )
        
        rewritten = response.strip() if response else ""
        if rewritten == "CLARIFICATION_NEEDED":
            return {
                "rewritten_query": user_query,
                "was_rewritten": False,
                "needs_clarification": True,
                "original_query": user_query,
                "q_type": "AMBIGUOUS",
                "reuse_context": False
            }
            
        if not rewritten:
            return {
                "rewritten_query": user_query,
                "was_rewritten": False,
                "needs_clarification": False,
                "original_query": user_query,
                "q_type": q_type,
                "reuse_context": reuse_context
            }
            
        return {
            "rewritten_query": rewritten,
            "was_rewritten": True,
            "needs_clarification": False,
            "original_query": user_query,
            "q_type": q_type,
            "reuse_context": reuse_context
        }

    except Exception as e:
        log.warning("query_rewriter_failed", error=str(e), query=user_query)
        return {
            "rewritten_query": user_query,
            "was_rewritten": False,
            "needs_clarification": False,
            "original_query": user_query,
            "q_type": q_type,
            "reuse_context": reuse_context
        }
