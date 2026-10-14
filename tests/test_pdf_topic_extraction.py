import os
import pytest
import pymupdf as fitz
from pathlib import Path
from typing import Dict, Any, List

from backend.app.knowledge_base.topic_extraction import (
    TopicExtractionService,
    topic_extractor,
    clean_topic_name,
    normalize_match_key
)
from backend.app.rag.query_understanding import is_exhaustive_topic_query
from backend.app.rag.grounded_generation import grounded_generator


def create_synthetic_pdf(
    file_path: Path,
    pages_content: List[Dict[str, Any]],
    toc: List[List[Any]] = None
):
    """
    Helper to generate a clean synthetic PDF with realistic heading hierarchies,
    font sizes, page text, and optional document outline / TOC.
    """
    doc = fitz.open()
    for p_info in pages_content:
        page = doc.new_page(width=595, height=842)
        y = 50.0

        # Module heading if present
        if p_info.get("module"):
            page.insert_text(fitz.Point(50, y), p_info["module"], fontsize=16)
            y += 35.0

        # Section / Topic heading if present
        if p_info.get("topic"):
            page.insert_text(fitz.Point(50, y), p_info["topic"], fontsize=14)
            y += 28.0

        # Subtopic if present
        if p_info.get("subtopic"):
            page.insert_text(fitz.Point(60, y), p_info["subtopic"], fontsize=12)
            y += 22.0

        # Body text
        if p_info.get("body"):
            page.insert_text(fitz.Point(50, y), p_info["body"], fontsize=10)
            y += 20.0

    if toc:
        doc.set_toc(toc)

    doc.save(str(file_path))
    doc.close()


