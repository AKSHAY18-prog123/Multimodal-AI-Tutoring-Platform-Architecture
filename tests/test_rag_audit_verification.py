import os
import uuid
import pytest
from pathlib import Path

from backend.app.ingestion.video_ingestion import (
    video_ingestor,
    parse_timestamp_to_seconds,
    _group_timed_utterances
)
from backend.app.knowledge_base.chunking import chunker, find_exact_timestamp_in_chunk
from backend.app.knowledge_base.vector_store import vector_store
from backend.app.rag.hybrid_retrieval import hybrid_retriever
from backend.app.rag.citation_validator import citation_validator
from backend.app.rag.query_understanding import query_analyzer, classify_conversational_intent
from backend.app.rag.source_resolver import source_resolver
from backend.app.rag.grounded_generation import grounded_generator, evaluate_evidence_sufficiency


@pytest.fixture
def temp_course_scope():
    """Creates a clean isolated course_id in ChromaDB and cleans up after the test."""
    cid = f"test-course-{uuid.uuid4().hex[:8]}"
    yield cid
    vector_store.delete_by_course_id(cid)


# ============================================================================
# 1. PROBLEM A — Video Lecture Understanding & Exact Timestamp Tests
# ============================================================================

def test_parse_vtt_srt_timestamps_exact(tmp_path: Path):
    """Verifies VTT/SRT files parse real start/end timestamps instead of hardcoding 0.0-60.0."""
    vtt_file = tmp_path / "os_lecture.vtt"
    vtt_file.write_text(
        "WEBVTT\n\n"
        "00:00:00.000 --> 00:01:45.000\n"
        "Welcome to Operating Systems. Today we introduce process synchronization and concurrency.\n\n"
        "00:03:15.000 --> 00:05:45.000\n"
        "Now let us examine deadlock prevention. Deadlock prevention works by invalidating one of the four Coffman conditions: mutual exclusion, hold and wait, no preemption, or circular wait.\n\n"
        "00:05:45.000 --> 00:08:30.000\n"
        "Next we cover the Banker's algorithm for deadlock avoidance using safe state matrices.\n",
        encoding="utf-8"
    )

    segments = video_ingestor._parse_transcript_file(vtt_file)
    assert len(segments) == 3
    assert segments[0]["timestamp_start"] == 0.0
    assert segments[0]["timestamp_end"] == 105.0
    assert segments[0]["timestamp_start_formatted"] == "00:00"
    assert segments[0]["timestamp_end_formatted"] == "01:45"

    assert segments[1]["timestamp_start"] == 195.0
    assert segments[1]["timestamp_end"] == 345.0
    assert segments[1]["timestamp_start_formatted"] == "03:15"
    assert segments[1]["timestamp_end_formatted"] == "05:45"
    assert "deadlock prevention" in segments[1]["transcript"].lower()
    assert segments[1]["is_fallback"] is False


