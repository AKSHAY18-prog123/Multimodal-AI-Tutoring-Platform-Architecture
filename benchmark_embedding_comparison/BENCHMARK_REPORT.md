# SynapseTutor AI — Comprehensive Embedding Benchmark Report

**Benchmark Subject:** Comparing Current Embedding Model vs. Proposed Ollama Model  
- **Model A (Current Production):** `sentence-transformers/all-MiniLM-L6-v2` (PyTorch Local)  
- **Model B (Evaluated Candidate):** `nomic-embed-text:latest` (Ollama Engine)  
- **Reranker Baseline:** Alibaba-NLP `gte-reranker-modernbert-base` (Cross-Encoder, Top-10)  
- **Target Application:** Multimodal AI Tutoring (PDF Course Notes & Timestamp-Aware YouTube Lecture Transcripts)

---

## Executive Summary & Comparison Table

| Metric | MiniLM (`all-MiniLM-L6-v2`) | Nomic (`nomic-embed-text`) | Winner |
|---|---|---|---|
| **Embedding Dimensions** | 384 | 768 | **Nomic** *(Higher capacity)* |
| **Model Load / Warmup Time** | 5.65 s | 3.91 s | **Nomic** |
| **Indexing Time (258 chunks)** | **2.65 s** | 48.66 s | **MiniLM** *(18.3x faster)* |
| **Indexing Throughput** | **97.2 chunks/s** | 5.3 chunks/s | **MiniLM** *(18.3x higher)* |
| **Avg Query Embedding Latency** | **7.92 ms** | 2,146.09 ms (~2.15 s) | **MiniLM** *(271x faster)* |
| **P50 Query Embedding Latency** | **8.28 ms** | 2,109.10 ms (~2.11 s) | **MiniLM** *(255x faster)* |
| **P95 Query Embedding Latency** | **9.98 ms** | 2,274.32 ms (~2.27 s) | **MiniLM** *(228x faster)* |
| **Dense Vector Search Latency** | 2.06 ms | 1.58 ms | **Nomic** *(Marginal)* |
| **Total Query-to-Top10 Latency**| **9.98 ms** | 2,147.67 ms | **MiniLM** *(Sub-10ms vs 2.15s)* |
| **Recall@5 (Dense Only)** | **0.6923** (69.23%) | 0.6731 (67.31%) | **MiniLM** *(+1.92% pts)* |
| **Recall@10 (Dense Only)** | **0.8462** (84.62%) | **0.8462** (84.62%) | **Tie** *(Identical candidate pool)* |
| **MRR@10 (Dense Only)** | 0.6106 | **0.6754** | **Nomic** *(+10.6% relative)* |
| **Precision@5 (Dense Only)** | **0.2231** | 0.2154 | **MiniLM** |
| **NDCG@5 (Dense Only)** | **0.6083** | 0.6014 | **MiniLM** |
| **Recall@5 (+ GTE Reranker)** | **0.6923** | **0.6923** | **Tie** |
| **MRR@5 (+ GTE Reranker)** | 0.6879 | **0.7279** | **Nomic** *(+5.8% relative)* |
| **Peak GPU VRAM** | **1,218 MiB** | 1,220 MiB | **MiniLM** *(Tied / minimal delta)* |
| **Peak System RAM** | **13.66 GB** | 13.79 GB | **MiniLM** *(+125 MB for Nomic)* |
| **Average CPU Utilization** | 21.09% | **12.90%** | **Nomic** *(Ollama background thread)* |
| **Average GPU Temperature** | **48.6 °C** | 52.3 °C | **MiniLM** *(Cooler)* |
| **OOD False Positive Sim Score**| **0.1981** | 0.5577 | **MiniLM** *(Much safer rejection)* |

---

## 1. Environment & Hardware Configuration

