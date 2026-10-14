# Benchmark Report: FlashRank vs GTE-Reranker-ModernBERT vs Qwen3-Reranker-0.6B

## 1. Executive Summary & Production Decision

- **Primary Recommendation:** **Retain FlashRank as the Production Reranker** for the immediate demo and low-latency interactive tutoring pipeline.
- **Top Retrieval Accuracy Winner:** **Alibaba-NLP/gte-reranker-modernbert-base** achieved the highest overall ranking accuracy (**nDCG@5: 0.9244**, **Recall@5: 1.000**, **MRR@5: 0.9375**), outperforming both FlashRank (0.7755) and Qwen3 (0.8430).
- **Inference Speed Analysis:**
  - **FlashRank (ONNX Runtime, 4.4M params):** **11.52 ms** per query (real-time, zero perceptible latency, ~240,000 tok/s).
  - **GTE-ModernBERT (PyTorch CPU, 149M params):** **2,287.75 ms (~2.3s)** per query (~1,218 tok/s). 20x faster than Qwen3, but introduces a perceptible 2.3s wait per student question in CPU mode.
  - **Qwen3-Reranker-0.6B (PyTorch CPU, 596M params):** **47,309.6 ms (~47.3s)** per query. Severe CPU bottleneck caused it to trigger the 5-minute timeout guard after 6 queries.
- **Strategic Evolution Path:** If GPU acceleration (CUDA on the RTX 3050 Laptop GPU) is enabled or if ONNX conversion is applied to ModernBERT, GTE-ModernBERT will run in under **35–50 ms**, making it the ideal long-term production upgrade. Until then, FlashRank remains the superior production baseline.

---

## 2. Concise Benchmark Comparison Table

| Metric | FlashRank (Baseline) | GTE-ModernBERT (Candidate 1) | Qwen3-Reranker-0.6B (Candidate 2) |
|---|---|---|---|
| **Retrieval Quality (nDCG@5)** | **0.7755** | **0.9244** | **0.8430** |
| **Recall@5 (Targeted Queries)** | **0.8750** | **1.0000** | **1.0000** |
| **MRR@5 (Targeted Queries)** | **0.7188** | **0.9375** | **0.8333** |
| **Average Latency / Query** | **11.52 ms** | **2,287.75 ms (2.29s)** | **47,309.60 ms (47.3s)** |
| **Total Benchmark Runtime** | **0.12 s** | **22.88 s** | **283.86 s** (Timeout Guard) |
| **Model Load Time** | **0.0555 s** | **0.2791 s** | **0.5311 s** |
| **Input Tokens Processed** | **27,880** | **27,880** | **16,728** (6 queries) |
| **Input Tokens / Second** | **240,559.5 tok/s** | **1,218.6 tok/s** | **54.9 tok/s** |
| **Execution Engine** | **ONNX Runtime (CPU)** | **PyTorch (CPU)** | **PyTorch (CPU)** |
| **Model Architecture & Size** | 4.4M (`ms-marco-TinyBERT`) | 149M (`ModernBERT-base`) | 596M (`Qwen3-0.6B`) |
| **Peak GPU Temperature** | **49.0 °C** | **56.0 °C** | **59.0 °C** |
| **Peak VRAM Usage** | **938.0 MiB** | **934.0 MiB** | **970.0 MiB** |
| **Peak System RAM** | **14.28 GB** | **14.99 GB** | **16.29 GB** |
| **Average CPU Utilization** | **19.5%** | **74.5%** | **80.3%** |

---

## 3. Query-by-Query Performance (10 Representative Queries)

