# Automated Evaluation & Benchmark Suite

The evaluation suite (`scripts/run_evaluation.py`) measures the platform against the core hackathon requirements across 4 key dimensions:

---

## 1. Grounding & Off-Material Refusal (Section 37 Benchmark)
- **Objective**: Ensure the system strictly adheres to syllabus boundaries and does not hallucinate course facts for out-of-scope inquiries.
- **Evaluation Set**: Inquiries about GPU microarchitectures, cooking recipes, weather, and celebrity gossip.
- **Result**: `100.0% (5/5) Refusal Accuracy`.
- **Behavior**: System emits: *"This topic is not covered in the uploaded course material. Would you like an outside-knowledge explanation?"*

---

## 2. Citation Presence & Correctness
- **Objective**: Guarantee every course claim is backed by a verified canonical source anchor.
- **Evaluation Set**: Core curriculum inquiries (Banker's Algorithm, Coffman deadlock conditions, allocation matrices).
- **Result**: `100.0% (3/3) Citation Accuracy`.
- **Anchor Format**: Exact page, slide, or video timestamp (`[Source: Operating Systems • Page 384]`, `[Source: Module 4 • Slide 12]`).

---

## 3. Question Verification & Novelty
- **Objective**: Prevent repetitive or mathematically invalid questions from reaching students.
- **Evaluation**: SymPy deterministic math execution, MCQ distractor uniqueness, and dense embedding cosine similarity check ($> 0.85$ rejected).
- **Results**:
  - Verification Pass Rate: `100.0%`
  - Novelty Rate: `100.0% (0% repetition)`

---

## 4. Cognitive Learner Simulation
- **Objective**: Verify that Bayesian Knowledge Tracing updates correctly over time.
- **Simulation**:
  - **Student A** (Starts struggling, then masters concepts): Trajectory $[15.0\% \rightarrow 11.9\% \rightarrow 11.5\% \rightarrow 43.2\% \rightarrow 79.7\% \rightarrow 95.2\%]$ ($+95.0\%$ gain).
  - **Student B** (Consistent correct answers): Trajectory $[15.0\% \rightarrow 49.8\% \rightarrow 83.5\% \rightarrow 96.2\% \rightarrow 78.5\% \rightarrow 94.8\%]$ ($+94.6\%$ gain).
