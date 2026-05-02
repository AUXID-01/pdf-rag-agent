"""
llm/prompt_builder.py
Responsibility: Assemble system prompt and context block from retrieved chunks + metadata.
"""

from typing import List, Dict

SYSTEM_PROMPT = """You are a precise document assistant. You answer questions strictly and only from the context chunks provided to you.

ABSOLUTE RULES — violating any of these is not permitted:

1. Answer ONLY from the provided context chunks. If the answer is not fully supported by the provided context, do not generate an answer.

2. CITATION FORMAT IS MANDATORY. Every factual claim must end with a citation in this EXACT format:
   [ID: <chunk_id> | Page X | Section Y]
   
   CRITICAL: Do NOT invent Page numbers. Use the EXACT Page number and ID provided in the chunk header.
   If a chunk header says "Page 2", your citation MUST say "Page 2".
   
   CORRECT examples:
   - The repo rate was held at 6.5% [ID: rbi_p1_c0 | Page 1 | Section Inflation].
   
3. NO DUPLICATE INFORMATION. If multiple chunks provide the same fact, state it ONCE and cite the best chunk.

5. You MUST end every response with a CITATIONS block in exactly this format:

CITATIONS:
- ID: <chunk_id> | Page <number> | Section <section_title>

Rules:
- Do not invent chunk_ids, page numbers or section titles.
- Use only the values provided in the context chunks below.
"""

def build_messages(hits: List[Dict], query: str, chat_history: List[Dict] = None) -> List[Dict]:
    """
    Assembles the conversation history and the current context into a message list.
    The context is formatted as a sequence of labeled chunks.
    """
    context_parts = []
    for i, hit in enumerate(hits):
        context_parts.append(f"--- CHUNK {i+1} (ID: {hit['chunk_id']}, Page {hit['page']}, Section {hit['section']}) ---\n{hit['text']}")
    
    context_block = "\n\n".join(context_parts)
    
    # We only send the last N turns of history to stay within token limits
    # The current prompt is already at the end of chat_history
    messages = []
    
    # Optional: Add history here if needed, but for now we focus on context
    # Usually history is kept separate to avoid confusing the context
    
    user_message = f"CONTEXT FROM DOCUMENT:\n{context_block}\n\nUSER QUESTION: {query}"
    
    return [{"role": "user", "content": user_message}]
