# Grounded Multimodal RAG Pipeline Specification

## Pipeline Flow

```
USER QUESTION
      │
      ▼
1. Query Understanding & Scope Detector
   ├─ Detects Intent (conceptual, numerical, definition, chitchat)
   ├─ Identifies target concept keywords
   └─ Off-Material Detection (Section 37 Refusal Benchmark)
      │
      ▼
2. Hybrid Multimodal Retrieval
   ├─ Dense Vector Search: ChromaDB with normalized embeddings
   ├─ Lexical Keyword Search: BM25-style frequency scoring
   └─ Metadata Filter: course_id, source_type
      │
      ▼
3. Hybrid Reranking
   └─ Combines semantic vector score (60%) + lexical term density (30%) + exact phrase match bonus (10%)
      │
      ▼
4. Grounded Context Construction
   └─ Prepends explicit Source Headers: [SOURCE #N | Type | File | Page/Slide/Timestamp]
      │
      ▼
5. Learner & Memory Context Injection
   ├─ Non-sensitive Learning Behavior Profile (scaffolding style, math preference)
   └─ Relevant past Episodic Memories (e.g. past misconception resolution)
      │
      ▼
6. LLM Generation
   └─ Strict instruction: Answer grounded in provided source chunks; cite exact sources in brackets.
      │
      ▼
7. Citation Validation & Verification Gate
   ├─ Scans citations against retrieved source anchors
   └─ Strips hallucinated citations; builds UI clickable citation chips
      │
      ▼
RESPONSE EMISSION (Answer + Validated Citations + Suggested Follow-ups)
```

## Off-Material Refusal Mechanics
When a question is outside the syllabus:
- The system returns:
  > *"This topic is not covered in the uploaded course material. Would you like an outside-knowledge explanation?"*
- If the user explicitly opts in, the response is clearly badged:
  > `### Outside Knowledge (Not from uploaded course material)`
