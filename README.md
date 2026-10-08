# SynapseTutor AI — Multimodal Adaptive Tutoring Platform

> **Multimodal AI Hackathon 2026 — Track D: Personalized Tutoring & Adaptive Learning**  
> Production-quality cognitive tutoring system connecting multimodal course grounding, Bayesian Knowledge Tracing (BKT), multi-tier memory, and self-verifying adaptive assessment.

---

## 🌟 Key Highlights & Capabilities

1. **Source-Grounded Multimodal Knowledge Base**
   - Ingests **PDF textbooks/notes** (PyMuPDF: text, headings, tables, equations, images).
   - Ingests **PowerPoint slide decks** (python-pptx: slide titles, bullet points, speaker notes, tables).
   - Ingests **Lecture videos & audio** (timestamp segments, transcripts, concepts).
   - Ingests **Diagrams & figures** (multimodal vision understanding of entities and relationships).
   - **Canonical Source Anchoring**: Every knowledge unit retains its origin (`[Source: Module 4 • Slide 24]`, `[Source: Operating Systems • Page 384]`, `[Source: Lecture 5 • 32:14]`). Zero fake citations.

2. **Multimodal Grounded RAG with Strict Refusal**
   - Hybrid retrieval combining dense vector similarity and BM25 lexical keyword density with reranking.
   - **Section 37 Off-Material Benchmark**: Blatantly off-topic inquiries (e.g. asking for GPU architectures or recipes in an Operating Systems course) are strictly refused: *"This topic is not covered in the uploaded course material."* Offers explicit, labeled *Outside Knowledge* only upon request.

3. **Cognitive Learner Model & Bayesian Knowledge Tracing (BKT)**
   - Prior initialization ($P(L_0) = 0.15$) for novices.
   - Mathematical evidence updating:
     $$P(L_t \mid \text{Correct}) = \frac{P(L_t) \cdot (1 - P(S))}{P(L_t) \cdot (1 - P(S)) + (1 - P(L_t)) \cdot P(G)}$$
   - Evidence-weighted updates (Exam: 1.0, Short answer: 0.7, Conversation: 0.3).
   - Ebbinghaus-style half-life forgetting decay.
   - Non-sensitive **Learning Behavior Profile** (explanation preferences, pacing, scaffolding).

4. **Machine Learning (`scikit-learn`) for Student Modeling**
   - **Random Forest Classifier**: Pedagogical readiness state (*ready for next*, *needs practice*, *prerequisite gap detected*).
   - **Gradient Boosting Regressor**: Predicts expected quiz score and estimated study minutes to achieve 80% target mastery.

5. **Three-Tier Memory Architecture**
   - **Short-Term Memory**: Ephemeral active session context, sliding dialogue turns.
   - **Long-Term Memory**: Persistent relational profile, concept mastery distributions, behavioral styles.
   - **Episodic Memory**: Semantic timeline of critical learning moments (misconceptions resolved, breakthroughs).

6. **Adaptive Assessment Engine & Self-Verification**
   - Self-verifying pipeline: Generator $\rightarrow$ Deterministic SymPy Math Verifier $\rightarrow$ Distractor Checker $\rightarrow$ Pass.
   - **Novelty Checker**: Question text hash + dense cosine similarity check ($> 0.85$ rejected) ensuring 0% question repetition.
   - **Adaptive Selection**: 50% weak, 30% intermediate, 20% review; plus foundational pre-test mode for cold start.
   - **Misconception Detection**: Diagnoses recurring wrong-answer patterns (e.g., Safe State vs Deadlock State confusion) with targeted remediation guidance.

7. **Multi-Window Chat & Reusable Source Viewer**
   - Multi-conversation ChatGPT-style UI (New Chat, Recent Chats, Pinning, Search, Delete).
   - Slide-over **Source Viewer Drawer** allowing instant inspection of the exact PDF page, slide, or video timestamp when clicking citation chips.

---

## 🏗️ System Architecture

