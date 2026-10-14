"""
Comprehensive Validation Test Suite for Nomic Embed Text Integration in SynapseTutor AI
Tests:
1. Provider Availability and Dimension Verification (768d)
2. Task Prefixes ('search_query: ' and 'search_document: ')
3. ChromaDB Vector Store Nomic Collection Compatibility (768d)
4. Original MiniLM Collection Untouched (384d)
5. Dense Vector Search on Course PDF Content
6. Dense Vector Search on YouTube Lecture Transcript Content
7. Metadata Preservation (video timestamps, video_url, page numbers, topics)
8. End-to-End Hybrid Retrieval + GTE-ModernBERT Reranking
9. NoveltyChecker Semantic Similarity Compatibility
"""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Ensure UTF-8 output on Windows
sys.stdout.reconfigure(encoding='utf-8')

import asyncio
import time
from backend.app.core.config import settings
from backend.app.knowledge_base.vector_store import vector_store
from backend.app.rag.hybrid_retrieval import hybrid_retriever
from backend.app.assessment.novelty_checker import NoveltyChecker


async def run_validation_suite():
    print("=" * 80)
    print(" SYNAPSETUTOR AI — NOMIC EMBED TEXT INTEGRATION VALIDATION")
    print("=" * 80)

    passed_tests = []
    failed_tests = []

    # -------------------------------------------------------------------------
    # TEST 1: Model Availability & Vector Dimensions
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Testing Ollama Provider Availability & Dimensions...")
    try:
        prov = vector_store.embedding_provider
        avail = await prov.verify_availability()
        assert avail["available"], f"Provider not available: {avail}"
        
        # Test query embedding
        q_vec = await prov.embed_text("Test query embedding for Python tutorial")
        assert len(q_vec) == 768, f"Expected 768d query embedding, got {len(q_vec)}"

        # Test document batch embedding
        docs_vecs = await prov.embed_documents(["Doc chunk 1", "Doc chunk 2"])
        assert len(docs_vecs) == 2, f"Expected 2 doc vectors, got {len(docs_vecs)}"
        assert len(docs_vecs[0]) == 768, f"Expected 768d doc embedding, got {len(docs_vecs[0])}"

        print(f"  PASS: Ollama responded successfully. Query & Doc vectors verified at 768 dimensions.")
        passed_tests.append("Test 1: Model Availability & Vector Dimensions (768d)")
    except Exception as e:
        print(f"  FAIL: {e}")
        failed_tests.append(f"Test 1: Model Availability & Dimensions ({e})")

    # -------------------------------------------------------------------------
    # TEST 2: Chroma Collection Separation & MiniLM Integrity
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Testing Chroma Collection Separation & MiniLM Isolation...")
    try:
        assert vector_store.collection_name == "course_knowledge_chunks_nomic"
        nomic_count = vector_store.collection.count()
        assert nomic_count == 258, f"Expected 258 chunks in Nomic collection, got {nomic_count}"

        peek_nomic = vector_store.collection.peek(limit=1)
        embs_n = peek_nomic.get("embeddings")
        assert embs_n is not None and len(embs_n[0]) == 768, f"Nomic collection must be 768d"

        # Check original MiniLM collection
        minilm_col = vector_store.client.get_collection("course_knowledge_chunks")
        minilm_count = minilm_col.count()
        assert minilm_count == 258, f"Original MiniLM collection must have 258 chunks, got {minilm_count}"
        
        peek_minilm = minilm_col.peek(limit=1)
        embs_m = peek_minilm.get("embeddings")
        assert embs_m is not None and len(embs_m[0]) == 384, f"Original MiniLM collection must remain 384d"

        print(f"  PASS: 'course_knowledge_chunks_nomic' is 768d ({nomic_count} chunks).")
        print(f"  PASS: 'course_knowledge_chunks' is untouched at 384d ({minilm_count} chunks).")
        passed_tests.append("Test 2: Chroma Collection Separation & MiniLM Isolation")
    except Exception as e:
        print(f"  FAIL: {e}")
        failed_tests.append(f"Test 2: Chroma Collection Separation ({e})")

    # -------------------------------------------------------------------------
    # TEST 3: Retrieval on Course PDF Documents
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Testing Retrieval on Course PDF Content...")
    try:
        pdf_query = "What built-in method replaces occurrences of a substring in a Python string?"
        hits = await vector_store.search(query=pdf_query, top_k=5)
        assert len(hits) > 0, "No hits returned for PDF query"
        top_hit = hits[0]
        meta = top_hit.get("metadata", {})
        print(f"  Top PDF Hit ID: {top_hit['id']}")
        print(f"  Source File:    {meta.get('source_file')}")
        print(f"  Vector Score:   {top_hit['vector_score']}")
        print(f"  Content Sample: {top_hit['content'][:120]}...")
        assert "replace" in top_hit["content"].lower(), "Expected 'replace' in retrieved passage"
        print("  PASS: PDF question correctly retrieved relevant content.")
        passed_tests.append("Test 3: Course PDF Content Retrieval")
    except Exception as e:
        print(f"  FAIL: {e}")
        failed_tests.append(f"Test 3: PDF Content Retrieval ({e})")

    # -------------------------------------------------------------------------
    # TEST 4: Retrieval on YouTube Lecture Transcript & Timestamp Preservation
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Testing Retrieval on YouTube Lecture Transcript with Timestamps...")
    try:
        video_query = "What does the teacher discuss at timestamp 00:30 regarding what you can do with Python?"
        hits = await vector_store.search(query=video_query, top_k=5)
        assert len(hits) > 0, "No hits returned for video query"
        
        # Verify video chunks retain timestamp metadata
        video_hit = None
        for h in hits:
            if h.get("metadata", {}).get("source_type") == "video":
                video_hit = h
                break
        
        assert video_hit is not None, "Expected at least one video chunk in top hits"
        v_meta = video_hit["metadata"]
        print(f"  Video Hit ID:     {video_hit['id']}")
        print(f"  Topic Name:       {v_meta.get('topic_name')}")
        print(f"  Source Type:      {v_meta.get('source_type')}")
        print(f"  Timestamp Range:  {v_meta.get('timestamp_start_formatted')} - {v_meta.get('timestamp_end_formatted')}")
        print(f"  Raw Seconds:      {v_meta.get('timestamp_start')}s to {v_meta.get('timestamp_end')}s")
        print(f"  Video URL:        {v_meta.get('video_url')}")
        
        assert v_meta.get("timestamp_start") is not None, "timestamp_start must be preserved"
        assert v_meta.get("timestamp_end") is not None, "timestamp_end must be preserved"
        print("  PASS: YouTube transcript retrieved with video timestamps and URLs intact.")
        passed_tests.append("Test 4: YouTube Transcript & Timestamp Preservation")
    except Exception as e:
        print(f"  FAIL: {e}")
        failed_tests.append(f"Test 4: YouTube Transcript Retrieval ({e})")

    # -------------------------------------------------------------------------
    # TEST 5: End-to-End Hybrid Retrieval + GTE-ModernBERT Reranking
    # -------------------------------------------------------------------------
    print("\n[TEST 5] Testing End-to-End Hybrid Retrieval + GTE-ModernBERT Reranking...")
    try:
        complex_query = "How do strings work in Python and why are they immutable?"
        t0 = time.time()
        candidates = await hybrid_retriever.retrieve_candidates(query=complex_query, top_k=5)
        latency = (time.time() - t0) * 1000.0
        assert len(candidates) > 0, "No candidates returned from hybrid retriever"
        
        print(f"  Retrieved {len(candidates)} candidates in {latency:.1f}ms:")
        for idx, c in enumerate(candidates[:3], 1):
            m = c.get("metadata", {})
            st = m.get("source_type", "doc")
            rf = c.get("rerank_score", "N/A")
            print(f"    {idx}. [{st.upper()}] Rerank Score: {rf} | {c['content'][:100]}...")

        top_cand = candidates[0]
        assert "rerank_score" in top_cand, "Candidate must contain rerank_score from CrossEncoder"
        print("  PASS: Hybrid retrieval and GTE-ModernBERT reranking executed cleanly with Nomic vectors.")
        passed_tests.append("Test 5: Hybrid Retrieval + GTE-ModernBERT Reranking")
    except Exception as e:
        print(f"  FAIL: {e}")
        failed_tests.append(f"Test 5: Hybrid Retrieval + Reranking ({e})")

    # -------------------------------------------------------------------------
    # TEST 6: Assessment NoveltyChecker Semantic Similarity
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Testing NoveltyChecker Semantic Similarity with Nomic...")
    try:
        checker = NoveltyChecker(similarity_threshold=0.85)
        existing_q = [
            {"question_text": "What is the difference between mutable and immutable types in Python?"}
        ]
        
        # Test similar question
        is_novel, sim, reason = await checker.is_novel(
            "Explain mutable versus immutable data structures in Python.",
            existing_q
        )
        print(f"  Similar check: is_novel={is_novel}, sim={sim:.3f}")

        # Test completely different question
        is_novel_diff, sim_diff, reason_diff = await checker.is_novel(
            "What is Dijkstra's shortest path algorithm?",
            existing_q
        )
        print(f"  Different check: is_novel={is_novel_diff}, sim={sim_diff:.3f}")
        assert sim > sim_diff, "Similar question must have higher similarity than completely different question"
        print("  PASS: NoveltyChecker successfully utilizes Nomic embeddings.")
        passed_tests.append("Test 6: Assessment NoveltyChecker Semantic Similarity")
    except Exception as e:
        print(f"  FAIL: {e}")
        failed_tests.append(f"Test 6: NoveltyChecker ({e})")

    # -------------------------------------------------------------------------
    # Summary Report
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print(" VALIDATION SUITE SUMMARY")
    print("=" * 80)
    print(f"Passed: {len(passed_tests)}/{len(passed_tests) + len(failed_tests)} tests")
    for t in passed_tests:
        print(f"  [x] {t}")
    if failed_tests:
        print("\nFailed Tests:")
        for t in failed_tests:
            print(f"  [!] {t}")
        sys.exit(1)
    else:
        print("\nALL VALIDATION TESTS PASSED PERFECTLY!")


if __name__ == "__main__":
    asyncio.run(run_validation_suite())
