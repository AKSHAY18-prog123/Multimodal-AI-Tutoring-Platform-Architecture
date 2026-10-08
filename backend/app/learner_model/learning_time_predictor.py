from typing import Dict, Any, List
from datetime import datetime, timezone

class LearningTimeTracker:
    """Tracks active reading time, answering time, and calculates historical learning velocities."""

    def compute_session_summary(
        self,
        session_start: datetime,
        session_end: datetime,
        reading_seconds: float,
        answering_seconds: float,
        question_attempts: int,
        initial_mastery: float,
        final_mastery: float
    ) -> Dict[str, Any]:
        total_seconds = max(1.0, (session_end - session_start).total_seconds())
        active_study_seconds = reading_seconds + answering_seconds
        mastery_delta = final_mastery - initial_mastery

        # Velocity: mastery gain per 10 minutes of active study
        gain_per_10min = 0.0
        if active_study_seconds > 60:
            gain_per_10min = (mastery_delta / (active_study_seconds / 600.0))

        return {
            "total_session_minutes": round(total_seconds / 60.0, 1),
            "active_study_minutes": round(active_study_seconds / 60.0, 1),
            "reading_minutes": round(reading_seconds / 60.0, 1),
            "answering_minutes": round(answering_seconds / 60.0, 1),
            "questions_answered": question_attempts,
            "avg_seconds_per_question": round(answering_seconds / max(1, question_attempts), 1),
            "initial_mastery": round(initial_mastery, 3),
            "final_mastery": round(final_mastery, 3),
            "mastery_gain": round(mastery_delta, 3),
            "learning_velocity_per_10m": round(gain_per_10min, 3)
        }

learning_time_tracker = LearningTimeTracker()