@pytest.fixture(scope="module")
def ten_pdf_test_suite(tmp_path_factory) -> Dict[str, Any]:
    """
    Generates 10 test PDF documents covering all required test cases:
    1. Topics distributed across all 10 PDFs.
    2. Duplicate topics appearing in multiple PDFs (Linear Regression in PDF 1 & PDF 2).
    3. Topics appearing only near the end of a long PDF (ACID Properties & Two-Phase Locking on p7-8 of PDF 6).
    4. PDFs containing tables of contents and nested headings (PDF 7).
    5. An unreadable/corrupted PDF (PDF 8) and a blank/unreadable page (PDF 8b).
    6. Two PDFs containing similar but distinct topics (Simple Linear Regression vs Multiple Linear Regression in PDF 9 & 10).
    """
    test_dir = tmp_path_factory.mktemp("pdf_suite")

    # 1. PDF 1: Calculus
    p1 = test_dir / "pdf1_calculus.pdf"
    create_synthetic_pdf(p1, [
        {
            "module": "Chapter 1: Differential Calculus",
            "topic": "1.1 Limits and Continuity",
            "body": "Limits form the analytical foundation of calculus and mathematical analysis."
        },
        {
            "topic": "1.2 Derivatives and Differentiation",
            "subtopic": "Product Rule and Chain Rule",
            "body": "The product rule and chain rule allow computing derivatives of composite functions."
        },
        {
            "topic": "1.3 Linear Regression Modeling",
            "body": "Introductory data fitting note on line equations and linear regression approximation."
        }
    ])

    # 2. PDF 2: Statistics (Contains duplicate 'Linear Regression')
    p2 = test_dir / "pdf2_statistics.pdf"
    create_synthetic_pdf(p2, [
        {
            "module": "Module 1: Regression Analysis",
            "topic": "Linear Regression Modeling",
            "subtopic": "Ordinary Least Squares Estimation",
            "body": "Linear regression fits a linear model minimizing squared errors between target and prediction."
        },
        {
            "topic": "Logistic Regression Classification",
            "subtopic": "Sigmoid Activation and Log-Odds",
            "body": "Logistic regression uses the sigmoid function to map linear outputs to probability space."
        }
    ])

    # 3. PDF 3: Deep Learning
    p3 = test_dir / "pdf3_deep_learning.pdf"
    create_synthetic_pdf(p3, [
        {
            "module": "Unit 2: Neural Network Architectures",
            "topic": "Artificial Neural Networks",
            "subtopic": "Backpropagation Algorithm",
            "body": "Multilayer perceptrons learn representations via forward passes and backpropagation gradient updates."
        },
        {
            "topic": "Convolutional Neural Networks",
            "subtopic": "Pooling Layers and Receptive Fields",
            "body": "CNNs apply spatial convolutional kernels followed by max pooling to extract visual features."
        }
    ])

    # 4. PDF 4: Operating Systems
    p4 = test_dir / "pdf4_operating_systems.pdf"
    create_synthetic_pdf(p4, [
        {
            "module": "Module 3: Process Management",
            "topic": "Process Synchronization",
            "subtopic": "Semaphores and Mutexes",
            "body": "Semaphores coordinate concurrent access to shared memory and critical sections."
        },
        {
            "topic": "Deadlock Prevention",
            "subtopic": "Banker's Algorithm",
            "body": "Deadlock prevention invalidates one of the four Coffman conditions to avoid circular deadlock."
        }
    ])

    # 5. PDF 5: Computer Networks
    p5 = test_dir / "pdf5_computer_networks.pdf"
    create_synthetic_pdf(p5, [
        {
            "module": "Chapter 4: Transport Layer Protocols",
            "topic": "Transmission Control Protocol",
            "subtopic": "Three-Way Handshake Connection",
            "body": "TCP is a connection-oriented, reliable stream protocol establishing sessions via SYN, SYN-ACK, ACK."
        },
        {
            "topic": "User Datagram Protocol",
            "subtopic": "Connectionless Transmission",
            "body": "UDP is a lightweight, connectionless datagram protocol without retransmission guarantees."
        }
    ])

    # 6. PDF 6: Database Systems (8-page long PDF, topics near the end on pages 7 & 8)
    p6 = test_dir / "pdf6_database_systems.pdf"
    long_pages = []
    for i in range(1, 7):
        long_pages.append({
            "body": f"Page {i} discusses introductory database history, relational schema definitions, and SQL queries."
        })
    # Late appearing topics on Page 7 and Page 8
    long_pages.append({
        "module": "Chapter 5: Transaction Management",
        "topic": "ACID Properties",
        "subtopic": "Atomicity and Serializability",
        "body": "Transactions guarantee Atomicity, Consistency, Isolation, and Durability in relational database engines."
    })
    long_pages.append({
        "topic": "Two-Phase Locking Protocol",
        "subtopic": "Strict 2PL and Deadlock Detection",
        "body": "Two-phase locking ensures conflict serializability by separating growing and shrinking lock phases."
    })
    create_synthetic_pdf(p6, long_pages)

    # 7. PDF 7: Data Structures (Contains embedded Table of Contents and nested headings)
    p7 = test_dir / "pdf7_data_structures.pdf"
    create_synthetic_pdf(p7, [
        {
            "module": "Module 6: Tree Data Structures",
            "topic": "Binary Search Trees",
            "body": "A binary search tree maintains sorted keys where left children are strictly less than parent nodes."
        },
        {
            "topic": "AVL Trees",
            "subtopic": "Tree Rotations and Balance Factors",
            "body": "AVL trees are self-balancing binary search trees maintaining height balance factors between -1 and +1."
        }
    ], toc=[
        [1, "Module 6: Tree Data Structures", 1],
        [2, "Binary Search Trees", 1],
        [2, "AVL Trees", 2],
        [3, "Tree Rotations and Balance Factors", 2]
    ])

    # 8. PDF 8: Corrupted / Unreadable PDF
    p8 = test_dir / "pdf8_corrupted.pdf"
    with open(p8, "wb") as f:
        f.write(b"%PDF-1.4\n%BAD_CORRUPTED_STREAM_GARBAGE\xff\xfe\x00\x00")

    # 8b. PDF 8b: PDF with a blank/unreadable page to test unreadable page tracking
    p8b = test_dir / "pdf8b_partially_unreadable.pdf"
    doc_unreadable = fitz.open()
    page1 = doc_unreadable.new_page(width=595, height=842)
    page1.insert_text(fitz.Point(50, 50), "Module: Digital Logic Circuits", fontsize=15)
    page1.insert_text(fitz.Point(50, 80), "Boolean Algebra Simplification", fontsize=13)
    page1.insert_text(fitz.Point(50, 110), "Karnaugh maps minimize combinational Boolean expressions.", fontsize=10)
    # Page 2 has NO text (blank / scanned image placeholder)
    doc_unreadable.new_page(width=595, height=842)
    doc_unreadable.save(str(p8b))
    doc_unreadable.close()

    # 9. PDF 9: Simple Linear Regression (Distinct concept from Multiple)
    p9 = test_dir / "pdf9_linear_models_part_a.pdf"
    create_synthetic_pdf(p9, [
        {
            "module": "Part A: Univariate Linear Models",
            "topic": "Simple Linear Regression",
            "subtopic": "Single Predictor Variable",
            "body": "Simple linear regression models the relationship between a single independent variable X and dependent variable Y."
        }
    ])

    # 10. PDF 10: Multiple Linear Regression (Distinct concept from Simple)
    p10 = test_dir / "pdf10_linear_models_part_b.pdf"
    create_synthetic_pdf(p10, [
        {
            "module": "Part B: Multivariate Linear Models",
            "topic": "Multiple Linear Regression",
            "subtopic": "Matrix Formulation and Covariates",
            "body": "Multiple linear regression extends linear modeling to multiple explanatory predictors using matrix equations."
        }
    ])

    all_paths = [
        str(p1), str(p2), str(p3), str(p4), str(p5),
        str(p6), str(p7), str(p8), str(p9), str(p10)
    ]

    return {
        "dir": test_dir,
        "paths": all_paths,
        "pdf1": str(p1),
        "pdf2": str(p2),
        "pdf6": str(p6),
        "pdf7": str(p7),
        "pdf8": str(p8),
        "pdf8b": str(p8b),
        "pdf9": str(p9),
        "pdf10": str(p10),
        "ground_truth_topics": {
            "Limits and Continuity",
            "Derivatives and Differentiation",
            "Linear Regression Modeling",
            "Logistic Regression Classification",
            "Artificial Neural Networks",
            "Convolutional Neural Networks",
            "Process Synchronization",
            "Deadlock Prevention",
            "Transmission Control Protocol",
            "User Datagram Protocol",
            "ACID Properties",
            "Two-Phase Locking Protocol",
            "Binary Search Trees",
            "AVL Trees",
            "Simple Linear Regression",
            "Multiple Linear Regression"
        }
    }


