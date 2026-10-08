from typing import List, Dict, Any
from backend.app.ai.llm.provider import get_llm_provider
from backend.app.core.logging import logger

TOPIC_EXTRACTION_PROMPT = """
You are a senior curriculum designer and educational knowledge architect.
Analyze the provided course material text and extract a structured hierarchy of Topics and Concepts.
Also identify prerequisite relationships between concepts (e.g., Concept A must be learned before Concept B).

Return ONLY valid JSON matching this schema:
{
  "topics": [
    {
      "title": "Topic Name (e.g., Thermodynamics, Network Protocols, Organic Synthesis, Macroeconomics)",
      "description": "Short topic summary",
      "concepts": [
        {
          "name": "Concept Name (e.g., Carnot Cycle, Three-Way Handshake, Nucleophilic Substitution)",
          "subtopic": "Subtopic (e.g., Heat Engines, TCP Connection Management, Reaction Mechanisms)",
          "definition": "Clear concise definition",
          "difficulty": "easy | medium | hard"
        }
      ]
    }
  ],
  "relationships": [
    {
      "source_concept": "Foundational Concept Name",
      "target_concept": "Advanced Concept Name",
      "relationship_type": "prerequisite",
      "strength": 1.0
    }
  ]
}
"""

class TopicExtractionService:
    """Extracts topics, concepts, and prerequisite relationships from course materials."""

    def __init__(self):
        self.llm = get_llm_provider()

    async def extract_course_taxonomy(self, sample_text: str) -> Dict[str, Any]:
        """Runs LLM taxonomy extraction on representative course chunks."""
        prompt = f"{TOPIC_EXTRACTION_PROMPT}\n\nCourse Material Content Excerpt:\n{sample_text[:4000]}"
        try:
            result = await self.llm.generate_json(prompt)
            if "topics" in result:
                return result
        except Exception as e:
            logger.error(f"LLM topic extraction failed: {e}")

        # Fallback taxonomy if parsing error or offline
        return {
            "topics": [
                {
                    "title": "Core Foundations",
                    "description": "Essential foundational concepts in the course module.",
                    "concepts": [
                        {"name": "Foundational Principles", "subtopic": "Basics", "definition": "Core rules governing system state.", "difficulty": "easy"},
                        {"name": "State Transitions", "subtopic": "Execution", "definition": "How components transition between valid states.", "difficulty": "medium"}
                    ]
                }
            ],
            "relationships": [
                {
                    "source_concept": "Foundational Principles",
                    "target_concept": "State Transitions",
                    "relationship_type": "prerequisite",
                    "strength": 1.0
                }
            ]
        }

topic_extractor = TopicExtractionService()
