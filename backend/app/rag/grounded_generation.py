import re
from typing import Dict, Any, List, Optional, Tuple
from backend.app.ai.llm.provider import get_llm_provider
from backend.app.rag.query_understanding import query_analyzer
from backend.app.rag.hybrid_retrieval import hybrid_retriever
from backend.app.rag.context_builder import context_builder
from backend.app.rag.citation_validator import citation_validator
from backend.app.core.logging import logger

SYSTEM_PROMPT = """
You are SynapseTutor, an encouraging, articulate, and friendly AI tutor.
Your core principles:
1. SOURCE GROUNDING: Answer using the provided course materials whenever the question is course-related.
2. CITATION DISCIPLINE: Always cite your sources explicitly in the text using bracketed format, e.g. [Source: Textbook • Page 42], [Source: Module 4 • Slide 24], or [Source: Lecture Video • 02:35]. Never fabricate citations.
3. HUMAN-FRIENDLY CLARITY & CLEAN FORMATTING: Present explanations in a conversational, structured, and easy-to-read style. Use clean bullet points, short paragraphs, and clear concept names. Do NOT use awkward formatting, excessive asterisks (****), or raw HTML tags like <br> (use standard clean markdown paragraphs).
4. ENGLISH PEDAGOGICAL EXPLANATION: Regardless of the domain or language of the student's question, always provide your explanation in clear, accessible, and supportive English.
5. ADAPTIVE PEDAGOGY: Adapt your explanation to the student's mastery level and learning behavior profile. If the student indicates confusion or requests a simpler explanation, immediately provide a real-world intuitive analogy, break the concept into bite-sized steps, and avoid intimidating jargon.
6. MATHEMATICAL & CALCULUS EXPRESSIONS: Whenever writing math formulas (e.g. derivatives $\\frac{dy}{dx}$, partial derivatives $\\frac{\\partial L}{\\partial w}$, integrals $\\int_{a}^{b} f(x)\\,dx$, limits $\\lim_{x \\to \\infty}$, summation $\\sum_{i=1}^n x_i$, or dimension formulas), write them strictly in standard LaTeX math syntax: inline `$f'(x) = \\frac{df}{dx}$` or block equations `$$\\int_{-\\infty}^{\\infty} e^{-x^2} dx = \\sqrt{\\pi}$$` and `$$\\sigma(z) = \\frac{1}{1 + e^{-z}}$$`.
7. MATRIX SHAPES & FEATURE MAPS: When illustrating 2D matrices, kernels, filters, or feature map values, write them as LaTeX matrices:
$$\\begin{bmatrix} 1 & 2 \\\\ 3 & 4 \\end{bmatrix}$$ or structured markdown tables so the shape and alignment are mathematically precise.
8. FLOWCHARTS, ARCHITECTURES & WORKFLOWS: For ANY subject (such as Operating Systems, Computer Networks, Compiler Design, Database Systems, Software Engineering, Deep Learning, Digital Electronics, or Algorithms), whenever explaining a sequence of steps, lifecycle, protocol, or system architecture:
- For linear pipeline sequences, write clean arrow flows: `Stage 1 → Stage 2 → Stage 3 → Stage 4` (e.g. in OS: `New → Ready → Running → Terminated` or `Interrupt → Context Save → ISR → Context Restore`; in Networks: `SYN → SYN-ACK → ACK`; in Compilers: `Lexical Analysis → Syntax Analysis → Semantic Analysis → Intermediate Code → Code Optimization → Target Code`).
- For multi-branching flowcharts or complex architectures, provide a Mermaid diagram block (```mermaid graph TD or graph LR) with labeled nodes and arrows so it renders as a visual diagram.
9. HIGH-QUALITY CODING INSTRUCTION: When teaching programming (Python, C++, Java, JavaScript, SQL, etc.), provide clean, syntactically correct code blocks with language tags (e.g. ```python). Include clear inline comments and step-by-step logic breakdown.
10. GEOMETRY, SHAPES & DRAWINGS: When explaining geometric shapes, spatial concepts, or coordinate transformations, break them down step-by-step with clear dimensions, vertices, and visual Mermaid diagrams or coordinate grids.
11. VIDEO LECTURE & TIMESTAMP AWARENESS: When explaining video lectures or timestamped materials, identify when topics shift across time intervals (e.g. "From 00:00 to 02:35, the lecture introduces... and from 02:35 to 04:40, it dives into...") and cite exact timestamps: `[Source: Video • 02:35]`.
12. HONEST BOUNDARIES: If the provided materials do not contain sufficient information to answer the course question, clearly state: "This topic is not covered in the uploaded course material." Do not hallucinate course facts.
"""