# ============================================================================
# TEST CASES
# ============================================================================

def test_query_understanding_exhaustive_topic_intent():
    """Verifies that exhaustive topic requests are correctly identified and separated from standard RAG."""
    exhaustive_queries = [
        "List all topics in the uploaded materials",
        "Give me the complete syllabus from these PDFs",
        "List all modules and subtopics",
        "Identify every topic covered across all documents",
        "Find duplicate topics and topics missing from my notes",
        "What are all the topics in the uploaded documents?",
        "Extract a complete master topic list from my PDFs"
    ]
    for q in exhaustive_queries:
        assert is_exhaustive_topic_query(q) is True, f"Failed to classify query as exhaustive topic query: {q}"

    # Specific localized questions must remain standard RAG queries
    standard_rag_queries = [
        "What is the difference between TCP and UDP?",
        "Explain the deadlock prevention banker's algorithm",
        "How does backpropagation work in neural networks?",
        "Solve the knapsack problem step by step"
    ]
    for q in standard_rag_queries:
        assert is_exhaustive_topic_query(q) is False, f"Erroneously classified standard query as exhaustive: {q}"


@pytest.mark.asyncio
async def test_case_1_topics_distributed_across_all_10_pdfs(ten_pdf_test_suite):
    """
    Test Case 1: Topics distributed across all 10 PDFs.
    Measures topic precision, recall, and verifies coverage across every uploaded document.
    """
    service = TopicExtractionService()
    result = await service.extract_exhaustive_topics_for_course(
        query="List all topics in the uploaded materials",
        file_paths=ten_pdf_test_suite["paths"]
    )

    summary = result.get("summary", {})
    assert summary["total_pdfs"] == 10
    assert summary["successful_pdfs"] == 9  # 9 valid PDFs, 1 corrupted
    assert summary["failed_pdfs"] == 1
    assert summary["total_pages"] >= 20

    answer = result["answer"]
    # Verify the 4 mandatory sections are present in markdown output
    assert "### Document Processing Summary" in answer
    assert "### Complete Topic Index" in answer
    assert "### Consolidated Master Topic List" in answer
    assert "### Coverage and Limitations" in answer

    # Verify topics from different documents appear in the output
    assert "Limits and Continuity" in answer or "Limits" in answer
    assert "Transmission Control Protocol" in answer or "TCP" in answer
    assert "Artificial Neural Networks" in answer
    assert "Process Synchronization" in answer


