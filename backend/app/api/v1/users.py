from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid

from backend.app.database.session import get_db_session
from backend.app.database.models.user import User
from backend.app.database.models.learner import LearnerProfile
from backend.app.core.exceptions import format_success_response, EntityNotFoundError
from backend.app.core.logging import logger
from backend.app.responses.user_responses import OnboardRequest, UserUpdateRequest

router = APIRouter(prefix="/users", tags=["Users & Onboarding"])

@router.get("/status")
async def get_user_status(
    user_id: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Detects whether a student profile already exists.
    Used on initial application load to direct the student to Onboarding or Dashboard.
    """
    if user_id:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            return format_success_response({
                "exists": True,
                "onboarding_completed": bool(user.onboarding_completed),
                "user": {
                    "id": user.id,
                    "name": user.full_name,
                    "email": user.email,
                    "created_at": user.created_at.isoformat() if user.created_at else None
                }
            })

    # If no user_id passed, check if any registered user exists in DB
    result = await session.execute(select(User).order_by(User.created_at.desc()).limit(1))
    latest_user = result.scalar_one_or_none()

    if latest_user:
        return format_success_response({
            "exists": True,
            "onboarding_completed": bool(latest_user.onboarding_completed),
            "user": {
                "id": latest_user.id,
                "name": latest_user.full_name,
                "email": latest_user.email,
                "created_at": latest_user.created_at.isoformat() if latest_user.created_at else None
            }
        })

    return format_success_response({
        "exists": False,
        "onboarding_completed": False,
        "user": None
    })

@router.post("/onboard")
async def onboard_student(
    payload: OnboardRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Onboards a first-time student:
    - Stores their name in the database
    - Initializes a clean uncalibrated learner profile (zero fake data)
    - Returns the new user record
    """
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Student name cannot be empty.")

    new_id = payload.user_id or str(uuid.uuid4())

    # Check if user with this ID exists
    existing = await session.execute(select(User).where(User.id == new_id))
    user = existing.scalar_one_or_none()

    if not user:
        user = User(
            id=new_id,
            full_name=name,
            email=payload.email,
            onboarding_completed=True,
            last_active_at=datetime.now(timezone.utc)
        )
        session.add(user)
        await session.flush()

        # Create clean, uncalibrated learner profile (no fake mastery or fake metrics)
        profile = LearnerProfile(
            user_id=user.id,
            status="uncalibrated",
            overall_mastery=0.0,
            total_active_study_minutes=0.0,
            total_questions_answered=0,
            total_assessments_completed=0,
            learning_behavior={
                "explanation_preference": "balanced_scaffolded",
                "prefers_examples_before_theory": True,
                "prefers_formal_math": False,
                "pacing": "moderate",
                "common_struggles": [],
                "strengths": []
            }
        )
        session.add(profile)
        await session.commit()
        await session.refresh(user)
        logger.info(f"Successfully onboarded new student: {user.full_name} ({user.id})")
    else:
        user.full_name = name
        user.onboarding_completed = True
        user.last_active_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(user)

    return format_success_response({
        "id": user.id,
        "name": user.full_name,
        "email": user.email,
        "onboarding_completed": user.onboarding_completed,
        "created_at": user.created_at.isoformat() if user.created_at else None
    })

@router.get("/me")
async def get_current_user(
    user_id: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db_session)
):
    """Returns profile for currently active student."""
    if not user_id:
        # Fallback to latest active user
        result = await session.execute(select(User).order_by(User.last_active_at.desc()).limit(1))
        user = result.scalar_one_or_none()
    else:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="No active student found.")

    return format_success_response({
        "id": user.id,
        "name": user.full_name,
        "email": user.email,
        "onboarding_completed": user.onboarding_completed,
        "created_at": user.created_at.isoformat() if user.created_at else None
    })

@router.get("")
async def list_students(session: AsyncSession = Depends(get_db_session)):
    """Lists all students in the database."""
    result = await session.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return format_success_response([
        {
            "id": u.id,
            "name": u.full_name,
            "email": u.email,
            "onboarding_completed": u.onboarding_completed,
            "created_at": u.created_at.isoformat() if u.created_at else None
        }
        for u in users
    ])