```
                                  USER (Browser)
                                        │
                         React + Vite + Tailwind CSS
   [Dashboard | Course Library | Knowledge Explorer | Tutor Chat | Assessments | Learner Profile]
                                        │
                               REST APIs (FastAPI)
                                        │
        ┌───────────────────────────────┼───────────────────────────────┐
        │                               │                               │
        ▼                               ▼                               ▼
 1. INGESTION PIPELINE           2. GROUNDED RAG PIPELINE        3. LEARNER COGNITIVE ENGINE
 ├─ PDF (PyMuPDF: pages, tables)  ├─ Query Intent & Scope         ├─ Bayesian Knowledge Tracing (BKT)
 ├─ PPTX (python-pptx: slides)    ├─ Hybrid Retrieval (Dense+BM25)├─ ML Readiness Classifier (Random Forest)
 ├─ Video (Timestamps, transcripts)├─ Reranking & Strict Grounding ├─ Learning-Time Regressor (GBR)
 ├─ Vision (Diagram analysis)     ├─ Citation Validation Engine   ├─ 3-Tier Memory Engine:
 └─ Canonical Source Anchoring    └─ Off-Material Refusal            │  • Short-term (Active session)
    (Page / Slide / Timestamp)                                       │  • Long-term (Mastery in DB)
                                                                     │  • Episodic (Struggles/Breakthroughs)
                                                                     └─ Adaptive Assessment Engine
                                                                        (Generator → SymPy Verifier → Novelty)
                                        │
                               STORAGE & AI PROVIDER LAYER
        ┌───────────────────────────────┴───────────────────────────────┐
        ▼                                                               ▼
 RELATIONAL & VECTOR STORAGE                                   AI PROVIDER ABSTRACTION
 ├─ SQLite WAL Mode (Relational, JSON, Foreign Keys)           ├─ Google Gemini (Gemini 2.0 Flash / Pro)
 └─ Chroma Embedded Vector Store (Dense Chunks & Metadata)    ├─ Local Ollama (llama3.2, llama3.2-vision)
                                                               ├─ Deterministic Mock (Zero-key offline mode)
                                                               └─ Local Embeddings & Fast Reranking
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- **Python 3.11+**
- **Node.js v18+** & npm

### 2. Backend Setup
```bash
# 1. Activate Python virtual environment
.\venv\Scripts\activate   # Windows
# or: source venv/bin/activate # Linux/Mac

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
# Copy .env.example to .env (Default uses SQLite & local fallback)
# If you have a Google Gemini key, add: GEMINI_API_KEY="your-key"

# 4. Start FastAPI server
# Schema initializes cleanly on startup (zero fake courses or fake seed data)
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# (Optional) To seed an offline sample Operating Systems demo course:
# python -m scripts.process_sample_course
```
API Documentation will be live at: `http://localhost:8000/docs`

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Web application will be live at: `http://localhost:5173`

On first visit, the app automatically presents the onboarding prompt (*"What should we call you?"*), initializes your clean learning space, and invites you to add your first course and multimodal materials.

---

## 🧪 Automated Evaluation Benchmarks

Run the comprehensive evaluation suite:
```bash
python -m scripts.run_evaluation
```

### Benchmark Results
- **Off-Material Refusal Accuracy (Section 37)**: `100.0% (5/5)`
- **Citation Grounding Accuracy**: `100.0% (3/3)`
- **Assessment Question Verification Pass Rate**: `100.0%`
- **Question Novelty Rate**: `100.0% (0% repetition)`
- **Learner BKT Simulation Gain**: `+95.0%`

---

## 📂 Project Structure

```
project-root/
├── README.md
├── requirements.txt
├── .env.example
├── docker-compose.yml
├── frontend/
│   ├── src/
│   │   ├── components/layout/ (Navbar)
│   │   ├── components/onboarding/ (OnboardingModal)
│   │   ├── components/courses/ (CreateCourseModal)
│   │   ├── components/sources/ (SourceViewerDrawer)
│   │   ├── pages/Dashboard/
│   │   ├── pages/Courses/
│   │   ├── pages/KnowledgeExplorer/
│   │   ├── pages/Tutor/
│   │   ├── pages/Assessments/
│   │   ├── pages/LearnerProfile/
│   │   ├── pages/Analytics/
│   │   ├── services/api.ts
│   │   ├── types/index.ts
│   │   └── responses/index.ts
├── backend/app/
│   ├── main.py
│   ├── api/v1/ (users, courses, documents, chat, assessments, learner, analytics, memory)
│   ├── ingestion/ (pdf, ppt, video, visual_understanding)
│   ├── knowledge_base/ (chunking, prerequisite_graph, topic_extraction, vector_store)
│   ├── rag/ (query_understanding, hybrid_retrieval, citation_validator, grounded_generation)
│   ├── assessment/ (question_generator, question_verifier, novelty_checker, adaptive_selector)
│   ├── learner_model/ (knowledge_tracing, classification, regression, misconception_detector)
│   ├── memory/ (short_term_memory, long_term_memory, episodic_memory)
│   ├── ai/ (llm, vision, embeddings, reranker providers)
│   ├── database/ (models, init_db, session)
│   ├── models/ (re-exported ORM entities)
│   └── responses/ (type-safe Pydantic API response schemas)
├── scripts/ (process_sample_course.py, run_evaluation.py)
└── docs/ (architecture, api, rag_pipeline, learner_model, memory_architecture, evaluation)
```
