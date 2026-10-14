from typing import Dict, Any, List, Optional
from backend.app.ai.llm.provider import get_llm_provider
from backend.app.core.logging import logger

QUESTION_GENERATION_PROMPT = """
You are a senior exam designer and assessment psychometrician.
Generate an educational assessment question grounded directly in the provided course material.

Target Concept: {concept}
Topic: {topic}
Difficulty: {difficulty}
Question Type: {qtype} (mcq | numerical | conceptual | short_answer)

Rules:
1. Ensure the question tests true conceptual understanding or problem-solving, not trivial keyword matching.
2. For MCQ: provide 4 distinct plausible options (A, B, C, D) with 1 unambiguously correct option and informative distractors.
3. For Numerical: provide step-by-step mathematical calculations and deterministic final answer.
4. Provide a thorough pedagogical explanation.

Return ONLY a valid JSON object matching:
{
  "question": "Question text...",
  "question_type": "{qtype}",
  "difficulty": "{difficulty}",
  "options": [
    {"id": "A", "text": "Option A text"},
    {"id": "B", "text": "Option B text"},
    {"id": "C", "text": "Option C text"},
    {"id": "D", "text": "Option D text"}
  ],
  "correct_answer": "Option letter (e.g. 'A') or exact numerical/text answer",
  "explanation": "Detailed step-by-step explanation why the correct answer is right and why others are wrong.",
  "topic": "{topic}",
  "concept": "{concept}",
  "math_expression": "Optional sympy-evaluable expression if numerical, e.g. 5 + 3 * 2"
}
"""

class QuestionGenerator:
    """Generates source-grounded assessment questions across diverse difficulty levels and types."""

    def __init__(self):
        self.llm = get_llm_provider()

    async def generate_question(
        self,
        concept: str,
        topic: str,
        difficulty: str = "medium",
        question_type: str = "mcq",
        source_context: str = ""
    ) -> Dict[str, Any]:
        prompt = (
            QUESTION_GENERATION_PROMPT
            .replace("{concept}", concept)
            .replace("{topic}", topic)
            .replace("{difficulty}", difficulty)
            .replace("{qtype}", question_type)
        )
        if source_context:
            prompt += f"\n\nSource Material Context:\n{source_context[:2500]}"

        try:
            result = await self.llm.generate_json(prompt)
            if "question" in result and "correct_answer" in result:
                return result
        except Exception as e:
            logger.error(f"Question generation failed: {e}")

        # Fallback question grounded in source context if available
        clean_context = re.sub(r"\[\d{2}:\d{2}(?::\d{2})?\]", "", source_context).strip()
        context_preview = ""
        if clean_context:
            sentences = [s.strip() for s in re.split(r"[.!?]", clean_context) if len(s.strip().split()) >= 4]
            if sentences:
                context_preview = sentences[0]

        if context_preview:
            return {
                "question": f"Based on the lecture on {topic}, how is {concept} explained?",
                "question_type": "mcq",
                "difficulty": difficulty,
                "options": [
                    {"id": "A", "text": f"{context_preview}."},
                    {"id": "B", "text": f"It is introduced as an alternative that replaces {topic} completely."},
                    {"id": "C", "text": f"It is mentioned solely as a historical footnote with no current application."},
                    {"id": "D", "text": f"It is presented as an error condition to be avoided."}
                ],
                "correct_answer": "A",
                "explanation": f"According to the lecture: \"{context_preview}.\"",
                "topic": topic,
                "concept": concept
            }

        return {
            "question": f"In the study of {topic}, what is the key function of {concept}?",
            "question_type": "mcq",
            "difficulty": difficulty,
            "options": [
                {"id": "A", "text": f"It defines the core operation and principles governing {concept} in {topic}."},
                {"id": "B", "text": f"It serves only as a temporary placeholder without computational significance."},
                {"id": "C", "text": f"It reverses the fundamental logic of {topic}."},
                {"id": "D", "text": f"It is an obsolete concept superseded by unrelated techniques."}
            ],
            "correct_answer": "A",
            "explanation": f"{concept} plays a central role in {topic} by defining the foundational logic and practical behavior.",
            "topic": topic,
            "concept": concept
        }

question_generator = QuestionGenerator()
