from conversation.history import get_recent_history, format_history_for_rewriter, is_followup
from llm.groq_client import call_llm
from config import MAX_CHAT_HISTORY
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

def rewrite_query(
    user_query: str,
    chat_history: list,
    max_turns: int = MAX_CHAT_HISTORY
) -> dict:
    """
    Rewrites a follow-up query into a self-contained query.

    Returns a dict with exactly these keys:
        rewritten_query: str   — the rewritten query to use for retrieval
        was_rewritten: bool    — True if rewriting changed the query
        needs_clarification: bool — True if CLARIFICATION_NEEDED was returned
        original_query: str    — the original user input unchanged

    Logic:
    1. Call is_followup(user_query, chat_history).
    2. Call get_recent_history(chat_history, max_turns) to get context.
    3. Call format_history_for_rewriter(recent_history) to get history block.
    4. Build user message for LLM.
    5. Call call_llm.
    6. Strip response and check for CLARIFICATION_NEEDED.
    7. Fallback for empty/error.
    8. Return result.
    """
    # 1. Logic
    if not is_followup(user_query, chat_history):
        return {
            "rewritten_query": user_query,
            "was_rewritten": False,
            "needs_clarification": False,
            "original_query": user_query
        }
    
    # 2. Logic
    recent_history = get_recent_history(chat_history, max_turns)
    if not recent_history:
        return {
            "rewritten_query": user_query,
            "was_rewritten": False,
            "needs_clarification": False,
            "original_query": user_query
        }
        
    # 3. Logic
    history_block = format_history_for_rewriter(recent_history)
    
    # 4. Logic
    user_message = f"""Conversation so far:
{history_block}

Follow-up question: {user_query}

Rewrite the follow-up into a self-contained search query."""

    # 5. Logic
    try:
        # Call call_llm as per instructions. 
        # Note: We pass max_tokens and temperature as requested, 
        # assuming call_llm will be updated or already matches.
        response = call_llm(
            system_prompt=REWRITER_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
            max_tokens=80,
            temperature=0.0
        )
        
        # 6. Logic
        rewritten = response.strip() if response else ""
        if rewritten == "CLARIFICATION_NEEDED":
            return {
                "rewritten_query": user_query,
                "was_rewritten": False,
                "needs_clarification": True,
                "original_query": user_query
            }
            
        # 7. Logic
        if not rewritten:
            log.warning("query_rewriter_empty_response", query=user_query)
            return {
                "rewritten_query": user_query,
                "was_rewritten": False,
                "needs_clarification": False,
                "original_query": user_query
            }
            
        # 8. Logic
        return {
            "rewritten_query": rewritten,
            "was_rewritten": True,
            "needs_clarification": False,
            "original_query": user_query
        }

    except Exception as e:
        log.warning("query_rewriter_failed", error=str(e), query=user_query)
        return {
            "rewritten_query": user_query,
            "was_rewritten": False,
            "needs_clarification": False,
            "original_query": user_query
        }
