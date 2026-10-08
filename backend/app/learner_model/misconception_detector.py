from typing import List, Dict, Any, Optional
from collections import Counter

class MisconceptionDetector:
    """Detects recurring wrong-answer patterns and diagnoses pedagogical misconceptions dynamically across any subject."""

    def analyze_mistakes(
        self,
        recent_wrong_attempts: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Analyzes a sequence of incorrect attempts.
        If a student repeatedly misses questions on a particular concept or distractor pattern,
        identifies the likely misconception and prescribes targeted remediation.
        """
        if not recent_wrong_attempts or len(recent_wrong_attempts) < 2:
            return None

        # Check concept clusters
        concept_counts = Counter(a.get("concept_name", "") for a in recent_wrong_attempts if a.get("concept_name"))
        if not concept_counts:
            return None

        most_common_concept, count = concept_counts.most_common(1)[0]

        if count >= 2 and most_common_concept:
            topic_name = recent_wrong_attempts[0].get("topic_name", "Core Curriculum")
            
            # Analyze distractor patterns if available
            selected_distractors = [a.get("selected_answer", "") for a in recent_wrong_attempts if a.get("concept_name") == most_common_concept]
            common_distractor = Counter(selected_distractors).most_common(1)[0][0] if selected_distractors else "Alternative"

            misconception_title = f"Distractor Pattern '{common_distractor}' in {most_common_concept}"
            remediation = (
                f"Review the foundational definitions and boundary conditions of '{most_common_concept}' in {topic_name}. "
                f"Pay particular attention to edge cases that differentiate correct states from distractor conditions, "
                f"followed by 2 scaffolded practice questions."
            )

            return {
                "detected": True,
                "concept": most_common_concept,
                "misconception_title": misconception_title,
                "occurrences": count,
                "remediation_guidance": remediation,
                "recommended_action": "prerequisite_review_and_scaffolded_quiz"
            }

        return None

misconception_detector = MisconceptionDetector()