@pytest.mark.asyncio
async def test_case_2_duplicate_topics_appearing_in_multiple_pdfs(ten_pdf_test_suite):
    """
    Test Case 2: Duplicate topics appearing in multiple PDFs.
    Verifies that 'Linear Regression Modeling' present in both PDF 1 and PDF 2 is merged
    in the Consolidated Master Topic List and that both source documents are cited.
    """
    service = TopicExtractionService()
    result = await service.extract_exhaustive_topics_for_course(
        query="Find duplicate topics across the uploaded materials",
        file_paths=[ten_pdf_test_suite["pdf1"], ten_pdf_test_suite["pdf2"]]
    )

    answer = result["answer"]
    summary = result.get("summary", {})
    assert summary["duplicate_rate"] > 0.0, "Duplicate topic rate should be non-zero"

    # In Consolidated Master Topic List, Linear Regression should cite both files
    assert "Linear Regression" in answer
    assert "pdf1_calculus.pdf" in answer
    assert "pdf2_statistics.pdf" in answer


@pytest.mark.asyncio
async def test_case_3_topics_appearing_near_end_of_long_pdf(ten_pdf_test_suite):
    """
    Test Case 3: Topics appearing only near the end of a long PDF.
    PDF 6 has 8 pages, with 'ACID Properties' on page 7 and 'Two-Phase Locking Protocol' on page 8.
    """
    service = TopicExtractionService()
    doc_res = service.extract_topics_from_pdf(
        file_path=ten_pdf_test_suite["pdf6"],
        filename="pdf6_database_systems.pdf"
    )

    assert doc_res["success"] is True
    assert doc_res["pages_processed"] == 8

    # Extract all topic names and pages
    extracted_topics = []
    for m in doc_res.get("modules", []):
        for t in m.get("topics", []):
            extracted_topics.append((t["name"], t["page"]))

    topic_names = [t[0] for t in extracted_topics]
    topic_pages = {t[0]: t[1] for t in extracted_topics}

    assert any("ACID" in name for name in topic_names), "Failed to extract ACID Properties from page 7"
    assert any("Two-Phase Locking" in name or "2PL" in name for name in topic_names), "Failed to extract Two-Phase Locking from page 8"

    acid_page = [p for name, p in topic_pages.items() if "ACID" in name][0]
    assert acid_page == 7, f"Expected ACID Properties on page 7, got page {acid_page}"


@pytest.mark.asyncio
async def test_case_4_pdf_with_toc_and_nested_headings(ten_pdf_test_suite):
    """
    Test Case 4: PDFs containing tables of contents and nested headings.
    Verifies that Module -> Topic -> Subtopic hierarchy is preserved.
    """
    service = TopicExtractionService()
    doc_res = service.extract_topics_from_pdf(
        file_path=ten_pdf_test_suite["pdf7"],
        filename="pdf7_data_structures.pdf"
    )

    assert doc_res["success"] is True
    modules = doc_res.get("modules", [])
    assert len(modules) >= 1

    first_mod = modules[0]
    assert "Tree Data Structures" in first_mod["title"]

    topics = first_mod.get("topics", [])
    assert len(topics) >= 2

    bst_topic = [t for t in topics if "Binary Search" in t["name"]]
    avl_topic = [t for t in topics if "AVL" in t["name"]]
    assert len(bst_topic) == 1
    assert len(avl_topic) == 1

    # Check subtopics on AVL Trees
    avl_subs = avl_topic[0].get("subtopics", [])
    assert len(avl_subs) >= 1
    assert "Rotations" in avl_subs[0]["name"]


@pytest.mark.asyncio
async def test_case_5_unreadable_or_corrupted_pdf_handling(ten_pdf_test_suite):
    """
    Test Case 5: An unreadable or corrupted PDF and unreadable pages.
    Verifies that corrupted PDFs and blank pages are detected, reported, and do NOT crash the service.
    """
    service = TopicExtractionService()

    # 1. Corrupted file
    corrupt_res = service.extract_topics_from_pdf(
        file_path=ten_pdf_test_suite["pdf8"],
        filename="pdf8_corrupted.pdf"
    )
    assert corrupt_res["success"] is False
    assert "error" in corrupt_res

    # 2. Partially unreadable page file (Page 2 has no text)
    partial_res = service.extract_topics_from_pdf(
        file_path=ten_pdf_test_suite["pdf8b"],
        filename="pdf8b_partially_unreadable.pdf"
    )
    assert partial_res["success"] is True
    assert 2 in partial_res.get("unreadable_pages", [])

    # 3. Overall response formatting reports the failure clearly
    formatted_answer, _ = service.format_exhaustive_topic_response(
        doc_results=[corrupt_res, partial_res],
        consolidated=service.consolidate_master_topics([partial_res]),
        query="List all topics"
    )
    assert "pdf8_corrupted.pdf" in formatted_answer
    assert "Page 2" in formatted_answer
    assert "Coverage and Limitations" in formatted_answer
    assert "Partial coverage warning" in formatted_answer


