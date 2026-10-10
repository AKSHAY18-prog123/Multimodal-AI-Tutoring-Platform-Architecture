import re
from typing import Dict, Any, List, Optional
from backend.app.ai.llm.provider import get_llm_provider
from backend.app.ai.reranker.base import extract_content_terms

QUERY_UNDERSTANDING_PROMPT = """
You are an intelligent educational query analyzer.
Analyze the student's question and determine:
1. Intent: 'greeting_or_social' | 'acknowledgement' | 'course_question' | 'syllabus_overview' | 'source_specific_request' | 'ambiguous_followup' | 'outside_permission_grant' | 'outside_permission_decline' | 'unrelated_question' | 'conceptual_explanation' | 'numerical_problem' | 'definition' | 'exam_prep'
2. Course relevance: 'on_topic' | 'off_material' | 'ambiguous' | 'conversational'
3. Key concept keywords mentioned in the query
4. Does the user explicitly ask for outside knowledge? (e.g., 'explain from outside', 'beyond the syllabus')

Return ONLY a valid JSON object matching:
{
  "intent": "course_question",
  "relevance": "on_topic",
  "keywords": ["Core Mechanism", "Governing Principles"],
  "explicit_outside_request": false
}
"""

_GREETING_EXACT = {
    "hi", "hello", "hey", "hiya", "howdy", "greetings",
    "good morning", "good afternoon", "good evening",
    "hi there", "hello there", "hey there",
    "how are you", "how are you doing", "how is it going",
    "who are you", "what can you do", "what can you help me with",
    "can you help me", "help me study"
}

_ACKNOWLEDGEMENT_EXACT = {
    "thanks", "thank you", "thank you so much", "thanks a lot", "many thanks",
    "thx", "ty", "okay", "ok", "got it", "i got it", "understood", "i understand",
    "i understand now", "makes sense", "that makes sense", "crystal clear",
    "cool", "great", "awesome", "nice", "perfect", "alright", "sounds good",
    "okay thanks", "ok thank you", "got it thanks", "understood thank you",
    "okay got it", "ok got it", "alright got it", "got it thank you", "thanks got it"
}

_PERMISSION_GRANT_PHRASES = {
    "yes", "yeah", "yep", "sure", "ok", "okay", "please", "go ahead",
    "yes please", "yes explain", "yes please explain", "definitely",
    "yes explain using outside knowledge", "explain using outside knowledge",
    "provide an outside-knowledge explanation", "use outside knowledge",
    "explain with outside knowledge", "outside knowledge please",
    "yes use outside knowledge", "sure go ahead"
}

_PERMISSION_DECLINE_PHRASES = {
    "no", "nope", "no thanks", "no thank you", "skip", "never mind", "nevermind",
    "dont", "do not", "return to course topics", "stay on course",
    "only course material", "stick to the course", "back to course"
}


