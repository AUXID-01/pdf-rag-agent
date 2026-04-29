"""
conversation/query_rewriter.py
Responsibility: Rewrites vague or pronoun-heavy follow-up queries into
self-contained queries using conversation history and a Groq LLM call.
Only activates when the query is short AND contains reference triggers.
Does not run on every turn — only when needed.
"""

import os
from dotenv import load_dotenv
from groq import Groq
from typing import List, Dict, Optional
from config import LLM_MODEL
from logs.logger import get_logger

load_dotenv()
log = get_logger("conversation.query_rewriter")

REFERENCE_TRIGGERS = [
    "that", "it", "this", "there", "they", "those",
    "the announcement", "the decision", "the measure",
    "the policy", "the rate", "the report", "the section",
    "what about", "elaborate", "explain more", "tell me more",
    "why", "how so", "and then", "what happened", "what was"
]

REWRITER_SYSTEM_PROMPT = """You are a query rewriting assistant for a document Q&A system.

Your job: Given a conversation history and a vague follow-up question, rewrite the question into a fully self-contained search query that can be understood without any prior context.

Rules:
1. Output ONLY the rewritten query. No explanation. No preamble.
2. Preserve the original intent exactly.
3. Replace all pronouns and vague references with specific terms from the conversation.
4. Keep the rewritten query concise — one sentence maximum.
5. If the query is already self-contained, return it unchanged.
"""

def needs_rewriting(query: str) -> bool:
    """
    Returns True if the query is short and contains reference triggers
    that suggest it depends on prior context.
    """
    query_lower = query.lower().strip()
    word_count = len(query_lower.split())
    
    if word_count > 12:
        return False
    
    return any(trigger in query_lower for trigger in REFERENCE_TRIGGERS)

def build_history_summary(chat_history: List[Dict], max_turns: int = 3) -> str:
    """
    Extracts the last N assistant+user turns from chat history
    and formats them as a readable conversation summary.
    """
    relevant = []
    turns_collected = 0
    
    for msg in reversed(chat_history):
        if turns_collected >= max_turns:
            break
        if msg["role"] in ("user", "assistant") and msg.get("content", "").strip():
            relevant.append(f"{msg['role'].upper()}: {msg['content'][:300]}")
            if msg["role"] == "user":
                turns_collected += 1
    
    if not relevant:
        return ""
    
    return "\n".join(reversed(relevant))

def rewrite_query(query: str, chat_history: List[Dict]) -> str:
    """
    Main entry point. Rewrites the query if needed using Groq.
    Returns original query unchanged if rewriting is not needed
    or if the LLM call fails.
    
    Args:
        query: The raw user query from the current turn.
        chat_history: Full session chat history list.
        
    Returns:
        Rewritten self-contained query string.
    """
    if not needs_rewriting(query):
        log.info("query_rewrite_skipped", reason="not_needed", query=query)
        return query
    
    history_summary = build_history_summary(chat_history)
    
    if not history_summary:
        log.info("query_rewrite_skipped", reason="no_history", query=query)
        return query
    
    try:
        log.info("query_rewrite_start", query=query)
        
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY not found")
        
        client = Groq(api_key=api_key)
        
        user_message = f"""Conversation so far:
{history_summary}

Follow-up question to rewrite:
{query}

Rewrite this follow-up into a fully self-contained search query:"""

        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": REWRITER_SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0,
            max_tokens=120
        )
        
        rewritten = response.choices[0].message.content.strip()
        log.info("query_rewrite_complete", original=query, rewritten=rewritten)
        return rewritten
        
    except Exception as e:
        log.warning("query_rewrite_failed", error=str(e), query=query)
        return query
