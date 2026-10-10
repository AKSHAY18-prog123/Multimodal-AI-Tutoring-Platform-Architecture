import re
from typing import Dict, Any, List, Optional, Tuple
from backend.app.ai.llm.provider import get_llm_provider
from backend.app.ai.reranker.base import extract_content_terms
from backend.app.rag.query_understanding import query_analyzer, classify_conversational_intent
from backend.app.rag.hybrid_retrieval import hybrid_retriever
from backend.app.rag.source_resolver import source_resolver
from backend.app.rag.context_builder import context_builder
from backend.app.rag.citation_validator import citation_validator
from backend.app.core.logging import logger

SYSTEM_PROMPT = r"""
You are SynapseTutor, an encouraging, articulate, and friendly AI tutor.
Your core principles:
1. SOURCE GROUNDING: Answer using the provided course materials whenever the question is course-related.
2. CITATION DISCIPLINE: Always cite your sources explicitly in the text using bracketed format, e.g. [Source: Textbook • Page 42], [Source: Module 4 • Slide 24], or [Source: Lecture Video • 02:35-04:10]. Never fabricate citations.
3. HUMAN-FRIENDLY CLARITY & CLEAN FORMATTING: Present explanations in a conversational, structured, and easy-to-read style. Use clean bullet points, short paragraphs, and clear concept names. Do NOT use awkward formatting, excessive asterisks (****), or raw HTML tags like <br> (use standard clean markdown paragraphs).
4. ENGLISH PEDAGOGICAL EXPLANATION: Regardless of the domain or language of the student's question, always provide your explanation in clear, accessible, and supportive English.
5. ADAPTIVE PEDAGOGY: Adapt your explanation to the student's mastery level and learning behavior profile. If the student indicates confusion or requests a simpler explanation, immediately provide a real-world intuitive analogy, break the concept into bite-sized steps, and avoid intimidating jargon.
6. MATHEMATICAL & CALCULUS EXPRESSIONS: Whenever writing math formulas (e.g. derivatives $\\frac{dy}{dx}$, partial derivatives $\\frac{\\partial L}{\\partial w}$, integrals $\\int_{a}^{b} f(x)\\,dx$, limits $\\lim_{x \\to \\infty}$, summation $\\sum_{i=1}^n x_i$, or dimension formulas), write them strictly in standard LaTeX math syntax: inline `$f'(x) = \\frac{df}{dx}$` or block equations `$$\\int_{-\\infty}^{\\infty} e^{-x^2} dx = \\sqrt{\\pi}$$` and `$$\\sigma(z) = \\frac{1}{1 + e^{-z}}$$`.
7. STEP-BY-STEP PROBLEM SOLVING & FORMULA CALCULATION:
Whenever the student asks to solve a problem, numerical question, exercise, algorithmic problem (e.g. Knapsack, CPU scheduling, Page replacement, gradient descent, etc.), or requests a step-by-step solution with formula:
- ACTIVE & COMPLETE RESOLUTION: Actively solve the problem completely from start to finish! Do NOT merely provide a high-level conceptual summary. Use the exact numbers and parameters from the course material or student query.
- GIVEN DATA & PARAMETERS: Clearly list the given inputs, parameters, and constraints in a structured list (e.g. Given: Bag Capacity $M = 20$, Objects, Weights, Profits).
- GOVERNING FORMULAS: State each governing formula or decision criterion explicitly in LaTeX BEFORE substituting numbers (e.g. Profit/Weight ratio $r_i = \frac{p_i}{w_i}$, Remaining Capacity $M_{\text{rem}} = M - w_i$, Total Profit $P = \sum p_i x_i$).
- STEP-BY-STEP BREAKDOWN: Structure the work into sequentially numbered steps:
  * **Step 1: Formula & Criteria Definition** (Define the formulas, equations, and decision rules).
  * **Step 2: Calculations & Table of Values** (Compute intermediate values like ratios or deltas, displayed in a clean Markdown table).
  * **Step 3: Sequential Execution / Decision Walkthrough** (Walk through each step or item selection showing arithmetic operations explicitly).
  * **Step 4: Final Total Computation** (Calculate the final answer or optimal value).
- HIGHLIGHT FINAL RESULT: Conclude with the final computed numerical result prominently highlighted in bold (e.g., **Final Answer: Maximum Profit = 31.5**).
8. MATRIX SHAPES & FEATURE MAPS: When illustrating 2D matrices, kernels, filters, or feature map values, write them as LaTeX matrices:
$$\\begin{bmatrix} 1 & 2 \\\\ 3 & 4 \\end{bmatrix}$$ or structured markdown tables so the shape and alignment are mathematically precise.
9. FLOWCHARTS, ARCHITECTURES & WORKFLOWS: For ANY subject (such as Operating Systems, Computer Networks, Compiler Design, Database Systems, Software Engineering, Deep Learning, Digital Electronics, or Algorithms), whenever explaining a sequence of steps, lifecycle, protocol, or system architecture:
- For linear pipeline sequences, write clean arrow flows: `Stage 1 → Stage 2 → Stage 3 → Stage 4`.
- For multi-branching flowcharts or complex architectures, provide a Mermaid diagram block (```mermaid graph TD or graph LR) with labeled nodes and arrows so it renders as a visual diagram.
10. HIGH-QUALITY CODING INSTRUCTION: When teaching programming (Python, C++, Java, JavaScript, SQL, etc.), provide clean, syntactically correct code blocks with language tags (e.g. ```python). Include clear inline comments and step-by-step logic breakdown.
11. GEOMETRY, SHAPES & DRAWINGS: When explaining geometric shapes, spatial concepts, or coordinate transformations, break them down step-by-step with clear dimensions, vertices, and visual Mermaid diagrams or coordinate grids.
12. VIDEO LECTURE & TIMESTAMP AWARENESS: When explaining video lectures or timestamped materials, identify the exact timestamp or timestamp range where the instructor discusses the topic (e.g. "From 02:35 to 04:40, the instructor explains..."), include the direct video link when provided in the source header, and cite exact timestamps: `[Source: Video • 02:35-04:40]`.
13. HONEST BOUNDARIES: If the provided materials do not contain sufficient information to answer the course question, clearly state: "This topic is not covered in the uploaded course material." Do not hallucinate course facts or fabricate timestamps.
"""