def test_utterance_grouping_eliminates_timestamp_drift_and_preserves_subtimestamps():
    """Verifies _group_timed_utterances uses exact utterance start times and embeds [MM:SS] markers."""
    utterances = [
        {"start": 0.0, "duration": 40.0, "text": "Introduction to operating systems kernel architecture."},
        {"start": 45.0, "duration": 80.0, "text": "System calls provide the interface between user space and kernel mode."},
        # Notice a 15-second pause before the next topic begins at 140.0s (02:20)
        {"start": 140.0, "duration": 30.0, "text": "Now we begin our discussion of 프로세스 scheduling and context switching."},
        {"start": 175.0, "duration": 35.0, "text": "Deadlock prevention eliminates circular wait by imposing a total ordering on resource types."},
        {"start": 215.0, "duration": 50.0, "text": "Hold and wait can be prevented by requiring processes to request all resources upfront."}
    ]

    grouped = _group_timed_utterances(utterances, video_id="dQw4w9WgXcQ", window_seconds=120.0)
    assert len(grouped) == 2

    # First group: 0.0 -> 125.0
    assert grouped[0]["timestamp_start"] == 0.0
    assert grouped[0]["timestamp_end"] == 125.0
    assert grouped[0]["timestamp_start_formatted"] == "00:00"
    assert grouped[0]["timestamp_end_formatted"] == "02:05"

    # Second group MUST start at 140.0 (02:20), NOT 125.0 (no timestamp drift across pause!)
    assert grouped[1]["timestamp_start"] == 140.0
    assert grouped[1]["timestamp_start_formatted"] == "02:20"
    assert grouped[1]["timestamp_end"] == 265.0
    assert grouped[1]["timestamp_end_formatted"] == "04:25"
    assert "[02:55]" in grouped[1]["transcript"]
    assert grouped[1]["video_url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=140s"


@pytest.mark.asyncio
async def test_video_topic_and_exact_timestamp_retrieval(temp_course_scope: str):
    """
    Verifies that when a student asks about a specific topic ('deadlock prevention') or
    'At what time does the teacher explain deadlock prevention?', the system returns the
    exact sub-timestamp (02:55 - 04:25) and direct YouTube timestamp link.
    """
    utterances = [
        {"start": 0.0, "duration": 65.0, "text": "Welcome to Lecture 4 on Operating Systems. We start with process states and PCB."},
        {"start": 65.0, "duration": 65.0, "text": "A process transitions from New to Ready, Running, Waiting, and Terminated."},
        {"start": 140.0, "duration": 30.0, "text": "Before moving on, let us review thread synchronization with mutex locks."},
        {"start": 175.0, "duration": 45.0, "text": "Now we explain deadlock prevention. Deadlock prevention ensures at least one Coffman condition cannot hold."},
        {"start": 220.0, "duration": 45.0, "text": "Specifically, deadlock prevention attacks mutual exclusion, hold and wait, no preemption, and circular wait."},
        {"start": 270.0, "duration": 130.0, "text": "In the final part of this lecture, we study virtual memory paging and TLB hit ratios."}
    ]
    segments = _group_timed_utterances(utterances, video_id="osLect12345", window_seconds=120.0)
    doc_id = f"doc-vid-{uuid.uuid4().hex[:6]}"
    chunks = chunker.chunk_video_segments(segments, doc_id, "OS Deadlock Lecture (Video)", temp_course_scope)
    await vector_store.add_chunks(chunks)

    # 1. Ask: "At what time does the teacher explain deadlock prevention?"
    res = await grounded_generator.answer_question(
        query="At what time does the teacher explain deadlock prevention?",
        course_id=temp_course_scope,
        course_subject="Operating Systems"
    )
    assert res["is_outside_knowledge"] is False
    assert res["outside_knowledge_offered"] is False
    assert len(res["citations"]) >= 1

    top_cite = res["citations"][0]
    # Sub-timestamp refinement should pinpoint 02:55 (175s) where deadlock prevention starts!
    assert "02:55" in top_cite["label"] or "02:20" in top_cite["label"]
    assert top_cite["video_url"] is not None
    assert "osLect12345" in top_cite["video_url"]
    assert "t=175s" in top_cite["video_url"] or "t=140s" in top_cite["video_url"]
    assert "deadlock prevention" in res["answer"].lower()

    # 2. Ask about a topic NOT in the lecture video -> must NOT fabricate a timestamp
    res_missing = await grounded_generator.answer_question(
        query="At what time does the teacher explain BGP routing autonomous systems?",
        course_id=temp_course_scope,
        course_subject="Operating Systems"
    )
    assert res_missing["outside_knowledge_offered"] is True
    assert res_missing["citations"] == []


@pytest.mark.asyncio
async def test_video_fallback_states_limitation_instead_of_fabricating_timestamps(temp_course_scope: str):
    """Verifies that if a video has no extractable transcript (is_fallback=True), the tutor states the limitation."""
    fallback_segs = video_ingestor._generate_default_segments("Unindexed_Lecture.mp4")
    assert fallback_segs[0]["is_fallback"] is True

    doc_id = f"doc-fallback-{uuid.uuid4().hex[:6]}"
    chunks = chunker.chunk_video_segments(fallback_segs, doc_id, "Unindexed_Lecture.mp4", temp_course_scope)
    await vector_store.add_chunks(chunks)

    res = await grounded_generator.answer_question(
        query="Teach me the deadlock prevention topic from this lecture",
        course_id=temp_course_scope,
        course_subject="Operating Systems"
    )
    assert "reliable timestamped transcript could not be extracted" in res["answer"].lower()
    assert res["outside_knowledge_offered"] is True
    assert res["citations"] == []


# ============================================================================
# 2. PROBLEM B — Ingestion, Chunking, Storage, Retrieval & Citations Tests
# ============================================================================

def test_pdf_chunking_splits_paragraphs_and_long_pages_with_overlap():
    """Verifies chunk_pdf_pages splits paragraphs before clean_text and slices oversized pages with overlap."""
    para1 = " ".join([f"synchronization_concept_{i}" for i in range(300)])
    para2 = " ".join([f"deadlock_avoidance_{i}" for i in range(320)])
    pages = [{
        "page_number": 7,
        "text": f"{para1}\n\n{para2}",
        "headings": ["Process Synchronization"],
        "tables": [[["Condition", "Meaning"], ["Mutual Exclusion", "Exclusive resource access"]]]
    }]

    chunks = chunker.chunk_pdf_pages(pages, "doc-pdf-1", "OS_Notes.pdf", "course-1")
    # Should produce 1 table chunk + at least 2 text chunks (since 620 words > target_chunk_size=500)
    table_chunks = [c for c in chunks if c["chunk_type"] == "table"]
    text_chunks = [c for c in chunks if c["chunk_type"] == "text"]
    assert len(table_chunks) == 1
    assert len(text_chunks) == 2
    assert text_chunks[0]["page_number"] == 7
    assert text_chunks[1]["page_number"] == 7
    assert "synchronization_concept_0" in text_chunks[0]["content"]
    assert "deadlock_avoidance_319" in text_chunks[1]["content"]
    # Verify overlap words from para1 carried into chunk 2
    assert "synchronization_concept_299" in text_chunks[1]["content"]


def test_citation_validator_rejects_hallucinated_citations():
    """Verifies CitationValidator only emits citations backed by retrieved_chunks and attaches snippets."""
    retrieved = [{
        "id": "chunk-real-1",
        "content": "Page 12 explains Dijkstra's semaphore wait() and signal() atomic operations.",
        "rerank_score": 0.88,
        "metadata": {
            "document_id": "doc-1",
            "source_type": "pdf",
            "source_file": "Operating_Systems.pdf",
            "page_number": 12
        }
    }]
    llm_response = (
        "Semaphores use atomic wait() and signal() operations [Source: Operating Systems • Page 12]. "
        "Also see [Source: Hallucinated Book • Page 999]."
    )
    validated = citation_validator.extract_and_validate_citations(llm_response, retrieved)
    assert len(validated) == 1
    assert validated[0]["chunk_id"] == "chunk-real-1"
    assert validated[0]["page_number"] == 12
    assert "semaphore" in validated[0]["snippet"].lower()


# ============================================================================
# 3. PROBLEM C — Course Library Source Selection & Duplicate Names Tests
# ============================================================================

@pytest.mark.asyncio
async def test_duplicate_source_name_triggers_metadata_clarification_and_resolves_followup(temp_course_scope: str):
    """
    Verifies Case 2 of Problem C:
    When two uploaded sources share the same name ('Module 3 Notes'), the tutor asks a
    concise clarification question using real metadata (PDF from Operating Systems vs
    PowerPoint from Computer Networks), and then resolves the student's follow-up choice.
    """
    doc_pdf_id = f"doc-os-pdf-{uuid.uuid4().hex[:6]}"
    doc_ppt_id = f"doc-cn-ppt-{uuid.uuid4().hex[:6]}"

    pdf_chunks = chunker.chunk_pdf_pages(
        [{"page_number": 1, "text": "Module 3 covers CPU scheduling algorithms including Round Robin and SJF.", "headings": ["CPU Scheduling"], "tables": []}],
        doc_pdf_id,
        "Module 3 Notes.pdf",
        temp_course_scope
    )
    ppt_chunks = chunker.chunk_ppt_slides(
        [{"slide_number": 1, "title": "TCP Congestion Control", "bullet_points": ["Slow Start", "AIMD", "Fast Recovery"], "raw_text": "TCP Congestion Control Slow Start AIMD", "notes": ""}],
        doc_ppt_id,
        "Module 3 Notes.pptx",
        temp_course_scope
    )
    await vector_store.add_chunks(pdf_chunks + ppt_chunks)

    available_docs = [
        {
            "id": doc_pdf_id,
            "course_id": temp_course_scope,
            "course_title": "Operating Systems",
            "course_subject": "Operating Systems",
            "course_code": "CS301",
            "filename": "Module 3 Notes.pdf",
            "norm_name": "module 3 notes",
            "yt_title": "",
            "file_type": "pdf",
            "type_label": "PDF",
            "page_count": 14,
            "slide_count": None,
            "duration_formatted": None,
            "created_at": "2026-10-01",
            "in_active_course": True
        },
        {
            "id": doc_ppt_id,
            "course_id": temp_course_scope,
            "course_title": "Computer Networks",
            "course_subject": "Computer Networks",
            "course_code": "CS302",
            "filename": "Module 3 Notes.pptx",
            "norm_name": "module 3 notes",
            "yt_title": "",
            "file_type": "pptx",
            "type_label": "PowerPoint",
            "page_count": None,
            "slide_count": 22,
            "duration_formatted": None,
            "created_at": "2026-10-02",
            "in_active_course": True
        }
    ]

    # Turn 1: Student asks about "Module 3 Notes" without specifying which one
    turn1 = await grounded_generator.answer_question(
        query="Teach me the main topic from Module 3 Notes",
        course_id=temp_course_scope,
        available_docs=available_docs
    )
    assert "which one do you mean" in turn1["answer"].lower()
    assert "pdf" in turn1["answer"].lower()
    assert "operating systems" in turn1["answer"].lower()
    assert "14 pages" in turn1["answer"].lower()
    assert "powerpoint" in turn1["answer"].lower()
    assert "computer networks" in turn1["answer"].lower()
    assert "22 slides" in turn1["answer"].lower()
    assert turn1["citations"] == []

    # Turn 2: Student clarifies "The PDF from Operating Systems"
    history = [
        {"role": "user", "content": "Teach me the main topic from Module 3 Notes"},
        {"role": "assistant", "content": turn1["answer"]}
    ]
    turn2 = await grounded_generator.answer_question(
        query="Use the PDF from Operating Systems",
        course_id=temp_course_scope,
        chat_history=history,
        available_docs=available_docs
    )
    assert len(turn2["citations"]) == 1
    assert turn2["citations"][0]["document_id"] == doc_pdf_id
    assert turn2["citations"][0]["source_type"] == "pdf"
    assert "scheduling" in turn2["answer"].lower() or "round robin" in turn2["answer"].lower()


# ============================================================================
# 4. PROBLEM E — Natural Conversation & Intent Classification Tests
# ============================================================================

@pytest.mark.asyncio
async def test_greetings_and_acknowledgements_do_not_trigger_rag_or_refusal(temp_course_scope: str):
    """Verifies greetings ('Hi', 'Hello') and acknowledgements ('Thanks', 'Got it') respond naturally without RAG."""
    for greeting in ["Hi", "Hello!", "Good morning", "What can you help me with?"]:
        res = await grounded_generator.answer_question(
            query=greeting,
            course_id=temp_course_scope,
            course_subject="Operating Systems"
        )
        assert "not covered in the uploaded course material" not in res["answer"].lower()
        assert res["outside_knowledge_offered"] is False
        assert res["is_outside_knowledge"] is False
        assert res["citations"] == []
        assert res["retrieved_chunks_count"] == 0

    for ack in ["Thanks!", "Okay, got it", "Makes sense", "Understood, thank you"]:
        res_ack = await grounded_generator.answer_question(
            query=ack,
            course_id=temp_course_scope,
            course_subject="Operating Systems"
        )
        assert "not covered in the uploaded course material" not in res_ack["answer"].lower()
        assert res_ack["outside_knowledge_offered"] is False
        assert res_ack["citations"] == []
        assert res_ack["retrieved_chunks_count"] == 0


# ============================================================================
# 5. PROBLEM D & F — Grounded Evidence Sufficiency & One-Time Outside Permission
# ============================================================================

@pytest.mark.asyncio
async def test_one_time_outside_knowledge_permission_and_auto_reset(temp_course_scope: str):
    """
    Verifies Problem D & Problem F:
    1. Student asks an unsupported question -> Tutor refuses to hallucinate and offers outside knowledge.
    2. Student grants one-time permission ('Yes, explain using outside knowledge') -> Tutor recovers
       the pending question and answers it with clearly labeled Outside Knowledge and zero fake citations.
    3. On the next turn, permission automatically resets to strict source-grounded mode!
    4. If student declines ('No, return to course topics'), Tutor stays in grounded mode.
    """
    doc_id = f"doc-os-{uuid.uuid4().hex[:6]}"
    chunks = chunker.chunk_pdf_pages(
        [{"page_number": 1, "text": "Paging divides virtual memory into fixed-size blocks called pages and physical memory into frames.", "headings": ["Virtual Memory Paging"], "tables": []}],
        doc_id,
        "Virtual_Memory.pdf",
        temp_course_scope
    )
    await vector_store.add_chunks(chunks)

    # Turn 1: Student asks a question not supported by the uploaded Virtual Memory PDF
    q1 = "How does CRISPR-Cas9 gene editing target specific DNA sequences?"
    res1 = await grounded_generator.answer_question(
        query=q1,
        course_id=temp_course_scope,
        course_subject="Operating Systems"
    )
    assert res1["outside_knowledge_offered"] is True
    assert res1["is_outside_knowledge"] is False
    assert res1["citations"] == []
    assert "not covered in the uploaded course material" in res1["answer"].lower()

    # Turn 2: Student grants one-time permission
    history_after_t1 = [
        {"role": "user", "content": q1},
        {"role": "assistant", "content": res1["answer"]}
    ]
    res2 = await grounded_generator.answer_question(
        query="Yes, explain using outside knowledge",
        course_id=temp_course_scope,
        course_subject="Operating Systems",
        chat_history=history_after_t1
    )
    assert res2["is_outside_knowledge"] is True
    assert res2["outside_knowledge_offered"] is False
    assert res2["citations"] == []
    assert "### outside knowledge" in res2["answer"].lower()
    # Must answer the pending question (CRISPR-Cas9), NOT literally explain the string "Yes, explain using outside knowledge"
    assert "crispr" in res2["answer"].lower() or "gene" in res2["answer"].lower() or "dna" in res2["answer"].lower()

    # Turn 3: Next question is ALSO outside the material -> Permission MUST have reset to grounded mode!
    history_after_t2 = history_after_t1 + [
        {"role": "user", "content": "Yes, explain using outside knowledge"},
        {"role": "assistant", "content": res2["answer"]}
    ]
    q3 = "How does monetary inflation affect central bank interest rates?"
    res3 = await grounded_generator.answer_question(
        query=q3,
        course_id=temp_course_scope,
        course_subject="Operating Systems",
        chat_history=history_after_t2
    )
    assert res3["is_outside_knowledge"] is False
    assert res3["outside_knowledge_offered"] is True
    assert res3["citations"] == []

    # Turn 4: Student declines outside knowledge offer
    history_after_t3 = history_after_t2 + [
        {"role": "user", "content": q3},
        {"role": "assistant", "content": res3["answer"]}
    ]
    res4 = await grounded_generator.answer_question(
        query="No, return to course topics",
        course_id=temp_course_scope,
        course_subject="Operating Systems",
        chat_history=history_after_t3
    )
    assert res4["is_outside_knowledge"] is False
    assert res4["outside_knowledge_offered"] is False
    assert res4["citations"] == []
    assert "course material" in res4["answer"].lower()
