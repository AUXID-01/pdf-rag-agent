def get_recent_history(chat_history: list, max_turns: int) -> list:
    """
    Returns the last `max_turns` assistant+user pairs from chat_history.
    Each entry is a dict with keys: role, content.
    Ignore entries where role is not 'user' or 'assistant'.
    Ignore entries where content is empty or starts with '[Response blocked'.
    Returns a flat list ordered oldest to newest.
    """
    valid_msgs = []
    for msg in chat_history:
        role = msg.get("role")
        content = msg.get("content", "")
        if role not in ["user", "assistant"]:
            continue
        if not content or content.startswith("[Response blocked"):
            continue
        valid_msgs.append({"role": role, "content": content})
    
    return valid_msgs[-(max_turns * 2):]

def format_history_for_rewriter(recent_history: list) -> str:
    """
    Converts the recent history list into a plain text block for the
    rewriter prompt.
    Format each turn as:
        User: <content>
        Assistant: <content>
    Separate turns with a single blank line.
    Return the full block as a single string.
    If recent_history is empty, return an empty string.
    """
    if not recent_history:
        return ""
    
    formatted_turns = []
    current_turn = []
    for msg in recent_history:
        role = msg["role"].capitalize()
        content = msg["content"]
        current_turn.append(f"{role}: {content}")
        if role == "Assistant":
            formatted_turns.append("\n".join(current_turn))
            current_turn = []
    
    if current_turn:
        formatted_turns.append("\n".join(current_turn))
        
    return "\n\n".join(formatted_turns)

def is_followup(user_query: str, chat_history: list = []) -> bool:
    """
    Returns True if the query is likely a follow-up that needs rewriting.
    A query is a follow-up if it contains any of these signals:
        - Pronouns: it, its, they, them, their, this, that, there, those, these
        - Shorthand: that section, that part, the same, the above, the previous
        - Continuation phrases: what about, tell me more, explain further,
          summarize it, what are the risks there, what does it say, go on,
          and what, but what
    Match case-insensitively.
    Return False if the query is longer than 120 characters
    (long queries are self-contained).
    Return False if the chat_history passed in is empty.
    Accept chat_history as a second argument with default [].
    """
    if not chat_history:
        return False
    
    if len(user_query) > 120:
        return False
        
    import re
    query_lower = user_query.lower()
    
    signals = [
        "it", "its", "they", "them", "their", "this", "that", "there", "those", "these",
        "that section", "that part", "the same", "the above", "the previous",
        "what about", "tell me more", "explain further", "summarize it",
        "what are the risks there", "what does it say", "go on", "and what", "but what"
    ]
    
    for signal in signals:
        # Using word boundaries for shorter signals, but literal for phrases
        if " " in signal:
            if signal in query_lower:
                return True
        else:
            if re.search(r'\b' + re.escape(signal) + r'\b', query_lower):
                return True
            
    return False