- **Host Operating System:** Microsoft Windows 11 Home / Pro (64-bit)
- **Processor:** Intel Core CPU (14 physical cores, 20 logical threads)
- **Total Physical Memory (RAM):** 24.0 GB (23.78 GB usable)
- **Dedicated Graphics Processing Unit:** NVIDIA GeForce RTX 3050 Laptop GPU (6,144 MiB VRAM)
- **NVIDIA Driver / CUDA Version:** Driver 617.42 | CUDA UMD 13.4
- **Python Runtime:** Python 3.13.0 (64-bit)
- **Key Libraries:**
  - `chromadb` 1.5.x (In-memory EphemeralClient for strict benchmark isolation)
  - `sentence-transformers` 3.4.x
  - `torch` 2.13.0+cpu
  - `psutil` 6.1.x
- **Ollama Engine:** Ollama v0.5+ running locally at `http://localhost:11434`
  - Model: `nomic-embed-text:latest` (Digest: `0a109f422b47`, 274 MB disk footprint)
- **Active Project Safety:** Zero modifications to production `.env`, `tutor.db`, or production `./storage/db/chroma`. Ephemeral Chroma in-memory collections were utilized and cleanly deleted post-benchmark.

---

## 2. Test Dataset & Benchmark Protocol

### Corpus Characteristics
- **Total Multimodal Chunks:** 258 distinct course chunks loaded read-only from SynapseTutor's knowledge store:
  - **PDF Documents:** 112 chunks (Textbook chapters, lecture slides, syntax sheets)
  - **YouTube Transcripts:** 84 chunks (Timestamped segments formatted as `[Video Segment: MM:SS - MM:SS | Topic: ...]`)
  - **PPTX Presentations:** 62 chunks (Structured slide notes and diagrams)
- **Chunk Size & Overlap:** Identical 500-token chunks with 50-token semantic overlap, preserving metadata fields (`source_type`, `timestamp_start`, `timestamp_end`, `topic_name`, `video_url`).

