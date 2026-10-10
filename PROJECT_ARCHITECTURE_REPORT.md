# SynapseTutor AI — Technical Architecture, AI/ML Techniques & Engineering Report

> **Executive Summary:**  
> **SynapseTutor AI** is a full-stack Multimodal Adaptive Tutoring Platform that ingests heterogeneous course materials (PDF textbooks, PowerPoint slide decks, lecture videos, and diagrams) and delivers strictly source-grounded tutoring, real-time **Bayesian Knowledge Tracing (BKT)**, **Scikit-Learn** readiness predictions, a **3-Tier Cognitive Memory** system, and **Self-Verifying Adaptive Assessments** powered by local GPU LLM inference (**Ollama `qwen2.5:7b` on CUDA**).

---

## 1. End-to-End 4-Layer System Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: INTERACTIVE FRONTEND (React 19 + TypeScript + Vite + Tailwind CSS + KaTeX)      │
│  [ Dashboard ]   [ Tutor Chat ]   [ Adaptive Tests ]   [ Course Library ]   [ Profile ]  │
│  • Multi-session chat with KaTeX math & Mermaid diagrams                                 │
│  • Slide-over Source Viewer Drawer (opens exact PDF page / PPTX slide / Video timestamp) │
└────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                             │ REST API (/api/v1)
                                             ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 2: FASTAPI COGNITIVE ORCHESTRATION ENGINE (Async Python)                           │
│  ├─ 1. Multimodal Ingestion Worker (PyMuPDF, python-pptx, yt-dlp, faster-whisper)        │
│  ├─ 2. Hybrid Grounded RAG Pipeline (Query Rewriting + Dense/BM25 + Off-Topic Refusal)   │
│  ├─ 3. Learner Cognitive Engine (BKT Math + Random Forest Classifier + GBR Regressor)    │
│  ├─ 4. Three-Tier Memory System (Short-Term Sliding + Long-Term DB + Episodic Timeline)  │
│  └─ 5. Self-Verifying Assessment Engine (SymPy Verifier + Cosine Novelty Checker)        │
└─────────────────────┬──────────────────────────────────────────────┬─────────────────────┘
                      ▼                                              ▼
