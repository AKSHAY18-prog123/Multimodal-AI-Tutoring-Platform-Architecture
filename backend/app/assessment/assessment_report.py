from typing import List, Dict, Any
from backend.app.learner_model.misconception_detector import misconception_detector

class AssessmentReportService:
    """Generates detailed diagnostic post-assessment report with mastery deltas and recommendations."""

    def generate_report(
        self,
        assessment_id: str,
        attempts: List[Dict[str, Any]],
        mastery_before: Dict[str, float],
        mastery_after: Dict[str, float],
        total_time_seconds: float = 0.0
    ) -> Dict[str, Any]:
        total_q = len(attempts)
        correct_q = sum(1 for a in attempts if a.get("is_correct", False))
        accuracy = (correct_q / max(1, total_q)) * 100.0

        # Performance by concept
        concept_perf = {}
        difficulty_perf = {}
        wrong_attempts = []

        for a in attempts:
            c = a.get("concept_name", "General")
            diff = a.get("difficulty", "medium")
            is_corr = a.get("is_correct", False)

            if c not in concept_perf:
                concept_perf[c] = {"total": 0, "correct": 0}
            concept_perf[c]["total"] += 1
            if is_corr:
                concept_perf[c]["correct"] += 1
            else:
                wrong_attempts.append(a)

            if diff not in difficulty_perf:
                difficulty_perf[diff] = {"total": 0, "correct": 0}
            difficulty_perf[diff]["total"] += 1
            if is_corr:
                difficulty_perf[diff]["correct"] += 1

        # Calculate mastery deltas
        mastery_changes = []
        for c, m_after in mastery_after.items():
            m_before = mastery_before.get(c, 0.15)
            delta = m_after - m_before
            mastery_changes.append({
                "concept": c,
                "before": round(m_before * 100.0, 1),
                "after": round(m_after * 100.0, 1),
                "improvement": round(delta * 100.0, 1),
                "direction": "up" if delta >= 0 else "down"
            })

        # Detect misconceptions
        misconception_diag = misconception_detector.analyze_mistakes(wrong_attempts)

        # Categorize strong vs weak concepts
        weak_concepts = [c for c, data in concept_perf.items() if (data["correct"] / data["total"]) < 0.6]
        strong_concepts = [c for c, data in concept_perf.items() if (data["correct"] / data["total"]) >= 0.8]

        # Recommendations
        recommendations = []
        if misconception_diag:
            recommendations.append({
                "action": "remedy_misconception",
                "title": f"Address: {misconception_diag['misconception_title']}",
                "guidance": misconception_diag["remediation_guidance"]
            })
        elif weak_concepts:
            recommendations.append({
                "action": "review_weak_concepts",
                "title": f"Review {weak_concepts[0]}",
                "guidance": f"Your accuracy was low in {weak_concepts[0]}. Review the foundational course slides and attempt 3 targeted practice questions."
            })
        else:
            recommendations.append({
                "action": "advance_curriculum",
                "title": "Mastery Achieved",
                "guidance": "Outstanding performance! You are ready to advance to downstream concepts in the course graph."
            })

        return {
            "assessment_id": assessment_id,
            "total_questions": total_q,
            "correct_answers": correct_q,
            "accuracy_percentage": round(accuracy, 1),
            "score_percentage": round(accuracy, 1),
            "total_time_seconds": round(total_time_seconds, 1),
            "avg_time_per_question": round(total_time_seconds / max(1, total_q), 1),
            "concept_performance": {
                c: {
                    "accuracy": round((d["correct"] / d["total"]) * 100.0, 1),
                    "total": d["total"]
                }
                for c, d in concept_perf.items()
            },
            "difficulty_performance": {
                diff: {
                    "accuracy": round((d["correct"] / d["total"]) * 100.0, 1),
                    "total": d["total"]
                }
                for diff, d in difficulty_perf.items()
            },
            "mastery_changes": mastery_changes,
            "weak_concepts": weak_concepts,
            "strong_concepts": strong_concepts,
            "misconception_diagnostic": misconception_diag,
            "recommendations": recommendations
        }

assessment_reporter = AssessmentReportService()
