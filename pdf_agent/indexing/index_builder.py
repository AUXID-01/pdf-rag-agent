"""
indexing/index_builder.py
Responsibility: Orchestrate the flow from ingestion chunks to persistent vector storage.
Inputs: List[Chunk] (dataclass or dict)
Outputs: Summary dict of the operation.
Dependencies: indexing/embedder.py, indexing/vector_store.py, config.py, logs/logger.py
"""

from typing import List, Any, Dict
from config import CHROMA_COLLECTION_NAME, CHROMA_PERSIST_DIR
from logs.logger import get_logger
from indexing.vector_store import VectorStore

log = get_logger("indexing.index_builder")

def build_index(chunks: List[Any], source_doc: str = "Unknown") -> Dict[str, Any]:
    """
    Takes a list of chunk objects, validates them, embeds them, and persists them.
    Supports both dataclass attributes and dict keys for chunk objects.
    """
    log.info("index_build_start", source_doc=source_doc, chunk_count=len(chunks))
    
    if not chunks:
        log.warning("index_build_empty", source_doc=source_doc)
        return {
            "indexed_chunk_count": 0,
            "status": "empty_input"
        }

    valid_chunks = []
    ids = []
    texts = []
    metadatas = []

    # 1. Validation and Extraction
    try:
        for chunk in chunks:
            # Flexible access for dataclass or dict
            c_id = getattr(chunk, 'chunk_id', None) or chunk.get('chunk_id')
            c_text = getattr(chunk, 'text', None) or chunk.get('text')
            c_page = getattr(chunk, 'page', None) or chunk.get('page') or getattr(chunk, 'page_start', None) or chunk.get('page_start')
            c_section = getattr(chunk, 'section_title', None) or chunk.get('section_title')
            c_page_end = getattr(chunk, 'page_end', None) or chunk.get('page_end', c_page)
            c_chars = getattr(chunk, 'char_count', None) or chunk.get('char_count', len(c_text) if c_text else 0)

            if not c_id or not c_text or c_page is None:
                continue

            ids.append(c_id)
            texts.append(c_text)
            metadatas.append({
                "source_doc": source_doc,
                "chunk_id": c_id,
                "page": int(c_page),
                "page_end": int(c_page_end),
                "section_title": str(c_section or "General"),
                "char_count": int(c_chars)
            })
            valid_chunks.append(chunk)

        log.info("chunk_validation_complete", valid_count=len(ids))
        
        if not ids:
            raise ValueError("No valid chunks remained after validation.")

        # 2. Embedding
        from indexing.embedder import get_model
        model = get_model()
        embeddings = model.encode(texts, convert_to_numpy=True).tolist()

        # 3. Persistence
        vector_store = VectorStore()
        vector_store.add_chunks(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas
        )

        log.info("index_build_complete", source_doc=source_doc, total_indexed=len(ids))
        
        return {
            "collection_name": CHROMA_COLLECTION_NAME,
            "indexed_chunk_count": len(ids),
            "persist_path": CHROMA_PERSIST_DIR,
            "source_doc": source_doc,
            "status": "success"
        }

    except Exception as e:
        log.error("index_build_failed", source_doc=source_doc, error=str(e))
        raise e
