"""
llm/prompt_builder.py
Responsibility: Assemble system prompt and context block from retrieved chunks + metadata.
"""

from typing import List, Dict

SYSTEM_PROMPT = """
You are a highly accurate PDF-grounded conversational agent.
Your goal is to answer the user's question using ONLY the provided context chunks.

RULES:
1. If the answer is not in the context, say: "I'm sorry, but the provided document does not contain information to answer that question."
2. Do not use outside knowledge.
3. Every factual claim must be followed by a citation in the format [Page X].
4. Be concise and professional.
"""

def build_messages(hits: List[Dict], query: str, chat_history: List[Dict] = None) -> List[Dict]:
    """
    Assembles the conversation history and the current context into a message list.
    The context is formatted as a sequence of labeled chunks.
    """
    context_parts = []
    for i, hit in enumerate(hits):
        context_parts.append(f"--- CHUNK {i+1} (Page {hit['page']}, Section {hit['section']}) ---\n{hit['text']}")
    
    context_block = "\n\n".join(context_parts)
    
    # We only send the last N turns of history to stay within token limits
    # The current prompt is already at the end of chat_history
    messages = []
    
    # Optional: Add history here if needed, but for now we focus on context
    # Usually history is kept separate to avoid confusing the context
    
    user_message = f"CONTEXT FROM DOCUMENT:\n{context_block}\n\nUSER QUESTION: {query}"
    
    return [{"role": "user", "content": user_message}]