def extract_topic_keywords(text: str) -> str:
    """Extract key concept nouns from previous message to anchor follow-up questions."""
    stop_words = {
        "what", "is", "are", "the", "a", "an", "in", "on", "of", "to", "for", "with",
        "at", "by", "from", "and", "or", "can", "could", "would", "you", "tell",
        "me", "about", "explain", "how", "does", "do", "did", "please", "why",
        "which", "who", "whom", "where", "when", "there", "their", "give", "show",
        "want", "know", "more", "like", "need", "understand", "hello", "hi", "hey",
        "help", "yes", "sure", "ok", "okay", "fine", "cool", "alright"
    }
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
    concept_words = [w for w in words if w not in stop_words]
    return " ".join(concept_words[:6])


def contextualize_dialogue_query(
    query: str,
    last_user_turn: str,
    last_assistant_turn: str
) -> Tuple[str, bool, bool]:
    """
    Analyzes whether the student's message is:
    1. An affirmation / continuation (e.g. 'yes', 'sure', 'tell me more')
    2. A context-dependent follow-up question (e.g. 'how does it work?', 'what about stride?', 'can you give a formula for it?')
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
        "show me", "let's do that", "sounds good", "alright"
    }

    prev_topic = extract_topic_keywords(last_user_turn)
    if not prev_topic and last_assistant_turn:
        # Extract title or topic from assistant message header or content
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
        "both", "either", "neither", "which", "former", "latter", "same", "above", "such", "here"
    }
    has_pronoun_reference = bool(q_words & anaphoric_markers) or ("in this" in q_clean) or ("in that" in q_clean)

    # 3. Follow-up question starters (comparing, asking for formulas, examples, or effects)
    followup_starters = (
        "what about", "how about", "why is that", "why so", "and what if",
        "what happens if", "does it", "can it", "is it", "will it", "could it",
        "how does", "why does", "what does", "which is", "which one",
        "compare", "difference", "formula", "example", "drawback", "advantage",
        "can you calculate", "how do we calculate", "how to calculate", "what is actually"
    )
    has_followup_starter = any(q_clean.startswith(prefix) for prefix in followup_starters)

    # 4. Short elliptical follow-up questions (e.g. "why?", "how?", "formula?", "example?")
    is_short_followup = len(q_words) <= 3 and not (
        q_clean.startswith("define") or q_clean.startswith("explain")
    )

    if (has_pronoun_reference or has_followup_starter or is_short_followup) and prev_topic:
        # Contextualize query by appending previous topic keywords
        retrieval_query = f"{query} {prev_topic}"
        logger.info(f"Contextualized follow-up question: '{query}' -> '{retrieval_query}' (topic: '{prev_topic}')")
        return (retrieval_query, False, True)

    # 5. Independent Question: user asks about a new concept or specific question directly
    return (query, False, False)


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
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Executes grounded generation pipeline with short-term conversational context.
        """
        # Resolve Conversational Follow-up Context (Short-Term Memory)
        effective_query = query.strip()
        last_assistant_turn = ""
        last_user_turn = ""

        if chat_history:
            for turn in reversed(chat_history):
                if turn.get("role") == "assistant" and not last_assistant_turn and turn.get("content"):
                    last_assistant_turn = turn["content"]
                elif turn.get("role") == "user" and not last_user_turn and turn.get("content"):
                    last_user_turn = turn["content"]

        retrieval_query, is_affirmation, is_contextual_followup = contextualize_dialogue_query(
            query=effective_query,
            last_user_turn=last_user_turn,
            last_assistant_turn=last_assistant_turn
        )

        # Check if previous assistant message offered outside knowledge and user agreed
        if is_affirmation and last_assistant_turn and "outside-knowledge explanation" in last_assistant_turn.lower():
            explicit_outside = True
            is_off_material = True
        else:
            # Step 1: Query Understanding & Off-Material Detection using contextual query if follow-up
            analysis_query = retrieval_query if (is_affirmation or is_contextual_followup) else effective_query
            query_info = await query_analyzer.analyze_query(analysis_query, course_subject=course_subject)
            is_off_material = query_info.get("relevance") == "off_material"
            explicit_outside = query_info.get("explicit_outside_request", False) or allow_outside_knowledge

        # Step 2: Handle Off-Material Queries
        if is_off_material and not explicit_outside:
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

        # Step 3: Hybrid Retrieval using contextualized query with source intent detection
        chunks = []
        if not (is_off_material and explicit_outside):
            detected_source_type = None
            q_intent_lower = f"{retrieval_query} {effective_query}".lower()
            if any(w in q_intent_lower for w in ["video", "youtube", "lecture video", "timestamp", "watch"]):
                detected_source_type = "video"
            elif any(w in q_intent_lower for w in ["pdf", "textbook", "slides", "slide", "ppt", "document"]):
                detected_source_type = "document"

            # Conversational document continuity (e.g. "what are topics in this")
            last_source_file = None
            if last_assistant_turn:
                src_match = re.search(r"\[Source:\s*([^•\]]+)\s*•", last_assistant_turn)
                if src_match:
                    last_source_file = src_match.group(1).strip()

            if last_source_file and (not detected_source_type or detected_source_type == "video") and any(p in q_intent_lower for p in ["in this", "in that", "this video", "the video", "topics present", "topics covered", "what topics"]):
                if "video" in last_source_file.lower():
                    detected_source_type = "video"
                elif ".pdf" in last_source_file.lower():
                    detected_source_type = "document"
                retrieval_query = f"{retrieval_query} {last_source_file}"

            chunks = await hybrid_retriever.retrieve_candidates(
                query=retrieval_query,
                course_id=course_id,
                source_type=detected_source_type,
                top_k=5
            )
            # If filtered retrieval returned empty, relax source_type filter
            if not chunks and detected_source_type:
                chunks = await hybrid_retriever.retrieve_candidates(
                    query=retrieval_query,
                    course_id=course_id,
                    top_k=5
                )
            # If contextual retrieval returned 0 chunks on a conversational follow-up, fall back to searching last_user_turn
            if not chunks and (is_affirmation or is_contextual_followup) and last_user_turn:
                chunks = await hybrid_retriever.retrieve_candidates(
                    query=last_user_turn,
                    course_id=course_id,
                    top_k=5
                )

        # Step 4: Check if retrieved chunks are sufficient
        if not chunks and not is_off_material and not explicit_outside:
            return {
                "answer": (
                    "This topic is not covered in the uploaded course material.\n\n"
                    "Would you like an outside-knowledge explanation?"
                ),
                "citations": [],
                "is_outside_knowledge": False,
                "outside_knowledge_offered": True,
                "suggested_followups": [
                    "Provide an outside-knowledge explanation",
                    "What topics are covered in this course?"
                ],
                "retrieved_chunks_count": 0
            }

        # Step 5: Assemble Grounded Context & Learner Context
        grounded_context = context_builder.build_grounded_context(chunks)

        # Personalization prompt injection
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

        # Format recent short-term dialogue turns
        history_formatted = ""
        if chat_history:
            recent_turns_text = []
            for t in chat_history[-6:]:
                role_label = "Student" if t.get("role") == "user" else "Tutor"
                content_preview = t.get("content", "").strip()[:250]
                recent_turns_text.append(f"{role_label}: {content_preview}")
            if recent_turns_text:
                history_formatted = "\n--- RECENT CONVERSATION HISTORY ---\n" + "\n".join(recent_turns_text) + "\n"

        # Outside knowledge labeling
        outside_warning = ""
        if is_off_material and explicit_outside:
            outside_warning = "\n[NOTE: This answer uses OUTSIDE KNOWLEDGE as requested. Explicitly label the response as 'Outside Knowledge']"

        generation_prompt = f"""
{SYSTEM_PROMPT}
{learner_hint}
{episodic_hint}
{outside_warning}
{history_formatted}
--- RETRIEVED COURSE SOURCES ---
{grounded_context}

--- STUDENT'S LATEST MESSAGE ---
{query}

Provide a clear, warm, engaging, and well-structured explanation grounded in the course sources above.
Guidelines:
1. If the student's message is a follow-up question (e.g. asking 'why', 'how', for a formula, comparison, or referring back to prior concepts with words like 'it', 'that', or 'which'), answer their question thoroughly in direct connection to the ongoing conversation and the course sources.
2. If the student's message is an affirmation (e.g. 'yes', 'sure', 'tell me more'), seamlessly expand on your previous answer or dive into the suggested next steps.
3. If the student asks about a new topic, provide a clean educational explanation for the new topic, smoothly connecting it with prior knowledge where appropriate.
4. Organize your response with clean headings or bullet points for effortless readability.
5. Include exact citation labels like [Source: Filename • Page X] or [Source: Filename • Slide Y].
6. At the end of your answer, provide 2 short follow-up questions the student might want to ask next.
"""

        # Step 6: Generate Response
        raw_response = await self.llm.generate(generation_prompt, temperature=0.2)

        # Step 7: Validate Citations
        citations = citation_validator.extract_and_validate_citations(raw_response, chunks)

        # Step 8: Extract Follow-up Questions
        followups = [
            "Can we walk through a step-by-step example?",
            "How does this relate to other course concepts?"
        ]

        is_outside = bool(is_off_material and explicit_outside)
        if is_outside and not raw_response.startswith("### Outside Knowledge"):
            raw_response = "### Outside Knowledge\n*(This topic is not covered in the uploaded course material)*\n\n" + raw_response

        return {
            "answer": raw_response,
            "citations": citations,
            "is_outside_knowledge": is_outside,
            "outside_knowledge_offered": False,
            "suggested_followups": followups,
            "retrieved_chunks_count": len(chunks)
        }

grounded_generator = GroundedGenerationService()