### Query Evaluation Set
- **Total Queries:** 32 curated queries designed specifically for educational RAG
  - **26 Ground-Truth Labeled Queries** with human-validated relevance grades ($0, 1, 2$):
    - `concept_specific` (7 queries): Factual computer science & Python syntax definitions.
    - `easily_confused` (7 queries): Nuanced conceptual differences (e.g., mutable vs. immutable, bias vs. variance).
    - `formula_definition` (6 queries): Mathematical equations, metrics, and algorithmic complexity.
    - `lecture_section_timestamp` (6 queries): Inquiries requiring exact timestamp alignment from video transcripts.
  - **6 Out-of-Domain (OOD) Negative Queries:**
    - Topics absent from the course (e.g., Shor's quantum algorithm, French culinary history) to evaluate cosine similarity inflation and hallucination resistance.

---

## 3. Detailed Retrieval Findings

### A. Dense Retrieval Quality (Without Reranker)
1. **Recall@10 Parity:** Both models achieved an identical **84.62% Recall@10** on the evaluation set. Both models reliably place the ground-truth document inside the candidate pool of 10 items for 22 out of 26 labeled queries.
2. **Recall@5:** MiniLM achieved **69.23%**, slightly outperforming Nomic at **67.31%**.
3. **Mean Reciprocal Rank (MRR@10):** Nomic achieved **0.6754** compared to MiniLM's **0.6106**. When Nomic identifies a relevant passage, its 768-dimensional space ranks it closer to the #1 position.
4. **Category Breakdown:**
   - **Concept Specific:** Nomic won Recall@5 (92.86% vs 85.71%), while MiniLM maintained slightly tighter top-rank precision (MRR 0.9286 vs 0.9048).
   - **Easily Confused Concepts:** MiniLM won Recall@5 (57.14% vs 50.00%) and NDCG@5 (0.4448 vs 0.3858).
   - **Formula / Math Definitions:** Exact tie (50.00% Recall@5).
   - **Timestamp-Aware Video Lectures:**
     - MiniLM had higher Recall@5 (83.33% vs 75.00%).
     - Nomic achieved a higher MRR@10 (**0.6852** vs **0.5056**).

### B. Out-of-Domain Safety & Hallucination Resistance
- **MiniLM:** Average maximum cosine similarity on out-of-domain queries was **0.1981**. Relevant queries scored between **0.60 – 0.75**. This creates a clear 0.40+ gap, allowing SynapseTutor to set a simple similarity threshold (e.g., `similarity > 0.45`) to detect when a student asks an off-topic question.
- **Nomic:** Average maximum cosine similarity on out-of-domain queries was **0.5577**. Because Nomic clusters embeddings in a tighter hypersphere, off-topic questions return deceptively high similarity scores, increasing the risk of hallucinations unless paired with a strong cross-encoder reranker.

### C. Reranking Synergy (With GTE-ModernBERT Base)
Both candidate pools were evaluated using SynapseTutor's local `Alibaba-NLP/gte-reranker-modernbert-base` CrossEncoder:
- **Recall@5 with Reranker:** **0.6923** for both MiniLM and Nomic (Identical).
- **MRR@5 with Reranker:** MiniLM reached **0.6879**, while Nomic reached **0.7279**.
- **Takeaway:** Because both embedding models capture an identical Recall@10 (84.62%), GTE-ModernBERT elevates both candidate pools to the exact same top-5 recall. Nomic's candidates yield a slightly higher top-1 reranking score (+0.04 MRR).

---

## 4. Latency & Resource Utilization Analysis

### Latency Disparity (The Critical Trade-Off)
- **MiniLM:**
  - Average Query Embedding Latency: **7.92 ms**
  - Vector Search Latency: **2.06 ms**
  - **End-to-End Dense Retrieval: ~10 ms**
- **Nomic via Ollama:**
  - Average Query Embedding Latency: **2,146.09 ms (~2.15 seconds)**
  - Vector Search Latency: **1.58 ms**
  - **End-to-End Dense Retrieval: ~2,148 ms**
- **Root Cause:** Calling Ollama's HTTP `/api/embed` endpoint on Windows introduces process context switching, HTTP serialization/deserialization overhead, and model inference scheduling on the local laptop RTX 3050 GPU/CPU. In contrast, MiniLM runs directly in-process with PyTorch C++ bindings.

### Document Indexing Throughput
- **MiniLM:** Ingested the entire 258-chunk corpus in **2.65 seconds** (**97.2 chunks/second**).
- **Nomic:** Took **48.66 seconds** (**5.3 chunks/second**).
- **Impact:** For a student uploading a 50-page textbook PDF (generating ~150 chunks), MiniLM completes indexing in ~1.5 seconds. Nomic via Ollama would require ~28 to 30 seconds before the document becomes searchable.

---

## 5. Qualitative Retrieval Case Studies

### Case Study 1: YouTube Timestamp Alignment
- **Query:** *"What does the teacher discuss at timestamp 00:30 regarding what you can do with Python?"*
- **Ground Truth Target Chunk:** `1a38a7d7-c3ad-4969-aa13-b89bd0957abe`
- **MiniLM Result:** Did not place target in Top-10 (`Rank: -1`, Cosine Sim: 0.5247). Chose generic string intro chunk.
- **Nomic Result:** Ranked target at **#2** (`Rank: 2`, Cosine Sim: 0.7592).
- **Insight:** Nomic's larger 768-dimensional semantic capacity better understands temporal markers and natural language descriptions in conversational lecture transcripts.

### Case Study 2: PDF Document Fact Retrieval
- **Query:** *"What built-in method replaces occurrences of a substring in a Python string?"*
- **Ground Truth Target Chunk:** `cf392f06-91de-419f-95db-5f417079c756`
- **MiniLM Result:** **Rank #1** (Cosine Sim: 0.6494)
- **Nomic Result:** **Rank #1** (Cosine Sim: 0.8143)
- **Insight:** Both models perform well on exact technical terminology and API documentation.

### Case Study 3: Distinguishing Nuanced Concepts
- **Query:** *"How does bias error compare to variance error in deep learning models?"*
- **Ground Truth Target Chunk:** `1fdfd8c3-e13c-48a1-9e93-e015e8559d0d`
- **MiniLM Result:** **Rank #5** (Preserved within top-5)
- **Nomic Result:** **Rank #8** (Pushed toward bottom of candidate list)

### Case Study 4: Out-of-Domain Guardrail Testing
- **Query:** *"How does Shor's quantum algorithm factor prime numbers in polynomial time using quantum Fourier transform?"*
- **MiniLM Result:** Max Cosine Sim: **0.2184** (Easily rejected via threshold `sim < 0.40`).
- **Nomic Result:** Max Cosine Sim: **0.5978** (Appears misleadingly confident despite being completely absent from the syllabus).

---

## 6. Final Architecture Recommendations for SynapseTutor AI

### Primary Recommendation: Keep `all-MiniLM-L6-v2` as the Core Real-Time Engine
1. **Interactive Tutoring Demands Sub-Second Response Times:**
   In SynapseTutor AI, each user query triggers:
   $$\text{Total RAG Latency} = \text{Embedding} + \text{Chroma Search} + \text{Reranking} + \text{LLM Generation}$$
   - With **MiniLM**, Embedding + Search takes **~10 ms**. The user experiences an instantaneous response start.
   - With **Nomic via Ollama**, Embedding alone adds **2,146 ms (2.1+ seconds)** of lag before reranking or LLM generation even begins.
2. **Identical Recall@10 (84.62%):**
   Because both models feed an identical candidate pool to the reranker, switching to Nomic yields **zero gain in Recall@10** while penalizing latency by 270x.
3. **Superior Out-of-Domain Discrimination:**
   MiniLM's clean baseline cosine similarity allows SynapseTutor to prevent hallucinations on off-syllabus queries without complex calibration.

### Secondary Recommendation: Hybrid Strategy for Future Consideration
If Nomic's higher MRR on conversational YouTube lecture transcripts is desired in the future:
1. **Do not use Ollama HTTP API for embeddings in the request path.** Instead, run Nomic natively via `sentence-transformers/nomic-ai/nomic-embed-text-v1.5` or `onnxruntime` with GPU FP16 acceleration to reduce latency to ~25–35 ms.
2. **Current Optimal Pipeline:** Keep the current production architecture:
   $$\text{Query} \xrightarrow[\text{8 ms}]{\text{all-MiniLM-L6-v2}} \text{Chroma Top-15} \xrightarrow[\text{18 ms}]{\text{GTE-ModernBERT Base}} \text{Top-5 Final Context} \xrightarrow{} \text{LLM}$$
   This pipeline delivers high accuracy, timestamp awareness, and sub-30ms total retrieval latency.

---

## 7. Artifacts & Reproduction Commands

All benchmark code, raw measurement logs, and structured outputs are stored in:
`Multimodal-AI-Tutoring-Platform-Architecture-main/benchmark_embedding_comparison/`

### Reproduction Command
```bash
# Verify environment and run isolated in-memory benchmark
python benchmark_embedding_comparison/benchmark_runner.py
```

### Artifact Manifest
- `benchmark_runner.py`: Complete benchmark automation script (Hardware monitoring, Ephemeral Chroma, CrossEncoder evaluation).
- `results_raw.json`: Complete serialized metrics, query logs, per-query latencies, and hardware telemetry.
- `results_summary.csv`: Per-query side-by-side comparison with category, latencies, recall scores, and winners.
- `extract_examples.py`: Qualitative extraction helper script.
- `BENCHMARK_REPORT.md`: Comprehensive evaluation report.