def classify_conversational_intent(
    query: str,
    last_assistant_turn: str = ""
) -> Optional[Dict[str, Any]]:
    """
    Fast, deterministic intent classifier for conversational turns, permission responses,
    syllabus overview requests, and explicit off-material queries.
    """
    q_clean = re.sub(r"[^\w\s-]", " ", query.strip().lower())
    q_clean = re.sub(r"\s+", " ", q_clean).strip()
    last_asst_lower = (last_assistant_turn or "").lower()
    pending_outside_offer = (
        "outside-knowledge explanation" in last_asst_lower
        or "would you like me to explain it using general knowledge" in last_asst_lower
        or "would you like an outside-knowledge" in last_asst_lower
    )

    # 1. Check response to a pending outside-knowledge offer FIRST
    if pending_outside_offer:
        if q_clean in _PERMISSION_GRANT_PHRASES or any(p in q_clean for p in [
            "outside knowledge", "outside-knowledge", "general knowledge", "yes explain", "go ahead"
        ]):
            return {
                "intent": "outside_permission_grant",
                "relevance": "off_material",
                "keywords": [],
                "explicit_outside_request": True
            }
        if q_clean in _PERMISSION_DECLINE_PHRASES or q_clean.startswith("no ") or "return to course" in q_clean:
            return {
                "intent": "outside_permission_decline",
                "relevance": "conversational",
                "keywords": [],
                "explicit_outside_request": False
            }

    # 2. Direct explicit outside-knowledge button / command even without matching last_asst_lower
    if q_clean in {
        "yes explain using outside knowledge",
        "provide an outside-knowledge explanation",
        "explain with outside knowledge",
        "explain using outside knowledge"
    }:
        return {
            "intent": "outside_permission_grant",
            "relevance": "off_material",
            "keywords": [],
            "explicit_outside_request": True
        }

    if q_clean == "return to course topics":
        return {
            "intent": "outside_permission_decline",
            "relevance": "conversational",
            "keywords": [],
            "explicit_outside_request": False
        }

    # 3. Greeting or social turn
    if q_clean in _GREETING_EXACT or re.match(r"^(?:hi|hello|hey|good\s+(?:morning|afternoon|evening))(?:[\s,!]+(?:tutor|synapsetutor|there|how\s+are\s+you))?$", q_clean):
        return {
            "intent": "greeting_or_social",
            "relevance": "conversational",
            "keywords": [],
            "explicit_outside_request": False
        }

    # 4. Acknowledgement / brief closure turn
    if q_clean in _ACKNOWLEDGEMENT_EXACT:
        return {
            "intent": "acknowledgement",
            "relevance": "conversational",
            "keywords": [],
            "explicit_outside_request": False
        }

    # 5. Syllabus / full material overview
    if any(p in q_clean for p in [
        "entire syllabus", "whole syllabus", "full syllabus", "complete syllabus",
        "all uploaded material", "entire uploaded material", "teach me the syllabus",
        "what topics are covered", "course overview", "video overview"
    ]):
        return {
            "intent": "syllabus_overview",
            "relevance": "on_topic",
            "keywords": extract_content_terms(query)[:5],
            "explicit_outside_request": False
        }

    return None


class QueryUnderstandingService:
    """Analyzes student query intent, domain relevance, and extracts concept keywords."""

    def __init__(self):
        self.llm = get_llm_provider()

    async def analyze_query(
        self,
        query: str,
        course_subject: str = "",
        last_assistant_turn: str = ""
    ) -> Dict[str, Any]:
        # Fast conversational & state-machine classification first
        conv = classify_conversational_intent(query, last_assistant_turn=last_assistant_turn)
        if conv is not None:
            return conv

        q_lower = query.lower()

        # Check explicit outside request
        wants_outside = any(phrase in q_lower for phrase in [
            "outside knowledge", "outside-knowledge", "beyond the course",
            "beyond the syllabus", "external source", "general knowledge", "from outside"
        ])

        # Heuristic shortcut for clearly unrelated / off-material queries
        off_material_signals = [
            "nvidia gpu", "weather", "recipe", "stock price", "celebrity gossip",
            "crypto price", "cryptocurrency trading", "movie plot", "bake a cake",
            "chocolate cake", "actor", "market price", "fifa world cup", "taylor swift",
            "bitcoin price"
        ]
        if any(term in q_lower for term in off_material_signals):
            return {
                "intent": "unrelated_question",
                "relevance": "off_material",
                "keywords": extract_content_terms(query)[:5] or [query],
                "explicit_outside_request": wants_outside
            }

        # Source-specific request detection
        is_source_specific = any(w in q_lower for w in [
            "page ", "slide ", "at what time", "timestamp", "in this video",
            "from this lecture", "in the pdf", "in the ppt", "powerpoint", ".pdf", ".pptx", ".mp4"
        ])

        content_words = extract_content_terms(query)
        default_intent = "source_specific_request" if is_source_specific else "course_question"

        prompt = f"{QUERY_UNDERSTANDING_PROMPT}\nCourse Subject: {course_subject}\nStudent Question: \"{query}\""
        try:
            result = await self.llm.generate_json(prompt)
            if isinstance(result, dict) and "intent" in result:
                # Never let LLM misclassify an obvious question as chitchat if it has content words
                if result.get("intent") == "chitchat" and content_words:
                    result["intent"] = default_intent
                if is_source_specific and result.get("intent") in ("conceptual_explanation", "course_question"):
                    result["intent"] = "source_specific_request"
                result["explicit_outside_request"] = wants_outside or bool(result.get("explicit_outside_request", False))
                if not result.get("keywords"):
                    result["keywords"] = content_words[:5]
                return result
        except Exception:
            pass

        return {
            "intent": default_intent,
            "relevance": "on_topic",
            "keywords": content_words[:5],
            "explicit_outside_request": wants_outside
        }


query_analyzer = QueryUnderstandingService()
