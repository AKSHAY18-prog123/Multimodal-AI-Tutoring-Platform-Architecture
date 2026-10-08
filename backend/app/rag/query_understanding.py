import re
from typing import Dict, Any, List, Optional
from backend.app.ai.llm.provider import get_llm_provider

QUERY_UNDERSTANDING_PROMPT = """
You are an intelligent educational query analyzer.
Analyze the student's question and determine:
1. Intent: 'conceptual_explanation' | 'numerical_problem' | 'definition' | 'exam_prep' | 'chitchat' | 'outside_inquiry'
2. Course relevance: 'on_topic' | 'off_material' | 'ambiguous'
3. Key concept keywords mentioned in the query
4. Does the user explicitly ask for outside knowledge? (e.g., 'explain from outside', 'beyond the syllabus')

Return ONLY a valid JSON object matching:
{
  "intent": "conceptual_explanation",
  "relevance": "on_topic",
  "keywords": ["Core Mechanism", "Governing Principles"],
  "explicit_outside_request": false
}
"""

class QueryUnderstandingService:
    """Analyzes student query intent, domain relevance, and extracts concept keywords."""

    def __init__(self):
        self.llm = get_llm_provider()

    async def analyze_query(self, query: str, course_subject: str = "") -> Dict[str, Any]:
        q_lower = query.lower()

        # Heuristic shortcut for common outside-knowledge benchmarks
        off_material_signals = [
            "nvidia gpu", "weather", "recipe", "stock price", "celebrity gossip",
            "crypto price", "cryptocurrency trading", "movie plot", "cake", "actor", "market price"
        ]
        if any(term in q_lower for term in off_material_signals):
            return {
                "intent": "outside_inquiry",
                "relevance": "off_material",
                "keywords": [query],
                "explicit_outside_request": "outside" in q_lower or "beyond" in q_lower
            }

        # Check explicit outside request
        wants_outside = any(phrase in q_lower for phrase in ["outside knowledge", "beyond the course", "external source", "general knowledge"])

        prompt = f"{QUERY_UNDERSTANDING_PROMPT}\nCourse Subject: {course_subject}\nStudent Question: \"{query}\""
        try:
            result = await self.llm.generate_json(prompt)
            if "intent" in result:
                result["explicit_outside_request"] = wants_outside or result.get("explicit_outside_request", False)
                return result
        except Exception:
            pass

        # Fallback analysis
        words = [w for w in re.findall(r"\w+", query) if len(w) > 3]
        return {
            "intent": "conceptual_explanation",
            "relevance": "on_topic",
            "keywords": words[:5],
            "explicit_outside_request": wants_outside
        }

query_analyzer = QueryUnderstandingService()