def extract_topic_keywords(text: str) -> str:
    """Extract key concept nouns from previous message to anchor follow-up questions."""
    stop_words = {
        "what", "is", "are", "the", "a", "an", "in", "on", "of", "to", "for", "with",
        "at", "by", "from", "and", "or", "can", "could", "would", "you", "tell",
        "me", "about", "explain", "how", "does", "do", "did", "please", "why",
        "which", "who", "whom", "where", "when", "there", "their", "give", "show",
        "want", "know", "more", "like", "need", "understand", "hello", "hi", "hey",
        "help", "yes", "sure", "ok", "okay", "fine", "cool", "alright",
        "outside", "knowledge", "using", "use", "general", "course", "material",
        "materials", "uploaded", "topic", "topics", "return"
    }
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
    concept_words = [w for w in words if w not in stop_words]
    return " ".join(concept_words[:6])


def recover_pending_question(chat_history: Optional[List[Dict[str, str]]], fallback_query: str) -> str:
    """
    Recovers the original user question that triggered an outside-knowledge offer
    from the conversation history.
    """
    if not chat_history:
        return fallback_query

    ignore_phrases = {
        "yes", "yeah", "yep", "sure", "ok", "okay", "please", "go ahead",
        "yes please", "yes, explain using outside knowledge", "yes explain using outside knowledge",
        "provide an outside-knowledge explanation", "explain with outside knowledge",
        "explain using outside knowledge"
    }
    for turn in reversed(chat_history):
        if turn.get("role") == "user" and turn.get("content"):
            cand = turn["content"].strip()
            norm_cand = re.sub(r"[^\w\s-]", " ", cand.lower())
            norm_cand = re.sub(r"\s+", " ", norm_cand).strip()
            if norm_cand not in ignore_phrases and cand.lower().rstrip("!.?, ") not in ignore_phrases:
                return cand
    return fallback_query