┌─────────────────────────────────────────────┐ ┌──────────────────────────────────────────┐
│ LAYER 3: AI & ML COMPUTE LAYER              │ │ LAYER 4: HYBRID STORAGE LAYER            │
│  • Local LLM: Ollama qwen2.5:7b (CUDA GPU)  │ │  • SQLite (WAL Mode, Async SQLAlchemy)   │
│  • Dense Embeddings: MiniLM-L6-v2 (Local)   │ │    Users, Courses, Mastery, Memory, Chat │
│  • Cross-Encoder Reranker: FlashRank        │ │  • ChromaDB Persistent Vector Store      │
│  • Auto-Fallback: Resilient Mock/Cloud LLM  │ │    Source-Anchored Multimodal Chunks     │
└─────────────────────────────────────────────┘ └──────────────────────────────────────────┘
```

---

## 2. Core AI & Machine Learning Techniques

### Technique 1: Multimodal Course Ingestion & Canonical Source Anchoring
* **Module Path:** `backend/app/ingestion/` & `backend/app/knowledge_base/`
* **How It Works:**
  1. **PDF Textbooks (`pdf_processor.py`):** Uses `PyMuPDF` (`fitz`) to extract text blocks, headings, markdown tables, equations, and figures per page.
  2. **PowerPoint Slides (`ppt_processor.py`):** Uses `python-pptx` to extract slide titles, bullet hierarchies, tables, and speaker notes per slide number.
  3. **Lecture Videos (`video_processor.py`):** Extracts timestamped transcript segments (`MM:SS - MM:SS`) via `youtube-transcript-api` and `faster-whisper`.
  4. **Canonical Source Anchoring:** Every knowledge chunk stored in ChromaDB preserves immutable source coordinates (`[Source: Module 1 • Slide 24]`, `[Source: Page 15]`). Clicking any citation badge in the UI opens the exact page or slide inside the **Source Viewer Drawer**.

---

### Technique 2: Hybrid Grounded RAG with Cross-Encoder Reranking & Strict Refusal
* **Module Path:** `backend/app/rag/`
* **How It Works:**
  1. **Multi-Turn Query Contextualization (`query_understanding.py`):** Rewrites ambiguous follow-up prompts (e.g., *"Can you show a calculation example?"*) using recent conversation turns so retrieval stays locked on the active concept.
  2. **Hybrid Retrieval (`hybrid_retrieval.py`):** Combines **Dense Vector Similarity** (`ChromaDB` + `sentence-transformers/all-MiniLM-L6-v2`) with **BM25 Lexical Keyword Scoring** to capture both conceptual semantics and exact mathematical notation/acronyms.
  3. **FlashRank Reranking:** Re-scores retrieved candidates using a lightweight cross-encoder before prompt construction.
  4. **Strict Off-Material Refusal (`grounded_generation.py`):** Out-of-syllabus questions are strictly refused (*"This topic is not covered in the uploaded course material"*) to prevent hallucination, while offering an explicit opt-in **"Explain with Outside Knowledge"** toggle.

---

### Technique 3: Cognitive Learner Model — Bayesian Knowledge Tracing (BKT) & Scikit-Learn ML
* **Module Path:** `backend/app/learner_model/`
* **How It Works:**
  1. **Bayesian Knowledge Tracing (`knowledge_tracing.py`):**
     * Initializes novice mastery probability at $P(L_0) = 0.15$.
     * Updates posterior mastery after each assessment or chat interaction using Slip $P(S)$, Guess $P(G)$, and Learning Transition $P(T)$ probabilities:
       $$P(L_t \mid \text{Correct}) = \frac{P(L_t)(1 - P(S))}{P(L_t)(1 - P(S)) + (1 - P(L_t))P(G)}$$
       $$P(L_{t+1}) = P(L_t \mid \text{Evidence}) + \bigl(1 - P(L_t \mid \text{Evidence})\bigr) \cdot P(T)$$
     * Weighs evidence by interaction type (**Assessment Quiz = 1.0**, **Short Answer = 0.7**, **Chat Turn = 0.3**) and applies **Ebbinghaus Forgetting Decay** over elapsed days.
  2. **Random Forest Readiness Classifier (`classification.py`):**
     * Uses `scikit-learn` `RandomForestClassifier` to classify each topic into `ready_for_next`, `needs_practice`, or `prerequisite_gap`.
  3. **Gradient Boosting Study-Time Regressor (`regression.py`):**
     * Uses `scikit-learn` `GradientBoostingRegressor` to predict expected quiz scores and estimate the study minutes needed to reach the 80% mastery threshold.

---

### Technique 4: Three-Tier Cognitive Memory Architecture
* **Module Path:** `backend/app/memory/`
* **How It Works:**
  1. **Short-Term Memory (`short_term_memory.py`):** Sliding window of active session dialogue turns for immediate conversational context.
  2. **Long-Term Memory (`long_term_memory.py`):** Persistent SQLite mastery records and an adaptive **Learning Behavior Profile** (automatically switches `explanation_preference` to `intuitive_analogy_first` when student confusion signals are detected in chat).
  3. **Episodic Memory (`episodic_memory.py`):** Stores timestamped learning milestones (`confusion`, `misconception_detected`, `mastery_breakthrough`) and injects relevant past struggles into future tutor prompts.

---

### Technique 5: Self-Verifying Adaptive Assessment Engine
* **Module Path:** `backend/app/assessment/`
* **How It Works:**
  1. **Adaptive Selector (`adaptive_selector.py`):** Samples questions using a **50% weak / 30% intermediate / 20% review** distribution (plus a Cold-Start Diagnostic Pre-Test mode for new courses).
  2. **Deterministic Verification (`question_verifier.py`):** Validates generated questions using **SymPy** symbolic math verification and distractor uniqueness checks.
  3. **Novelty Checker (`novelty_checker.py`):** Rejects any generated question with $> 0.85$ dense cosine similarity against previously asked questions, ensuring **0% question repetition**.

---

## 3. Complete Engineering Log — What Was Built, Configured & Fixed

| # | Area | Issue / Requirement | Engineering Solution Implemented | Files Updated |
| :- | :--- | :--- | :--- | :--- |
| **1** | **Full-Stack Server Setup** | Run both FastAPI backend and React/Vite frontend reliably on Windows. | Verified Python 3.13 & Node.js v24, audited 179 frontend npm packages, initialized clean SQLite WAL database schema, and launched FastAPI (`127.0.0.1:8000`) & Vite (`localhost:5173`). | Runtime Environment |
| **2** | **Resilient LLM & Vision Auto-Fallback** | Tutor Chat threw `Error: Failed to fetch` (HTTP 500) when `.env` pointed to an offline Ollama port because `OllamaLLMProvider` lacked connection exception handling. | Added `try / except` fallback blocks in `OllamaLLMProvider`, `GeminiLLMProvider`, and `OllamaVisionProvider` so any connection refusal or API failure gracefully falls back to `MockLLMProvider` without crashing. | `backend/app/ai/llm/provider.py`<br>`backend/app/ai/vision/provider.py` |
| **3** | **Local Ollama 7B (`qwen2.5:7b`) GPU Integration** | Connect the platform to a local 7B LLM with hardware GPU acceleration. | Started the Ollama daemon (`ollama serve` on `127.0.0.1:11434`) utilizing the **NVIDIA GeForce RTX 3050 6GB Laptop GPU (CUDA)**, configured `LLM_PROVIDER="ollama"` & `OLLAMA_MODEL="qwen2.5:7b"`, and verified live end-to-end RAG responses. | `.env` |
| **4** | **KaTeX Mathematical Formula Rendering** | `qwen2.5:7b` outputs standard LaTeX delimiters `\(...\)` (inline) and `\[...\]` (display blocks), which were displayed as raw unformatted text in chat. | Upgraded both the inline tokenizer regex and the multiline block parser in `FormattedMessage.tsx` to detect `\(...\)`, `\[...\]`, `$...$`, and `$$...$$` and render them via **KaTeX**. | `frontend/src/components/chat/FormattedMessage.tsx` |
| **5** | **UI Navigation Streamlining** | Remove *Knowledge Explorer* and *Analytics* tabs to keep the interface focused. | Removed the Knowledge Explorer and Analytics tabs, icons, imports, and route views from `Navbar.tsx` and `App.tsx`, leaving 5 core modules: **Dashboard, Tutor Chat, Adaptive Tests, Course Library, and Learner Profile**. | `frontend/src/components/layout/Navbar.tsx`<br>`frontend/src/App.tsx` |