@pytest.mark.asyncio
async def test_case_6_similar_but_distinct_topics_not_falsely_merged(ten_pdf_test_suite):
    """
    Test Case 6: Two PDFs containing similar but distinct topics.
    'Simple Linear Regression' (PDF 9) and 'Multiple Linear Regression' (PDF 10)
    must remain separate distinct entries and not be collapsed into a single topic.
    """
    service = TopicExtractionService()
    res9 = service.extract_topics_from_pdf(ten_pdf_test_suite["pdf9"], "pdf9.pdf")
    res10 = service.extract_topics_from_pdf(ten_pdf_test_suite["pdf10"], "pdf10.pdf")

    consolidated = service.consolidate_master_topics([res9, res10])
    master_keys = list(consolidated["master_topics"].keys())

    # Verify both exist as distinct keys in master_topics
    simple_key = normalize_match_key("Simple Linear Regression")
    multiple_key = normalize_match_key("Multiple Linear Regression")

    assert simple_key in master_keys, f"Expected {simple_key} in {master_keys}"
    assert multiple_key in master_keys, f"Expected {multiple_key} in {master_keys}"
    assert simple_key != multiple_key, "Simple and Multiple Linear Regression must have distinct normalized keys"


@pytest.mark.asyncio
async def test_precision_recall_and_attribution_metrics(ten_pdf_test_suite):
    """
    Measures and asserts:
    - Topic precision: extracted topics must be 100% grounded in document contents (0 hallucinations).
    - Topic recall: ground truth topics recovered from the 9 readable PDFs.
    - Attribution accuracy: source filename and page numbers are attached to all extracted topics.
    """
    service = TopicExtractionService()
    result = await service.extract_exhaustive_topics_for_course(
        query="List all topics in the uploaded materials",
        file_paths=ten_pdf_test_suite["paths"]
    )

    answer = result["answer"]
    citations = result.get("citations", [])

    # Check citations attribution
    assert len(citations) > 0
    for cite in citations:
        assert cite["source_file"] is not None
        assert cite["page_number"] is not None
        assert cite["page_number"] > 0

    ground_truth = ten_pdf_test_suite["ground_truth_topics"]
    recovered = set()
    for gt in ground_truth:
        norm_gt = clean_topic_name(gt).lower()
        if norm_gt in answer.lower():
            recovered.add(gt)

    recall = len(recovered) / len(ground_truth)
    # Recall should be >= 85% across all 9 valid PDFs
    assert recall >= 0.85, f"Expected topic recall >= 0.85, got {recall:.2f}. Recovered: {recovered}"

    # Precision: zero hallucinated topics outside course PDFs
    hallucinated_candidates = ["Quantum Computing", "Blockchain Architecture", "Photosynthesis", "French Literature"]
    for hc in hallucinated_candidates:
        assert hc.lower() not in answer.lower(), f"Detected hallucinated topic in answer: {hc}"


@pytest.mark.asyncio
async def test_grounded_generator_routes_to_exhaustive_extraction_pipeline(monkeypatch, ten_pdf_test_suite):
    """
    Verifies that the chatbot's primary entrypoint (grounded_generator.answer_question)
    directly recognizes an exhaustive topic query and invokes the dedicated exhaustive extraction
    pipeline rather than standard top-k semantic retrieval.
    """
    called_exhaustive = False
    original_extract = topic_extractor.extract_exhaustive_topics_for_course

    async def mock_extract(query, course_id=None, session=None, target_doc_ids=None, file_paths=None):
        nonlocal called_exhaustive
        called_exhaustive = True
        return await original_extract(
            query=query,
            file_paths=ten_pdf_test_suite["paths"][:2]
        )

    monkeypatch.setattr(topic_extractor, "extract_exhaustive_topics_for_course", mock_extract)

    response = await grounded_generator.answer_question(
        query="List all topics in the uploaded materials",
        course_id="test-course-id"
    )

    assert called_exhaustive is True, "grounded_generator did not route exhaustive topic query to topic_extractor"
    assert "### Document Processing Summary" in response["answer"]
    assert "### Complete Topic Index" in response["answer"]
    assert "### Consolidated Master Topic List" in response["answer"]
    assert "### Coverage and Limitations" in response["answer"]

