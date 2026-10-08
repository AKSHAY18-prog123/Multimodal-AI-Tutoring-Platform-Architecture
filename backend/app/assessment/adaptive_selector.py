from typing import List, Dict, Any
import random
from backend.app.core.logging import logger

class AdaptiveQuestionSelector:
    """
    Selects assessment questions adapting to student's current knowledge tracing state:
    50% Weak (< 50%), 30% Intermediate (50% - 75%), 20% Maintenance/Review (>= 75%).
    Handles Cold-Start by choosing foundational prerequisite concepts.
    """

    def select_questions(
        self,
        candidate_questions: List[Dict[str, Any]],
        concept_masteries: Dict[str, float], # {concept_name: mastery_score}
        count: int = 5,
        is_cold_start: bool = False
    ) -> List[Dict[str, Any]]:
        if not candidate_questions:
            return []

        if len(candidate_questions) <= count:
            return candidate_questions

        # 1. Cold-Start Protocol: Select easy / foundational questions
        if is_cold_start or not concept_masteries:
            logger.info("Cold-start adaptive selection: Prioritizing foundational concepts.")
            easy_pool = [q for q in candidate_questions if q.get("difficulty") in ["easy", "medium"]]
            if len(easy_pool) >= count:
                return random.sample(easy_pool, count)
            return random.sample(candidate_questions, count)

        # 2. Partition candidate questions by student's mastery in each concept
        weak_pool = []
        medium_pool = []
        strong_pool = []

        for q in candidate_questions:
            c_name = q.get("concept_name", "")
            mastery = concept_masteries.get(c_name, 0.50)
            if mastery < 0.50:
                weak_pool.append(q)
            elif mastery < 0.75:
                medium_pool.append(q)
            else:
                strong_pool.append(q)

        # Target quota: 50% weak, 30% medium, 20% review
        target_weak = max(1, int(round(count * 0.50)))
        target_med = max(1, int(round(count * 0.30)))
        target_strong = max(0, count - target_weak - target_med)

        selected = []

        def sample_from(pool: list, n: int):
            random.shuffle(pool)
            chosen = pool[:n]
            return chosen

        # Pull from weak pool
        w_chosen = sample_from(weak_pool, target_weak)
        selected.extend(w_chosen)

        # Pull from medium pool
        m_chosen = sample_from(medium_pool, target_med)
        selected.extend(m_chosen)

        # Pull from strong pool
        s_chosen = sample_from(strong_pool, target_strong)
        selected.extend(s_chosen)

        # Fill remaining if any pool was smaller than target quota
        if len(selected) < count:
            remaining_pool = [q for q in candidate_questions if q not in selected]
            needed = count - len(selected)
            selected.extend(sample_from(remaining_pool, needed))

        return selected[:count]

adaptive_selector = AdaptiveQuestionSelector()