def contextualize_dialogue_query(
    query: str,
    last_user_turn: str,
    last_assistant_turn: str
) -> Tuple[str, bool, bool]:
    """
    Analyzes whether the student's message is:
    1. An affirmation / continuation (e.g. 'yes', 'sure', 'tell me more', 'next')
    2. A context-dependent follow-up question (e.g. 'how does it work?', 'what about stride?')
    3. An independent new question (e.g. 'what is dropout?', 'explain backpropagation')

    Returns:
      (retrieval_query, is_affirmation, is_contextual_followup)
    """
    q_clean = query.strip().lower().rstrip("!.,? ")
    q_words = set(re.findall(r"\b\w+\b", q_clean))

    affirmative_phrases = {
        "yes", "yeah", "yep", "sure", "ok", "okay", "please", "go ahead",
        "continue", "yes please", "tell me more", "explain more", "give an example",
        "proceed", "next", "i want to know more", "keep going", "dive deeper",
        "more", "yes dive deeper", "yes explain", "yes please explain", "definitely",
        "show me", "let's do that", "sounds good", "alright",
        "yes, explain using outside knowledge", "provide an outside-knowledge explanation"
    }

    prev_topic = extract_topic_keywords(last_user_turn)
    if not prev_topic and last_assistant_turn and "### outside knowledge" not in last_assistant_turn.lower():
        header_match = re.search(r"###\s*(?:📍|🎬|📘|💡|⚙️|🔁|🛡️)?\s*([^\n]+)", last_assistant_turn)
        if header_match:
            prev_topic = header_match.group(1).strip()
        else:
            prev_topic = extract_topic_keywords(last_assistant_turn[:300])

    # 1. Pure Affirmation / Continuation
    if q_clean in affirmative_phrases:
        retrieval_query = f"{prev_topic} {last_assistant_turn[:200]}".strip()
        return (retrieval_query or query, True, True)

    # 2. Pronouns and anaphoric reference words pointing to previous turn
    anaphoric_markers = {
        "it", "its", "that", "this", "these", "those", "them", "they", "there",
        "both", "either", "neither", "former", "latter", "same", "above", "such", "here"
    }
    has_pronoun_reference = bool(q_words & anaphoric_markers) or ("in this" in q_clean) or ("in that" in q_clean)

    # 3. Follow-up question starters (only contextual starters, NOT generic independent question starters like 'how does')
    followup_starters = (
        "what about", "how about", "why is that", "why so", "and what if",
        "what happens if", "does it", "can it", "is it", "will it", "could it",
        "which one", "can you calculate", "how do we calculate", "how to calculate", "what is actually",
        "solve", "solve it", "can you solve", "solve the problem", "solve this problem",
        "solve step by step", "calculate", "calculate it", "show calculation", "show step by step",
        "solve the question", "i want that", "i want", "can you ans", "ans the problem", "answer the problem"
    )
    problem_followup_phrases = ("step by step", "with formula", "solve the problem", "ans the problem", "solve it", "show calculation", "problem question")
    has_problem_followup = any(p in q_clean for p in problem_followup_phrases)
    has_followup_starter = any(q_clean.startswith(prefix) for prefix in followup_starters)

    # 4. Short elliptical follow-up questions (e.g. "why?", "how?", "formula?", "example?")
    elliptical_words = {"why", "how", "formula", "example", "examples", "proof", "code", "diagram", "summary", "when", "where"}
    is_short_followup = len(q_words) <= 3 and bool(q_words & elliptical_words)

    if (has_pronoun_reference or has_followup_starter or is_short_followup or has_problem_followup) and prev_topic:
        retrieval_query = f"{query} {prev_topic}"
        logger.info(f"Contextualized follow-up question: '{query}' -> '{retrieval_query}' (topic: '{prev_topic}')")
        return (retrieval_query, False, True)

    # 5. Independent Question
    return (query, False, False)


