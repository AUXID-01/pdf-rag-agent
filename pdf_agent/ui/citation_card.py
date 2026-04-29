import streamlit as st
from llm.response_parser import Citation
from typing import List

def render_citation_chips(citations: List[Citation]) -> None:
    """
    Renders each citation as a styled chip below the answer.
    """
    if not citations:
        return

    st.markdown("**Sources:**")
    cols = st.columns(min(len(citations), 4))

    for i, citation in enumerate(citations):
        col = cols[i % len(cols)]
        with col:
            st.markdown(
                f"""
                <div style="
                    background-color: #1e3a5f;
                    color: #e0f0ff;
                    padding: 6px 12px;
                    border-radius: 16px;
                    font-size: 0.78rem;
                    font-weight: 500;
                    text-align: center;
                    margin: 2px 0;
                    border: 1px solid #2d5a8e;
                ">
                    📄 Page {citation.page} &nbsp;|&nbsp; {citation.section}
                </div>
                """,
                unsafe_allow_html=True
            )

def render_refusal_chip() -> None:
    """
    Renders a red chip when gate2 fails — shows the answer was blocked.
    """
    st.markdown(
        """
        <div style="
            background-color: #3a1e1e;
            color: #ffcccc;
            padding: 6px 12px;
            border-radius: 16px;
            font-size: 0.78rem;
            font-weight: 500;
            text-align: center;
            margin: 4px 0;
            border: 1px solid #8e2d2d;
        ">
            ⚠️ Citation validation failed — response blocked
        </div>
        """,
        unsafe_allow_html=True
    )
