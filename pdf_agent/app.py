import streamlit as st
import os
import json
from datetime import datetime
from config import ensure_project_dirs, UPLOAD_DIR, CITATION_FORMAT, SESSION_KEYS
from ingestion.parser import parse_pdf
from ingestion.cleaner import clean_pages
from ingestion.metadata import enrich_metadata, clean_section_title
from ingestion.chunker import chunk_pages
from indexing.index_builder import build_index
from retrieval.searcher import search_query
from retrieval.hallucination_gate import evaluate, GateResult
from retrieval.reranker import rerank
from llm.prompt_builder import build_messages, SYSTEM_PROMPT
from llm.groq_client import call_llm
from llm.response_parser import parse_llm_response
from llm.gate2_checker import validate_citations_against_chunks
from ui.citation_card import render_citation_chips, render_refusal_chip
from conversation.history import is_followup
from conversation.query_rewriter import rewrite_query
from retrieval.citations import build_clean_citations
from logs.logger import get_logger

log = get_logger("app")


# 1. Page Configuration
st.set_page_config(
    page_title="PDF Agent | Phase 6 Enhanced Retrieval",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Session State Initialization
for key, default_value in SESSION_KEYS.items():
    if key not in st.session_state:
        st.session_state[key] = default_value

def add_trace(message: str, level: str = "INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.trace_log.append(f"[{timestamp}] {level}: {message}")
    if len(st.session_state.trace_log) > 20:
        st.session_state.trace_log.pop(0)

# 3. Sidebar: Configuration & Status
with st.sidebar:
    st.title("🎛️ Control Panel")
    
    # Upload Widget
    uploaded_file = st.file_uploader("Upload Source PDF", type=["pdf"])
    if uploaded_file:
        file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
        if st.session_state.uploaded_doc != uploaded_file.name:
            # New file uploaded
            ensure_project_dirs()
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            st.session_state.uploaded_doc = uploaded_file.name
            st.session_state.indexed = False
            st.session_state.chunk_count = 0
            st.session_state.last_index_summary = None
            st.session_state.last_retrievals = []
            add_trace(f"Uploaded {uploaded_file.name}")
            st.success(f"File uploaded: {uploaded_file.name}")

    st.markdown("---")
    
    # Ingest Button
    can_ingest = st.session_state.uploaded_doc is not None and not st.session_state.indexed
    if st.button("🚀 Ingest & Index", disabled=not can_ingest):
        with st.spinner("Processing PDF Pipeline..."):
            try:
                add_trace("Starting ingestion pipeline...")
                file_path = os.path.join(UPLOAD_DIR, st.session_state.uploaded_doc)
                
                # Run Pipeline
                parsed = parse_pdf(file_path)
                add_trace(f"Parsed {parsed.total_pages} pages")
                
                cleaned = clean_pages(parsed)
                add_trace("Text cleaning complete")
                
                enriched = enrich_metadata(cleaned)
                add_trace("Metadata enrichment complete")
                
                chunks = chunk_pages(enriched)
                add_trace(f"Created {len(chunks)} chunks")
                
                summary = build_index(chunks, source_doc=st.session_state.uploaded_doc)
                add_trace("Vector indexing complete")
                
                # Update State
                st.session_state.indexed = True
                st.session_state.chunk_count = summary.get("indexed_chunk_count", 0)
                st.session_state.last_index_summary = summary
                
            except Exception as e:
                add_trace(f"Error during ingestion: {str(e)}", level="ERROR")
                st.error(f"Ingestion failed: {e}")

    st.markdown("---")
    
    # Status Display
    st.subheader("System Status")
    if not st.session_state.uploaded_doc:
        st.info("Upload PDF to begin")
    elif not st.session_state.indexed:
        st.warning("Ready to index")
    else:
        st.success(f"✅ Indexed {st.session_state.chunk_count} chunks from {st.session_state.uploaded_doc}")
        if st.session_state.last_index_summary:
            with st.expander("Index Summary"):
                st.json(st.session_state.last_index_summary)

    # Retrieval Execution Trace (Requirement 8: Compact Sidebar)
    if st.session_state.last_retrievals:
        st.markdown("---")
        st.subheader("🎯 Latest Retrieval Hits")
        for i, hit in enumerate(st.session_state.last_retrievals):
            section = clean_section_title(hit['section'], hit.get('text', ''))
            # Truncate section title for sidebar
            short_section = (section[:15] + '..') if len(section) > 15 else section
            st.caption(f"**#{i+1}** | P{hit['page']} | {short_section} | Dist: {hit['distance']:.2f}")

    st.markdown("---")
    
    # Sidebar Trace
    st.subheader("Execution Trace")
    trace_container = st.container(height=250)
    with trace_container:
        for event in reversed(st.session_state.trace_log):
            st.caption(event)

# 4. Main Panel: Chat Interface
st.title("📄 PDF-Grounded Conversational Agent")

def render_retrieval_hits(hits, msg_idx=0):
    """Utility to render hits consistently in history and current turn."""
    with st.expander("Retrieved Context Chunks", expanded=False):
        for i, hit in enumerate(hits):
            section = clean_section_title(hit['section'], hit.get('text', ''))
            # Requirement 3 & 4: Rendering logic
            if section == "General":
                 section_html = f"*{section}*"  # Less emphasis
            else:
                 section_html = f"**{section}**"
            
            citation = CITATION_FORMAT.format(page=hit['page'], section=section_html)
            st.markdown(f"**Chunk #{i+1}** | {citation} | Distance: {hit['distance']:.3f}")
            
            # Requirement 2 & 6: Cleaned Preview
            st.info(hit['preview'])
            
            # Requirement 7: Full Text Toggle (Avoid nested expanders)
            if st.checkbox("View Full Raw Chunk", key=f"show_raw_{msg_idx}_{i}_{hit['chunk_id']}"):
                st.text(hit['text'])

# Display Chat History 
for msg_idx, message in enumerate(st.session_state.chat_history):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "hits" in message:
            render_retrieval_hits(message["hits"], msg_idx=msg_idx)

# Chat Input
if prompt := st.chat_input("Ask a question about the document"):
    # CHANGE 2 & 4: Capturing prompt and appending to history
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    
    rewrite_result = rewrite_query(prompt, st.session_state.chat_history)

    if rewrite_result["needs_clarification"]:
        with st.chat_message("assistant"):
            st.warning(
                "Your question references something unclear from the "
                "conversation. Could you clarify what you are referring to?"
            )
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": "Clarification requested — query too ambiguous to resolve.",
            "citations": []
        })
        st.stop()

    retrieval_query = rewrite_result["rewritten_query"]

    if rewrite_result["was_rewritten"]:
        log.info("query_rewritten",
                 original=prompt,
                 rewritten=retrieval_query)

    with st.chat_message("user"):
        st.markdown(prompt)
    
    add_trace(f"User query: {prompt}")

    # Assistant Logic
    with st.chat_message("assistant"):
        if not st.session_state.indexed:
            response = "I haven't indexed the document yet. Please click 'Ingest & Index' in the sidebar first."
            st.markdown(response)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
        else:
            with st.spinner("Retrieving relevant context..."):
                hits = search_query(
                    query=retrieval_query,
                    doc_id=st.session_state.uploaded_doc,
                    top_k=20
                )
                # CHANGE 3: Use retrieval_query for rerank
                hits = rerank(query=retrieval_query, hits=hits)
                if hits:
                    add_trace(f"Reranked to {len(hits)} chunks | top score: {hits[0]['rerank_score']:.3f}")
                else:
                    add_trace("Rerank returned empty", level="WARNING")

                gate: GateResult = evaluate(hits=hits, query=retrieval_query)
                st.session_state.last_retrievals = gate.hits
                add_trace(f"Gate decision: {gate.reason} | best_sim={gate.best_similarity:.3f}")

                if gate.passed:
                    with st.spinner("Generating grounded answer..."):
                        try:
                            messages = build_messages(query=retrieval_query, hits=gate.hits)
                            raw_answer = call_llm(system_prompt=SYSTEM_PROMPT, messages=messages)
                            parsed = parse_llm_response(raw_answer)
                            gate2_result = validate_citations_against_chunks(parsed, gate.hits)

                            if not gate2_result["passed"]:
                                st.warning(
                                    f"The system could not produce a verifiable cited answer. "
                                    f"Reason: {gate2_result['reason']}"
                                )
                                render_refusal_chip()
                            else:
                                clean_citations = build_clean_citations(gate.hits)
                                
                                # ENFORCE SOURCES BLOCK FORMAT (No inline)
                                source_block = ""
                                if clean_citations:
                                    source_block = "\n\n**Sources:**\n" + "\n".join([f"[Page {c[0]} | {c[1]}]" for c in clean_citations])
                                
                                full_answer = parsed.answer_text + source_block
                                st.markdown(full_answer)
                                
                                # DISABLED: Sources block and Chips (as per Step 5)
                                # render_citation_chips(clean_citations) 
                                
                                render_retrieval_hits(gate.hits)

                            # Append to session history only if gate2 passed
                            if gate2_result["passed"]:
                                st.session_state.chat_history.append({
                                    "role": "assistant",
                                    "content": full_answer,
                                    "citations": [
                                        {"page": c[0], "section": c[1]}
                                        for c in clean_citations
                                    ],
                                    "hits": gate.hits
                                })
                            else:
                                st.session_state.chat_history.append({
                                    "role": "assistant",
                                    "content": "[Response blocked — citation validation failed]",
                                    "citations": []
                                })

                            add_trace("LLM response generated successfully")
                        except Exception as e:
                            add_trace(f"LLM call failed: {str(e)}", level="ERROR")
                            st.error(f"Answer generation failed: {e}")
                else:
                    st.warning(gate.message)
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": gate.message,
                    })
                    add_trace(f"Gate refused — {gate.reason}", level="WARNING")

# 5. Footer / Info
if not st.session_state.chat_history:
    st.markdown("""
    ### Welcome!
    This is your PDF-grounded assistant.
    1. **Upload** a PDF in the sidebar.
    2. **Ingest** it to create searchable embeddings.
    3. **Chat** to retrieve relevant context using semantic search.
    """)
