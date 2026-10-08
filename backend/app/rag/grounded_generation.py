from typing import Dict, Any, List, Optional
from backend.app.ai.llm.provider import get_llm_provider
from backend.app.rag.query_understanding import query_analyzer
from backend.app.rag.hybrid_retrieval import hybrid_retriever
from backend.app.rag.context_builder import context_builder
from backend.app.rag.citation_validator import citation_validator
from backend.app.core.logging import logger

SYSTEM_PROMPT = """
You are SynapseTutor, a senior personalized multimodal AI tutor.
Your core principles:
1. SOURCE GROUNDING: You must answer using the provided course materials whenever the question is course-related.
2. CITATION DISCIPLINE: Always cite your sources explicitly in the text using bracketed format, e.g. [Source: Operating Systems • Page 384] or [Source: Module 4 • Slide 24]. Never fabricate citations.
3. ADAPTIVE PEDAGOGY: Adapt your explanation to the student's mastery level and learning behavior profile.
4. HONEST BOUNDARIES: If the provided materials do not contain sufficient information to answer the course question, clearly state: "This topic is not covered in the uploaded course material." Do not hallucinate course facts.
"""

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
        allow_outside_knowledge: bool = False
    ) -> Dict[str, Any]:
        """
        Executes grounded generation pipeline.
        Returns:
        {
          "answer": "...",
          "citations": [...],
          "is_outside_knowledge": bool,
          "outside_knowledge_offered": bool,
          "suggested_followups": [...],
          "retrieved_chunks_count": int
        }
        """
        # Step 1: Query Understanding & Off-Material Detection
        query_info = await query_analyzer.analyze_query(query, course_subject=course_subject)
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

        # Step 3: Hybrid Retrieval
        chunks = []
        if not (is_off_material and explicit_outside):
            chunks = await hybrid_retriever.retrieve_candidates(
                query=query,
                course_id=course_id,
                top_k=5
            )

        # Step 4: Check if retrieved chunks are sufficient
        # If no chunks match and query was ostensibly course-related
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

        # Outside knowledge labeling
        outside_warning = ""
        if is_off_material and explicit_outside:
            outside_warning = "\n[NOTE: This answer uses OUTSIDE KNOWLEDGE as requested. Explicitly label the response as 'Outside Knowledge']"

        generation_prompt = f"""
{SYSTEM_PROMPT}
{learner_hint}
{episodic_hint}
{outside_warning}

--- RETRIEVED COURSE SOURCES ---
{grounded_context}

--- STUDENT QUESTION ---
{query}

Provide a clear, engaging, and accurate explanation grounded in the course sources above.
Include exact citation labels like [Source: Filename • Page X] or [Source: Filename • Slide Y].
At the end of your answer, provide 2 short follow-up questions the student might want to ask next.
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
