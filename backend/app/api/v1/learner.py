from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional, List, Dict, Any

from backend.app.database.session import get_db_session
from backend.app.database.models.learner import LearnerProfile, TopicMastery, EpisodicMemory, StudySession
from backend.app.database.models.knowledge import Topic, Concept
from backend.app.learner_model.classification import readiness_classifier
from backend.app.learner_model.regression import learning_time_regressor
from backend.app.core.exceptions import format_success_response, EntityNotFoundError

router = APIRouter(prefix="/learner", tags=["Learner Profile & Modeling"])

async def _resolve_user_id(user_id: Optional[str], session: AsyncSession) -> str:
    if user_id:
        return user_id
    from backend.app.database.models.user import User
    u_res = await session.execute(select(User).order_by(User.last_active_at.desc()).limit(1))
    latest_u = u_res.scalar_one_or_none()
    return latest_u.id if latest_u else "anonymous-student"

@router.get("/profile")
async def get_learner_profile(
    user_id: Optional[str] = None,
    session: AsyncSession = Depends(get_db_session)
):
    target_uid = await _resolve_user_id(user_id, session)
    result = await session.execute(select(LearnerProfile).where(LearnerProfile.user_id == target_uid))
    profile = result.scalar_one_or_none()
    if not profile:
        return format_success_response({
            "user_id": target_uid,
            "status": "uncalibrated",
            "overall_mastery": 0.0,
            "learning_behavior": {
                "explanation_preference": "balanced_scaffolded",
                "pacing": "moderate"
            },
            "total_active_study_minutes": 0.0,
            "total_questions_answered": 0,
            "total_assessments_completed": 0,
            "is_cold_start": True
        })

    return format_success_response({
        "user_id": profile.user_id,
        "status": profile.status,
        "overall_mastery": profile.overall_mastery,
        "learning_behavior": profile.learning_behavior,
        "total_active_study_minutes": profile.total_active_study_minutes,
        "total_questions_answered": profile.total_questions_answered,
        "total_assessments_completed": profile.total_assessments_completed,
        "is_cold_start": (profile.status == "uncalibrated")
    })

@router.get("/mastery")
async def get_topic_mastery(
    user_id: Optional[str] = None,
    session: AsyncSession = Depends(get_db_session)
):
    """Returns fine-grained BKT mastery across all concepts with confidence levels."""
    target_uid = await _resolve_user_id(user_id, session)
    result = await session.execute(
        select(TopicMastery, Concept.name, Concept.difficulty_level, Topic.title)
        .join(Concept, TopicMastery.concept_id == Concept.id, isouter=True)
        .join(Topic, TopicMastery.topic_id == Topic.id, isouter=True)
        .where(TopicMastery.user_id == target_uid)
        .order_by(TopicMastery.mastery.asc())
    )
    rows = result.all()

    masteries = []
    for tm, c_name, c_diff, t_title in rows:
        masteries.append({
            "id": tm.id,
            "concept_name": c_name or "General Concept",
            "topic_title": t_title or "General Topic",
            "difficulty": c_diff or "medium",
            "mastery_score": round(tm.mastery * 100.0, 1),
            "raw_mastery": tm.mastery,
            "confidence": round(tm.confidence * 100.0, 1),
            "evidence_count": tm.evidence_count,
            "correct_count": tm.correct_count,
            "incorrect_count": tm.incorrect_count,
            "last_interaction": tm.last_interaction.isoformat() if tm.last_interaction else None
        })

    # Return true empty array for brand-new students with zero recorded interactions
    return format_success_response(masteries)

@router.get("/predictions")
async def get_ml_predictions(
    user_id: Optional[str] = None,
    concept_name: Optional[str] = None,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Executes actual scikit-learn models:
    - Random Forest: Pedagogical Readiness Classification
    - Gradient Boosting: Learning Time & Expected Quiz Score Regression
    """
    target_uid = await _resolve_user_id(user_id, session)
    target_concept = concept_name or "Core Principles"

    # Fetch user mastery
    res = await session.execute(
        select(TopicMastery)
        .where(TopicMastery.user_id == target_uid)
        .order_by(TopicMastery.last_interaction.desc())
    )
    latest_tm = res.scalars().first()
    curr_mast = latest_tm.mastery if latest_tm else 0.20

    # Run ML Classifier
    readiness = readiness_classifier.predict_readiness(
        current_mastery=curr_mast,
        prereq_mastery=0.60,
        accuracy_rate=0.50
    )

    # Run ML Regressor
    time_pred = learning_time_regressor.predict(
        current_mastery=curr_mast,
        target_mastery=0.80,
        difficulty="medium"
    )

    return format_success_response({
        "concept": target_concept,
        "readiness_classification": readiness,
        "time_to_mastery_regression": time_pred
    })

@router.get("/recommendations")
async def get_recommendations(
    user_id: Optional[str] = None,
    session: AsyncSession = Depends(get_db_session)
):
    target_uid = await _resolve_user_id(user_id, session)
    # Retrieve weak topics
    result = await session.execute(
        select(TopicMastery, Concept.name, Topic.title)
        .join(Concept, TopicMastery.concept_id == Concept.id, isouter=True)
        .join(Topic, TopicMastery.topic_id == Topic.id, isouter=True)
        .where(TopicMastery.user_id == target_uid)
        .order_by(TopicMastery.mastery.asc())
        .limit(3)
    )
    rows = result.all()

    recs = []
    if rows:
        for tm, c_name, t_title in rows:
            c = c_name or "Foundations"
            t = t_title or "Course Curriculum"
            recs.append({
                "title": f"Reinforce {c}",
                "topic": t,
                "reason": f"Current mastery is at {round(tm.mastery * 100)}%. Targeted review will solidify downstream comprehension.",
                "action_type": "adaptive_quiz",
                "urgency": "high" if tm.mastery < 0.4 else "medium"
            })
    else:
        # Subject-neutral cold-start recommendations
        recs = [
            {
                "title": "Add or Select a Course Resource",
                "topic": "Getting Started",
                "reason": "Upload textbooks, lecture slides, notes, or videos to construct your knowledge map.",
                "action_type": "add_course",
                "urgency": "high"
            },
            {
                "title": "Complete Baseline Diagnostic",
                "topic": "Calibration",
                "reason": "Take a 3-question diagnostic assessment once material is uploaded to establish initial mastery.",
                "action_type": "diagnostic_test",
                "urgency": "medium"
            }
        ]

    return format_success_response(recs)
