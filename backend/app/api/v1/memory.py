from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from backend.app.database.session import get_db_session
from backend.app.database.models.learner import EpisodicMemory, LearnerProfile
from backend.app.core.exceptions import format_success_response

router = APIRouter(prefix="/memory", tags=["Memory & Feedback"])

class FeedbackRequest(BaseModel):
    user_id: Optional[str] = None
    category: str = "explanation_style" # 'explanation_style', 'difficulty', 'content_gap'
    rating: int = 5 # 1 to 5
    comment: str = ""

@router.get("/relevant")
async def get_user_memory(
    user_id: Optional[str] = None,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Exposes safe, user-facing memory view:
    - Long-term learning traits and preferences
    - Episodic memory moments (breakthroughs, misconceptions resolved)
    - Strict privacy: No internal chain-of-thought exposed.
    """
    if not user_id:
        from backend.app.database.models.user import User
        u_res = await session.execute(select(User).order_by(User.last_active_at.desc()).limit(1))
        latest_u = u_res.scalar_one_or_none()
        user_id = latest_u.id if latest_u else "anonymous-student"

    prof_res = await session.execute(select(LearnerProfile).where(LearnerProfile.user_id == user_id))
    profile = prof_res.scalar_one_or_none()

    ep_res = await session.execute(
        select(EpisodicMemory)
        .where(EpisodicMemory.user_id == user_id)
        .order_by(desc(EpisodicMemory.timestamp))
        .limit(10)
    )
    episodes = ep_res.scalars().all()

    # User-facing episodic learning journey
    journey = [
        {
            "id": ep.id,
            "topic": ep.topic,
            "concept": ep.concept,
            "event_type": ep.event_type.replace("_", " ").title(),
            "evidence": ep.evidence,
            "result": ep.result,
            "date": ep.timestamp.strftime("%b %d, %H:%M")
        }
        for ep in episodes
    ]

    return format_success_response({
        "learner_behavior_profile": profile.learning_behavior if profile else {},
        "learning_episodes": journey,
        "memory_summary": "System maintains 3 memory layers: short-term active session context, long-term concept masteries, and episodic learning breakthroughs."
    })

@router.post("/feedback")
async def submit_student_feedback(
    payload: FeedbackRequest,
    session: AsyncSession = Depends(get_db_session)
):
    target_user_id = payload.user_id
    if not target_user_id:
        from backend.app.database.models.user import User
        u_res = await session.execute(select(User).order_by(User.last_active_at.desc()).limit(1))
        latest_u = u_res.scalar_one_or_none()
        target_user_id = latest_u.id if latest_u else "anonymous-student"

    prof_res = await session.execute(select(LearnerProfile).where(LearnerProfile.user_id == target_user_id))
    profile = prof_res.scalar_one_or_none()
    if profile:
        behavior = dict(profile.learning_behavior or {})
        if "concise" in payload.comment.lower():
            behavior["explanation_preference"] = "concise"
        elif "step" in payload.comment.lower():
            behavior["explanation_preference"] = "step_by_step"
        profile.learning_behavior = behavior
        await session.commit()

    return format_success_response({
        "message": "Feedback received and integrated into learning profile."
    })
