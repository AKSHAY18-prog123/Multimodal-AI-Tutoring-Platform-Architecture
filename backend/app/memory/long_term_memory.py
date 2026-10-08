from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.database.models.learner import LearnerProfile, TopicMastery
from backend.app.database.models.knowledge import Topic

class LongTermMemoryManager:
    """Manages persistent learner profile, behavioral preferences, and topic masteries."""

    async def get_learner_context(self, user_id: str, session: AsyncSession) -> Dict[str, Any]:
        """Loads non-sensitive learner behavior profile and mastery highlights."""
        result = await session.execute(
            select(LearnerProfile).where(LearnerProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()

        # Load weak and strong topics
        mastery_result = await session.execute(
            select(TopicMastery, Topic.title)
            .join(Topic, TopicMastery.topic_id == Topic.id, isouter=True)
            .where(TopicMastery.user_id == user_id)
        )
        mastery_rows = mastery_result.all()

        strong_topics = []
        weak_topics = []
        for row in mastery_rows:
            tm, t_title = row
            name = t_title or "General"
            if tm.mastery >= 0.75:
                strong_topics.append({"topic": name, "mastery": tm.mastery})
            elif tm.mastery < 0.50:
                weak_topics.append({"topic": name, "mastery": tm.mastery})

        behavior = profile.learning_behavior if profile else {
            "explanation_preference": "balanced_scaffolded",
            "prefers_examples_before_theory": True,
            "prefers_formal_math": False
        }

        return {
            "status": profile.status if profile else "uncalibrated",
            "overall_mastery": profile.overall_mastery if profile else 0.15,
            "behavior": behavior,
            "strong_topics": strong_topics,
            "weak_topics": weak_topics,
            "total_study_minutes": profile.total_active_study_minutes if profile else 0.0
        }

    async def update_behavior_preference(
        self,
        user_id: str,
        preference_key: str,
        value: Any,
        session: AsyncSession
    ):
        result = await session.execute(
            select(LearnerProfile).where(LearnerProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if profile:
            current_behavior = dict(profile.learning_behavior or {})
            current_behavior[preference_key] = value
            profile.learning_behavior = current_behavior
            await session.commit()

long_term_memory = LongTermMemoryManager()