def evaluate_evidence_sufficiency(
    user_query: str,
    retrieval_query: str,
    chunks: List[Dict[str, Any]],
    query_info: Dict[str, Any],
    is_full_syllabus: bool = False,
    target_page: Optional[int] = None,
    target_slide: Optional[int] = None,
    is_followup_or_affirmation: bool = False,
    has_resolved_source: bool = False
) -> Dict[str, Any]:
    """
    Evaluates whether the retrieved chunks actually support answering the student's question.
    Does NOT rely on vector similarity alone: combines content-term coverage, BM25/rerank scores,
    and structural coordinates into a calibrated confidence score.
    Returns:
      {
        "status": "supported" | "inferable" | "insufficient" | "transcript_unavailable",
        "confidence": float,
        "term_coverage": float
      }
    """
    if not chunks:
        return {"status": "insufficient", "confidence": 0.0, "term_coverage": 0.0}

    # Check if all retrieved chunks are fallback video placeholders (no real transcript)
    if all(c.get("metadata", {}).get("is_fallback") for c in chunks):
        return {"status": "transcript_unavailable", "confidence": 0.0, "term_coverage": 0.0}

    q_lower = user_query.lower()
    is_overview_or_step = is_full_syllabus or query_info.get("intent") == "syllabus_overview" or any(
        p in q_lower for p in [
            "overview", "syllabus", "curriculum", "what topics", "all topics",
            "what does this video teach", "what is this video about", "primary topics",
            "foundational mechanisms", "practice exercise", "one by one", "step by step",
            "topic 1", "topic 2", "topic 3", "topic 4", "topic 5", "topic 6", "topic 7",
            "next topic", "first topic", "main topic"
        ]
    )
    if is_overview_or_step:
        return {"status": "supported", "confidence": 0.92, "term_coverage": 1.0}

    if target_page is not None or target_slide is not None:
        return {"status": "supported", "confidence": 0.90, "term_coverage": 1.0}

    content_terms = extract_content_terms(user_query)
    if not content_terms and (has_resolved_source or chunks):
        return {"status": "supported", "confidence": 0.85, "term_coverage": 1.0}

    max_coverage = max((float(c.get("content_term_coverage", 0.0)) for c in chunks), default=0.0)
    max_rerank = max((float(c.get("rerank_score", 0.0)) for c in chunks), default=0.0)
    max_vector = max((float(c.get("vector_score", 0.0)) for c in chunks), default=0.0)

    # Also check direct substring / stem presence across top chunks for user_query content_terms
    if content_terms:
        combined_corpus = " ".join(
            f"{c.get('content', '')} {c.get('metadata', {}).get('source_file', '')}".lower()
            for c in chunks[:4]
        )
        matched = 0
        for t in content_terms:
            stem = t[:max(4, len(t) - 2)] if len(t) >= 5 else t
            if t in combined_corpus or stem in combined_corpus:
                matched += 1
        direct_coverage = matched / len(content_terms)
        max_coverage = max(max_coverage, direct_coverage)

    confidence = round((0.45 * max_rerank) + (0.35 * max_coverage) + (0.20 * max_vector), 4)

    # If the user asked a specific conceptual question with content terms and NONE of those terms
    # (or their stems) appear in the retrieved chunks, vector similarity alone is NOT proof of support!
    if content_terms and max_coverage == 0.0 and not is_followup_or_affirmation:
        return {"status": "insufficient", "confidence": min(confidence, 0.30), "term_coverage": 0.0}

    if is_followup_or_affirmation and chunks:
        return {"status": "supported", "confidence": max(confidence, 0.75), "term_coverage": max(max_coverage, 0.5)}

    if confidence >= 0.45 and max_coverage >= 0.34:
        return {"status": "supported", "confidence": confidence, "term_coverage": max_coverage}

    if confidence >= 0.32 and max_coverage > 0.0:
        return {"status": "inferable", "confidence": confidence, "term_coverage": max_coverage}

    return {"status": "insufficient", "confidence": confidence, "term_coverage": max_coverage}


