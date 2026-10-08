from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Dict, Any, Optional, List

from backend.app.database.session import get_db_session
from backend.app.database.models.assessment import Assessment, QuestionAttempt
from backend.app.database.models.learner import LearnerProfile, TopicMastery, StudySession
from backend.app.assessment.novelty_checker import novelty_checker
from backend.app.core.exceptions import format_success_response

router = APIRouter(prefix="/analytics", tags=["Analytics & Progress"])

@router.get("/progress")
async def get_analytics_progress(
    user_id: Optional[str] = None,
    session: AsyncSession = Depends(get_db_session)
):
    if not user_id:
        from backend.app.database.models.user import User
        u_res = await session.execute(select(User).order_by(User.last_active_at.desc()).limit(1))
        latest_u = u_res.scalar_one_or_none()
        user_id = latest_u.id if latest_u else "anonymous-student"

    # Fetch Assessments
    a_res = await session.execute(
        select(Assessment)
        .where(Assessment.user_id == user_id, Assessment.status == "completed")
        .order_by(Assessment.completed_at.asc())
    )
    assessments = a_res.scalars().all()

    # Quiz scores history
    score_history = [
        {
            "id": a.id,
            "title": a.title,
            "score": a.score,
            "accuracy": a.accuracy,
            "date": a.completed_at.strftime("%b %d, %H:%M") if a.completed_at else "Recently"
        }
        for a in assessments
    ]

    # Fetch Learner Profile
    prof_res = await session.execute(select(LearnerProfile).where(LearnerProfile.user_id == user_id))
    profile = prof_res.scalar_one_or_none()

    # Study time breakdown
    active_mins = profile.total_active_study_minutes if profile else 0.0
    reading_mins = round(active_mins * 0.6, 1)
    answering_mins = round(active_mins * 0.4, 1)
    overall_mast = int((profile.overall_mastery if profile else 0.0) * 100)

    # Mastery over time trajectory from real student assessments
    mastery_timeline = []
    if assessments:
        for idx, a in enumerate(assessments):
            label = f"Assessment {idx + 1}"
            mastery_timeline.append({"session": label, "mastery": int(a.score or 0)})
        mastery_timeline.append({"session": "Current", "mastery": overall_mast})
    elif overall_mast > 0:
        mastery_timeline.append({"session": "Current", "mastery": overall_mast})

    novelty_stats = novelty_checker.get_novelty_metrics()

    gains_str = "Baseline calibration in progress"
    if len(assessments) >= 2:
        diff = int(assessments[-1].score or 0) - int(assessments[0].score or 0)
        gains_str = f"+{diff}% Mastery Gain" if diff >= 0 else f"{diff}% Variance"
    elif len(assessments) == 1:
        gains_str = f"First Assessment Completed ({int(assessments[0].score or 0)}%)"

    return format_success_response({
        "overall_mastery_pct": overall_mast,
        "assessments_completed": len(assessments),
        "total_study_minutes": active_mins,
        "reading_minutes": reading_mins,
        "answering_minutes": answering_mins,
        "score_history": score_history,
        "mastery_timeline": mastery_timeline,
        "novelty_metrics": novelty_stats,
        "learning_gains": gains_str
    })