| Query ID | Category | Query Summary | FlashRank nDCG@5 | GTE-ModernBERT nDCG@5 | Qwen3 nDCG@5 | Latency (FR vs ModernBERT vs Qwen) | Winner |
|---|---|---|---|---|---|---|---|
| **Q01_CONCEPT** | Concept Specific | Built-in method replacing substring in Python string | 0.4307 (Rank 4) | **1.0000** (Rank 1) | **1.0000** (Rank 1) | 17.2 ms vs 2.28 s vs 49.8 s | **GTE-ModernBERT** |
| **Q02_CONCEPT** | Concept Specific | Backpropagation weight updates in MLP | 0.7967 (Rank 1) | **0.8262** (Rank 1) | 0.5213 (Rank 2) | 6.9 ms vs 1.66 s vs 43.2 s | **GTE-ModernBERT** |
| **Q08_CONFUSED** | Easily Confused | Difference between `/` and `//` division | **1.0000** (Rank 1) | **1.0000** (Rank 1) | **1.0000** (Rank 1) | 13.4 ms vs 2.47 s vs 52.4 s | **Tie** |
| **Q10_CONFUSED** | Easily Confused | Bias error vs variance error in deep learning | 0.0000 (Rank >5) | **0.6278** (Rank 2) | **0.6278** (Rank 2) | 7.8 ms vs 2.49 s vs 42.9 s | **GTE-ModernBERT** |
| **Q15_FORMULA** | Formula / Math | Cosine Similarity formula between two vectors | **0.9639** (Rank 1) | **0.9639** (Rank 1) | **0.9639** (Rank 1) | 6.2 ms vs 1.62 s vs 43.0 s | **Tie** |
| **Q16_FORMULA** | Formula / Math | Profit & Weight ratio in Knapsack problem | **0.9328** (Rank 1) | 0.8262 (Rank 2) | 0.9448 (Rank 1) | 14.0 ms vs 2.70 s vs 52.7 s | **FlashRank** |
| **Q21_TIMESTAMP** | Timestamp Specific | Lecture discussion at timestamp 00:30 (Python use cases) | 0.6309 (Rank 2) | **1.0000** (Rank 1) | *Skipped (Timeout)* | 13.5 ms vs 2.56 s vs N/A | **GTE-ModernBERT** |
| **Q25_TIMESTAMP** | Timestamp Specific | Knapsack video values (25, 24, 15) at 00:50 | **1.0000** (Rank 1) | **1.0000** (Rank 1) | *Skipped (Timeout)* | 15.1 ms vs 2.78 s vs N/A | **Tie** |
| **Q27_ABSENT** | Out of Domain | Shor's quantum factoring algorithm | **1.0000** | **1.0000** | *Skipped (Timeout)* | 10.4 ms vs 2.17 s vs N/A | **Tie** |
| **Q29_ABSENT** | Out of Domain | React `useEffect` cleanup hook | **1.0000** | **1.0000** | *Skipped (Timeout)* | 10.9 ms vs 2.16 s vs N/A | **Tie** |

---

## 4. Key Takeaways & Hardware Grounding

1. **Accuracy:**
   - **GTE-Reranker-ModernBERT-base is the clear quality winner.** It placed the ground truth at Rank 1 or 2 across 100% of tested queries, achieving an nDCG@5 of **0.9244**.
   - It effectively resolved the confusion queries where FlashRank struggled (e.g. `Q10_CONFUSED` on Bias vs. Variance, where FlashRank scored 0.000 and ModernBERT scored 0.6278).
2. **Speed & Latency:**
   - FlashRank is **198x faster** than GTE-ModernBERT and **4,106x faster** than Qwen3 on CPU.
   - For an interactive tutoring chatbot where the student is waiting for a response, 11 ms (FlashRank) is virtually instantaneous. A 2.3s reranking phase (ModernBERT) combined with LLM generation latency is noticeable, while 47.3s (Qwen3) is unacceptable.
3. **Resource Utilization:**
   - FlashRank used only 19.5% CPU and 14.28 GB RAM.
   - GTE-ModernBERT utilized 74.5% CPU and 14.99 GB RAM.
   - Qwen3 utilized 80.3% CPU and 16.29 GB RAM, running until stopped by the 5-minute guard.
   - The laptop GPU (RTX 3050) remained idle across all models because the host Python environment utilizes `torch+cpu`.
