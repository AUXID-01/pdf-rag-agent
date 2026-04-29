# 📄 PDF-Grounded Conversational RAG Agent

A production-grade, evaluator-centric RAG system designed for high-accuracy document Q&A. Built with a focus on **traceability**, **factual grounding**, and **adaptive ingestion**.

---

## 🚀 Key Features

### 1. Adaptive Ingestion Pipeline
- **Tiered Parsing**: Falls back from `PyMuPDF` to `pdfplumber` and finally to `Tesseract OCR` for scanned documents.
- **Quality Guardrails**: Automatically detects low-quality OCR and switches to "Scanned Content" metadata mode with atomic micro-chunking (150 chars).

### 2. Multi-Stage Retrieval & Ranking
- **Hybrid Retrieval**: Semantic search via ChromaDB and `all-MiniLM-L6-v2`.
- **Intelligent Reranking**: Stage 2 re-scoring using a bi-encoder with **Adaptive Thresholding** (0.25 for standard, 0.15 for follow-ups).
- **Intent Boosting**: Metadata-aware scoring that prioritize chunks where section titles match query intent (e.g., "Inflation", "Growth").

### 3. Dual-Gate Safety System
- **Gate 1 (Hallucination Gate)**: Protects against out-of-scope queries and scattered/irrelevant context using semantic confidence analysis.
- **Gate 2 (Citation Validator)**: Forces the LLM to provide exact sources and validates them against the retrieved context before displaying the answer.

### 4. Visibility & Observability
- **Reasoning Trace Panel**: A real-time sidebar providing full transparency into the pipeline's decisions (Query Rewriting, Retrieval Scores, Gate Reasons, and OCR Status).
- **Structured Refusals**: Context-aware refusals that explain *why* an answer wasn't provided (Out-of-Scope, False Assumption, or Partial Match).

---

## 🛠️ Tech Stack

- **Core**: Python 3.10+
- **Frontend**: Streamlit
- **Vector DB**: ChromaDB
- **Models**:
  - LLM: `llama-3.3-70b-versatile` (via Groq)
  - Embedding: `all-MiniLM-L6-v2` (Sentence Transformers)
- **Parsing**: PyMuPDF (fitz), pdfplumber, Tesseract OCR

---

## 📦 Installation

1. **Clone the repository**:
   ```bash
   git clone <repo-url>
   cd pdf_agent
   ```

2. **Set up Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**:
   Create a `.env` file in the root directory:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   ```

---

## 🖥️ Usage

1. **Run the App**:
   ```bash
   streamlit run app.py
   ```

2. **Upload & Index**:
   - Drag and drop a PDF into the sidebar.
   - Click **🚀 Ingest & Index** to process the document.
   - Monitor the **Trace Panel** to see the pipeline in action.

3. **Chat**:
   - Ask questions about the document.
   - Use follow-up questions (e.g., "What are the risks there?") to test multi-turn memory.
   - Verify answers using the **Sources** block at the end of every response.

---

## 📂 Project Structure

```text
pdf_agent/
├── app.py                # Main Streamlit Application
├── config.py             # System Hyperparameters (Thresholds, Paths)
├── ingestion/            # Parsing, Cleaning, & Metadata Logic
├── indexing/             # Embedding & Vector Store Orchestration
├── retrieval/            # Semantic Search, Reranking, & Hallucination Gates
├── conversation/         # Query Rewriting & History Management
├── llm/                  # Groq Client & Prompt Construction
├── logs/                 # Observability & Trace Schema
└── ui/                   # Reusable UI Components
```

---

## ⚖️ Evaluation Standards

This agent is built to comply with **Evaluator-Grade** standards:
- **Zero Hallucination**: Strict refusals on uncertain context.
- **Traceability**: Every decision is logged and visible in the UI.
- **Groundedness**: Every factual claim is backed by a `[Page X | Section Y]` source.

---
