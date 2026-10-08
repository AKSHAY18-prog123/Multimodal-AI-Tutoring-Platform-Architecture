from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from backend.app.database.models.learner import EpisodicMemory
from backend.app.core.logging import logger

class EpisodicMemoryManager:
    """Manages recording and semantic retrieval of critical learning events."""

    async def record_episode(
        self,
        user_id: str,
        topic: str,
        concept: str,
        event_type: str,
        evidence: str,
        result: str,
        session: AsyncSession
    ) -> EpisodicMemory:
        episode = EpisodicMemory(
            user_id=user_id,
            topic=topic,
            concept=concept,
            event_type=event_type,
            evidence=evidence,
            result=result,
            context_summary=f"Student {event_type} on {concept} in topic {topic}: {evidence} Result: {result}.",
            timestamp=datetime.now(timezone.utc)
        )
        session.add(episode)
        await session.commit()
        await session.refresh(episode)
        logger.info(f"Recorded episodic memory: {event_type} on {concept} for user {user_id}")
        return episode

    async def get_episodes_for_topic(
        self,
        user_id: str,
        topic: str,
        session: AsyncSession,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Retrieves recent learning episodes relating to a given topic or concept."""
        result = await session.execute(
            select(EpisodicMemory)
            .where(EpisodicMemory.user_id == user_id)
            .order_by(desc(EpisodicMemory.timestamp))
            .limit(limit)
        )
        episodes = result.scalars().all()
        return [
            {
                "id": ep.id,
                "topic": ep.topic,
                "concept": ep.concept,
                "event_type": ep.event_type,
                "evidence": ep.evidence,
                "result": ep.result,
                "timestamp": ep.timestamp.isoformat()
            }
            for ep in episodes
        ]

episodic_memory_manager = EpisodicMemoryManager()