class GroundedGenerationService:
    """Orchestrates end-to-end grounded multimodal RAG generation with strict source citations."""

    def __init__(self):
        self.llm = get_llm_provider()

    async def answer_question(
        self,
        query: str,
        course_id: Optional[str] = None,
        course_subject: str = "",
        student_profile: Optional[Dict[str, Any]] = None,
        episodic_memories: Optional[List[Dict[str, Any]]] = None,
        allow_outside_knowledge: bool = False,
        chat_history: Optional[List[Dict[str, str]]] = None,
        session: Optional[Any] = None,
        available_docs: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Executes grounded generation pipeline with:
        - Natural conversational handling for greetings & acknowledgements (no forced RAG)
        - Course Library source resolution & duplicate-name disambiguation
        - Hybrid dense + BM25 + FlashRank retrieval with exact timestamp & page/slide anchoring
        - Calibrated evidence sufficiency evaluation
        - One-time outside-knowledge permission state machine
        """
        effective_query = query.strip()
        last_assistant_turn = ""
        last_user_turn = ""

        if chat_history:
            for turn in reversed(chat_history):
                if turn.get("role") == "assistant" and not last_assistant_turn and turn.get("content"):
                    last_assistant_turn = turn["content"]
                elif turn.get("role") == "user" and not last_user_turn and turn.get("content"):
                    last_user_turn = turn["content"]

        # Step 0: Check Conversational Intent & Outside-Knowledge Permission State Machine
        conv_intent = classify_conversational_intent(effective_query, last_assistant_turn=last_assistant_turn)
        if conv_intent is not None:
            intent_type = conv_intent["intent"]

            # Problem E: Greeting or Social Turn -> Natural response without RAG
            if intent_type == "greeting_or_social":
                subj_note = f" for **{course_subject}**" if course_subject else ""
                return {
                    "answer": (
                        f"Hello! I'm **SynapseTutor**, your AI study assistant{subj_note}. "
                        f"I can help you understand your uploaded lectures, PDFs, and slides with exact page, slide, and timestamp citations. "
                        f"What topic or course material would you like to explore today?"
                    ),
                    "citations": [],
                    "is_outside_knowledge": False,
                    "outside_knowledge_offered": False,
                    "suggested_followups": [
                        "What topics are covered in this course?",
                        "Teach me the uploaded lecture step by step"
                    ],
                    "retrieved_chunks_count": 0
                }

            # Problem E: Brief Acknowledgement -> Natural response without unnecessary RAG
            if intent_type == "acknowledgement":
                return {
                    "answer": (
                        "Glad that makes sense! Whenever you're ready, let me know if you'd like to walk through an example, "
                        "try a practice question, or move on to the next topic in your course materials."
                    ),
                    "citations": [],
                    "is_outside_knowledge": False,
                    "outside_knowledge_offered": False,
                    "suggested_followups": [
                        "Can we walk through a step-by-step example?",
                        "Let's move to the next topic"
                    ],
                    "retrieved_chunks_count": 0
                }

            # Problem F: Student declined outside-knowledge offer -> Stay in grounded mode
            if intent_type == "outside_permission_decline":
                return {
                    "answer": (
                        "Understood! We will stay strictly focused on your uploaded course materials. "
                        "Which topic, document, or lecture segment from your course would you like to study next?"
                    ),
                    "citations": [],
                    "is_outside_knowledge": False,
                    "outside_knowledge_offered": False,
                    "suggested_followups": [
                        "What topics are covered in this course?",
                        "Provide a conceptual breakdown of the main module"
                    ],
                    "retrieved_chunks_count": 0
                }

            # Problem F: Student granted one-time permission to answer pending question with outside knowledge
            if intent_type == "outside_permission_grant":
                pending_q = recover_pending_question(chat_history, effective_query)
                return await self._generate_outside_knowledge_answer(
                    pending_question=pending_q,
                    course_subject=course_subject,
                    student_profile=student_profile
                )

        # Step 1: Course Library Source Selection & Duplicate-Name Disambiguation (Problem C)
        resolution = await source_resolver.resolve(
            query=effective_query,
            course_id=course_id,
            session=session,
            chat_history=chat_history,
            available_docs=available_docs
        )
        if resolution["status"] == "ambiguous":
            return {
                "answer": resolution["clarification_message"],
                "citations": [],
                "is_outside_knowledge": False,
                "outside_knowledge_offered": False,
                "suggested_followups": resolution["suggested_options"],
                "retrieved_chunks_count": 0
            }

        if resolution.get("effective_query") and resolution["effective_query"] != effective_query:
            effective_query = resolution["effective_query"]

        target_doc_id = resolution.get("document_id") or resolution.get("document_ids")
        target_course_id = resolution.get("course_id") or course_id
        target_source_type = resolution.get("source_type")
        target_page = resolution.get("page_number")
        target_slide = resolution.get("slide_number")
        is_full_syllabus = bool(resolution.get("is_full_syllabus", False))

        # Step 2: Contextualize Follow-up & Analyze Query
        retrieval_query, is_affirmation, is_contextual_followup = contextualize_dialogue_query(
            query=effective_query,
            last_user_turn=last_user_turn,
            last_assistant_turn=last_assistant_turn
        )

        analysis_query = retrieval_query if (is_affirmation or is_contextual_followup) else effective_query
        query_info = await query_analyzer.analyze_query(
            analysis_query,
            course_subject=course_subject,
            last_assistant_turn=last_assistant_turn
        )
        is_off_material = query_info.get("relevance") == "off_material"
        raw_q_lower = query.lower()
        explicit_in_current_turn = any(phrase in raw_q_lower for phrase in [
            "outside knowledge", "outside-knowledge", "beyond the course",
            "beyond the syllabus", "external source", "general knowledge", "from outside"
        ])
        explicit_outside = bool(explicit_in_current_turn or allow_outside_knowledge)

        # If clearly off-material (e.g. weather, celebrity, stock price) and not explicitly allowed
        if is_off_material and not explicit_outside:
            return self._build_outside_knowledge_offer(effective_query)

        if is_off_material and explicit_outside:
            return await self._generate_outside_knowledge_answer(
                pending_question=effective_query,
                course_subject=course_subject,
                student_profile=student_profile
            )

        # Step 3: Hybrid Retrieval with Resolved Source & Structural Filters
        chunks: List[Dict[str, Any]] = []
        if is_full_syllabus or query_info.get("intent") == "syllabus_overview":
            chunks = hybrid_retriever.retrieve_ordered_document_chunks(
                course_id=target_course_id,
                document_id=target_doc_id,
                source_type=target_source_type,
                max_chunks=10
            )

        if not chunks:
            chunks = await hybrid_retriever.retrieve_candidates(
                query=retrieval_query,
                course_id=target_course_id,
                source_type=target_source_type,
                document_id=target_doc_id,
                page_number=target_page,
                slide_number=target_slide,
                top_k=5,
                include_neighbors=True
            )

        # If page/slide filter yielded 0 chunks, check if relaxing page/slide within the same document helps
        if not chunks and (target_page is not None or target_slide is not None):
            chunks = await hybrid_retriever.retrieve_candidates(
                query=retrieval_query,
                course_id=target_course_id,
                source_type=target_source_type,
                document_id=target_doc_id,
                top_k=5
            )

        # If source_type filter yielded 0 chunks and no specific document was locked, relax source_type
        if not chunks and target_source_type and not target_doc_id:
            chunks = await hybrid_retriever.retrieve_candidates(
                query=retrieval_query,
                course_id=target_course_id,
                top_k=5
            )

        # If contextual follow-up yielded 0 chunks, fall back to last_user_turn
        if not chunks and (is_affirmation or is_contextual_followup) and last_user_turn:
            chunks = await hybrid_retriever.retrieve_candidates(
                query=last_user_turn,
                course_id=target_course_id,
                document_id=target_doc_id,
                top_k=5
            )

        # Step 4: Evaluate Evidence Sufficiency (Problem A & Problem D)
        sufficiency = evaluate_evidence_sufficiency(
            user_query=effective_query,
            retrieval_query=retrieval_query,
            chunks=chunks,
            query_info=query_info,
            is_full_syllabus=is_full_syllabus,
            target_page=target_page,
            target_slide=target_slide,
            is_followup_or_affirmation=(is_affirmation or is_contextual_followup),
            has_resolved_source=bool(target_doc_id)
        )

        if sufficiency["status"] == "transcript_unavailable":
            if explicit_outside:
                return await self._generate_outside_knowledge_answer(
                    pending_question=effective_query,
                    course_subject=course_subject,
                    student_profile=student_profile
                )
            return {
                "answer": (
                    "A reliable timestamped transcript could not be extracted for this lecture video, "
                    "so I cannot verify the exact timestamp or the instructor's spoken explanation from the recording.\n\n"
                    "Would you like an outside-knowledge explanation of this topic?"
                ),
                "citations": [],
                "is_outside_knowledge": False,
                "outside_knowledge_offered": True,
                "suggested_followups": [
                    "Yes, explain using outside knowledge",
                    "Return to course topics"
                ],
                "retrieved_chunks_count": 0
            }

        if sufficiency["status"] == "insufficient":
            if explicit_outside:
                return await self._generate_outside_knowledge_answer(
                    pending_question=effective_query,
                    course_subject=course_subject,
                    student_profile=student_profile
                )
            return self._build_outside_knowledge_offer(effective_query)

        # Step 5: Assemble Grounded Context & Learner Context
        grounded_context = context_builder.build_grounded_context(chunks)

        learner_hint = ""
        if student_profile:
            pref = student_profile.get("explanation_preference", "balanced_scaffolded")
            examples_first = student_profile.get("prefers_examples_before_theory", True)
            math_pref = student_profile.get("prefers_formal_math", False)
            learner_hint = f"\n[STUDENT LEARNING BEHAVIOR: Preference={pref}, ExamplesFirst={examples_first}, FormalMath={math_pref}]"

        episodic_hint = ""
        if episodic_memories:
            recent_events = [f"- {m.get('concept')}: {m.get('evidence')} ({m.get('result')})" for m in episodic_memories[:2]]
            episodic_hint = f"\n[RELEVANT LEARNING EPISODES:\n" + "\n".join(recent_events) + "]"

        history_formatted = ""
        if chat_history:
            recent_turns_text = []
            for t in chat_history[-6:]:
                role_label = "Student" if t.get("role") == "user" else "Tutor"
                content_preview = t.get("content", "").strip()[:250]
                recent_turns_text.append(f"{role_label}: {content_preview}")
            if recent_turns_text:
                history_formatted = "\n--- RECENT CONVERSATION HISTORY ---\n" + "\n".join(recent_turns_text) + "\n"

        inference_hint = ""
        if sufficiency["status"] == "inferable":
            inference_hint = (
                "\n[GROUNDING NOTE: The answer is partially or indirectly supported by the retrieved material. "
                "Explain what the uploaded material states with citations, and clearly distinguish any logical inference "
                "without presenting inferred details as direct quotations.]"
            )

        syllabus_hint = ""
        if is_full_syllabus:
            syllabus_hint = (
                "\n[SYLLABUS TEACHING MODE: The student asked to learn the full uploaded material/syllabus. "
                "Organize your response into structured topics in logical learning progression order using all retrieved sections, "
                "and offer to walk through each section progressively.]"
            )

        is_problem_solving = any(
            w in effective_query.lower() for w in [
                "solve", "solution", "calculate", "step by step", "step-by-step",
                "numerical", "formula", "formulas", "problem", "computation", "walkthrough", "ans the problem"
            ]
        )
        problem_solving_hint = ""
        if is_problem_solving:
            problem_solving_hint = (
                "\n[STEP-BY-STEP PROBLEM SOLVING MODE ACTIVATED:\n"
                "The student specifically requested to solve a problem question step-by-step with formulas.\n"
                "You MUST:\n"
                "1. Actively solve the problem completely from start to finish using the exact parameters from the material or query.\n"
                "2. List all given inputs, parameters, and constraints clearly at the beginning.\n"
                "3. Explicitly state the formulas and criteria in standard LaTeX before plugging in numbers.\n"
                "4. Structure the solution with clear numbered steps ('Step 1: Formula Definition', 'Step 2: Intermediate Values Table', 'Step 3: Sequential Decisions', 'Step 4: Final Total').\n"
                "5. Provide a Markdown table for intermediate variables and calculations where applicable.\n"
                "6. Conclude with the final computed numerical result clearly highlighted in bold (e.g. **Final Answer: ...**).]"
            )

        regression_hint = ""
        eff_lower = effective_query.lower()
        if "multiple" in eff_lower and ("regression" in eff_lower or "linear" in eff_lower):
            regression_hint = (
                "\n[MULTIPLE LINEAR REGRESSION INTEGRITY RULE:\n"
                "The student specifically asked about MULTIPLE Linear Regression.\n"
                "- STRICT PROHIBITION: You must NEVER use or substitute the 1-variable Simple Linear Regression dataset (Study Hours 2, 3, 4, 5 and Marks 40, 50, 60, 70). Doing so is strictly incorrect.\n"
                "- SOURCE GROUNDING:\n"
                "  * If the student asks for the worked example: Use the worked house price example from the retrieved course material (House Size $X_1$, Bedrooms $X_2$, Price $Y$ in ₹ Lakhs with dataset: [900, 2, 35], [1200, 3, 50], [1500, 3, 60], [1800, 4, 75]). Explain step-by-step using the Normal Equation $\\beta = (X^T X)^{-1} X^T Y$, design matrix $X$ with a column of 1s, parameter vector $\\beta = [-5, 0.0333, 5]^T$, regression equation $Y = -5 + 0.0333 X_1 + 5 X_2$, and calculate the predicted price for a 1600 sq.ft house with 3 bedrooms as approximately ₹63.28 Lakhs.\n"
                "  * If the student asks for the assignment on student marks: Use the assignment dataset from the retrieved material (Study Hours $X_1$, Attendance $X_2$, Marks $Y$ with students S1 to S4: S1=[2, 60, 45], S2=[4, 70, 60], S3=[6, 80, 75], S4=[8, 90, 90]) and solve for a student with 5 study hours and 85% attendance.\n"
                "  * If the retrieved material contains only a definition of Multiple Linear Regression and no worked example, explicitly state that limitation instead of presenting Simple Linear Regression as Multiple Linear Regression.\n"
                "  * If the question is ambiguous, clarify whether the student wants the worked house-price example or the student-marks assignment.\n"
                "  * Always include source citations like [Source: Module-1_DL.pdf • Page 61-63].]"
            )
        elif "simple" in eff_lower and ("regression" in eff_lower or "linear" in eff_lower):
            regression_hint = (
                "\n[SIMPLE LINEAR REGRESSION INTEGRITY RULE:\n"
                "The student specifically asked about SIMPLE Linear Regression (single independent variable).\n"
                "Use the Simple Linear Regression example from the course material: Study Hours ($X$: 2, 3, 4, 5) and Marks ($Y$: 40, 50, 60, 70), "
                "calculate means $\\bar{x} = 3.5, \\bar{y} = 55$, slope $b_1 = 10$, intercept $b_0 = 20$, regression equation $Y = 20 + 10X$, "
                "and prediction for 6 hours = 80 marks. Cite [Source: Module-1_DL.pdf • Page 52-53].]"
            )

        generation_prompt = f"""
{SYSTEM_PROMPT}
Course Subject: {course_subject}
{learner_hint}
{episodic_hint}
{inference_hint}
{syllabus_hint}
{problem_solving_hint}
{regression_hint}
{history_formatted}
--- RETRIEVED COURSE SOURCES ---
{grounded_context}

--- STUDENT'S LATEST MESSAGE ---
{effective_query}

Provide a clear, warm, engaging, and well-structured explanation grounded in the course sources above.
Guidelines:
1. If the student asks about a video lecture or when a topic is discussed, state the exact timestamp range (e.g., 02:35 – 04:40) and include the direct VideoURL link if present in the source header.
2. If the student's message is a follow-up question or affirmation, answer thoroughly in direct connection to the ongoing conversation and the course sources.
3. Organize your response with clean headings or bullet points for effortless readability.
4. Include exact citation labels like [Source: Filename • Page X], [Source: Filename • Slide Y], or [Source: Filename • MM:SS-MM:SS].
5. If the student asks to solve a problem, numerical question, or requests a step-by-step solution with formulas:
   - Provide the complete solution solved step-by-step with explicit LaTeX formulas.
   - List the given inputs and parameters clearly at the beginning.
   - Show all intermediate arithmetic calculations and steps.
   - Highlight the final computed answer clearly.
   - Mathematical Notation & Formatting Rules:
     * In the Normal Equation, ALWAYS write with parentheses: `\beta = (X^T X)^{-1} X^T Y` (never omit the parentheses as `X^T X^{-1}`).
     * Ensure every display equation and matrix is cleanly enclosed with matched delimiters (e.g. `$$\begin{{bmatrix}} ... \end{{bmatrix}}$$`). Never leave unmatched stray `\\[` or `\\]` delimiters on lines before headings.
6. At the end of your answer, provide 2 short follow-up questions the student might want to ask next.
"""

        # Step 6: Generate Response
        raw_response = await self.llm.generate(generation_prompt, temperature=0.2, max_tokens=3072)

        # If the LLM itself determined the retrieved chunks do not cover the requested question
        if "this topic is not covered in the uploaded course material" in raw_response.lower():
            if explicit_outside:
                return await self._generate_outside_knowledge_answer(
                    pending_question=effective_query,
                    course_subject=course_subject,
                    student_profile=student_profile
                )
            return self._build_outside_knowledge_offer(effective_query)

        # Step 7: Validate Citations strictly against retrieved chunks
        citations = citation_validator.extract_and_validate_citations(raw_response, chunks)

        followups = [
            "Can we walk through a step-by-step example?",
            "How does this relate to other course concepts?"
        ]

        return {
            "answer": raw_response,
            "citations": citations,
            "is_outside_knowledge": False,
            "outside_knowledge_offered": False,
            "suggested_followups": followups,
            "retrieved_chunks_count": len(chunks),
            "confidence_score": sufficiency["confidence"]
        }

    def _build_outside_knowledge_offer(self, query: str) -> Dict[str, Any]:
        return {
            "answer": (
                "This topic is not covered in the uploaded course material.\n\n"
                "Would you like an outside-knowledge explanation?"
            ),
            "citations": [],
            "is_outside_knowledge": False,
            "outside_knowledge_offered": True,
            "suggested_followups": [
                "Yes, explain using outside knowledge",
                "Return to course topics"
            ],
            "retrieved_chunks_count": 0
        }

    async def _generate_outside_knowledge_answer(
        self,
        pending_question: str,
        course_subject: str = "",
        student_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generates a one-time outside-knowledge explanation for the pending question."""
        outside_prompt = f"""
You are SynapseTutor operating in one-time OUTSIDE KNOWLEDGE MODE.
The student asked: "{pending_question}"
This topic is not covered in their uploaded course materials, and the student explicitly granted one-time permission to explain it using general outside knowledge.
[NOTE: This answer uses OUTSIDE KNOWLEDGE as requested. Explicitly label the response as 'Outside Knowledge']

--- STUDENT'S LATEST MESSAGE ---
{pending_question}

Provide a clear, accurate, and helpful educational explanation of "{pending_question}" using general knowledge.
If this is a problem question, numerical, or calculation, solve it completely step-by-step with explicit LaTeX formulas and arithmetic steps.
Do NOT fabricate any [Source: ...] course citations.
Begin your response with:
### Outside Knowledge
*(This topic is not covered in the uploaded course material. Answering using general outside knowledge.)*
"""
        raw_response = await self.llm.generate(outside_prompt, temperature=0.2)
        if not raw_response.strip().startswith("### Outside Knowledge"):
            raw_response = (
                "### Outside Knowledge\n"
                "*(This topic is not covered in the uploaded course material. Answering using general outside knowledge.)*\n\n"
                + raw_response.strip()
            )

        return {
            "answer": raw_response,
            "citations": [],
            "is_outside_knowledge": True,
            "outside_knowledge_offered": False,
            "suggested_followups": [
                "Return to course topics",
                "What topics are covered in this course?"
            ],
            "retrieved_chunks_count": 0
        }


grounded_generator = GroundedGenerationService()
