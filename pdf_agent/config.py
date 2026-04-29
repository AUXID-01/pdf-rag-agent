CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
TOP_K = 10
SIMILARITY_THRESHOLD = 0.28
SCATTER_THRESHOLD = 0.15
MAX_CHAT_HISTORY = 10
CHROMA_PERSIST_DIR = "data/chroma_db"
CHROMA_COLLECTION_NAME = "pdf_agent_collection"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
LLM_MODEL = "llama-3.3-70b-versatile"
LLM_MAX_TOKENS = 1024
CITATION_FORMAT = "Page {page} | Section {section}"
LOG_LEVEL = "DEBUG"
LOG_FILE = "data/logs/agent.jsonl"
UPLOAD_DIR = "data/uploads"

# Reranker
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
RERANKER_TOP_K = 5
RERANKER_THRESHOLD = 0.20

# Session State Keys
SESSION_KEYS = {
    "uploaded_doc": None,
    "indexed": False,
    "doc_id": None,
    "chat_history": [],
    "trace_log": [],
    "last_retrievals": [],
    "current_turn_id": None,
    "chunk_count": 0,
    "last_index_summary": None
}

def ensure_project_dirs():
    """Ensure all required project directories exist."""
    import os
    dirs = [
        UPLOAD_DIR,
        os.path.dirname(LOG_FILE),
        CHROMA_PERSIST_DIR,
        "data/uploads"
    ]
    for d in dirs:
        if d:
            os.makedirs(d, exist_ok=True)
