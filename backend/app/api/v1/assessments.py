from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid

from backend.app.database.session import get_db_session
from backend.app.database.models.assessment import Question, Assessment, AssessmentQuestion, QuestionAttempt
from backend.app.database.models.knowledge import Concept, Topic
from backend.app.database.models.learner import LearnerProfile, TopicMastery
from backend.app.assessment.question_generator import question_generator
from backend.app.assessment.question_verifier import question_verifier
from backend.app.assessment.novelty_checker import novelty_checker
from backend.app.assessment.adaptive_selector import adaptive_selector
from backend.app.assessment.assessment_report import assessment_reporter
from backend.app.learner_model.knowledge_tracing import bkt_engine
from backend.app.memory.episodic_memory import episodic_memory_manager
from backend.app.core.exceptions import format_success_response, EntityNotFoundError

router = APIRouter(prefix="/assessments", tags=["Assessments"])

class GenerateAssessmentRequest(BaseModel):
    user_id: Optional[str] = None
    course_id: Optional[str] = None
    topic_id: Optional[str] = None
    custom_prompt: Optional[str] = None  # Specific module, topic, or focus instruction requested by user
    question_type: str = "mcq"  # 'mcq', 'tf', 'mixed'
    difficulty: str = "medium"
    question_count: int = 5
    duration_minutes: int = 15
    is_diagnostic: bool = False # Fast placement pre-test for brand new students!

class SubmitAnswerItem(BaseModel):
    question_id: str
    selected_answer: str
    time_taken_seconds: float = 30.0

class SubmitAssessmentRequest(BaseModel):
    user_id: Optional[str] = None
    answers: List[SubmitAnswerItem]

@router.post("/generate")
async def generate_assessment(
    payload: GenerateAssessmentRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Adaptive Assessment Generator:
    Connects to course modules/topics or user custom focus prompt, generates verified questions,
    applies learner mastery weights or cold-start baseline, and returns ready assessment.
    """
    # 1. Fetch Learner State & Masteries
    user_id = payload.user_id or "anonymous-student"
    prof_res = await session.execute(select(LearnerProfile).where(LearnerProfile.user_id == user_id))
    profile = prof_res.scalar_one_or_none()
    is_cold_start = payload.is_diagnostic or (profile and profile.status == "uncalibrated")

    # Fetch concept masteries
    mast_res = await session.execute(
        select(TopicMastery, Concept.name)
        .join(Concept, TopicMastery.concept_id == Concept.id, isouter=True)
        .where(TopicMastery.user_id == user_id)
    )
    concept_masteries = {row[1]: row[0].mastery for row in mast_res.all() if row[1]}

    # 2. Fetch or Generate Candidate Questions
    topic_title = "General Assessment"
    if payload.custom_prompt and payload.custom_prompt.strip():
        topic_title = payload.custom_prompt.strip()
    elif payload.topic_id:
        t_res = await session.execute(select(Topic).where(Topic.id == payload.topic_id))
        t_obj = t_res.scalar_one_or_none()
        if t_obj:
            topic_title = t_obj.title
    elif payload.course_id:
        c_res = await session.execute(select(Course).where(Course.id == payload.course_id))
        c_obj = c_res.scalar_one_or_none()
        if c_obj:
            topic_title = c_obj.title

    # Query existing verified questions in the bank
    q_query = select(Question).where(Question.verification_status == "verified")
    if payload.custom_prompt:
        q_query = q_query.where(Question.topic_name.ilike(f"%{topic_title}%"))
    elif payload.topic_id:
        q_query = q_query.where(Question.topic_name == topic_title)
    existing_res = await session.execute(q_query)
    existing_questions = existing_res.scalars().all()

    # If question bank has fewer questions than needed or user gave custom prompt, generate new questions
    needed_count = max(payload.question_count, 6)
    candidate_pool = [
        {
            "id": q.id,
            "question_text": q.question_text,
            "question_type": q.question_type,
            "difficulty": q.difficulty,
            "options": q.options,
            "correct_answer": q.correct_answer,
            "explanation": q.explanation,
            "topic_name": q.topic_name,
            "concept_name": q.concept_name,
            "novelty_hash": q.novelty_hash
        }
        for q in existing_questions
    ] if not payload.custom_prompt else []

    if len(candidate_pool) < needed_count:
        if payload.custom_prompt:
            discovered_concepts = [
                payload.custom_prompt,
                f"{payload.custom_prompt} Fundamentals",
                f"{payload.custom_prompt} Analysis & Methods",
                f"{payload.custom_prompt} Practical Problem Solving"
            ]
        else:
            # Fetch concepts dynamically from DB for this course or topic
            concept_query = select(Concept.name).join(Topic, Concept.topic_id == Topic.id)
            if payload.topic_id:
                concept_query = concept_query.where(Topic.id == payload.topic_id)
            elif payload.course_id:
                concept_query = concept_query.where(Topic.course_id == payload.course_id)
            
            c_res = await session.execute(concept_query.limit(8))
            discovered_concepts = [r[0] for r in c_res.all()]

            if not discovered_concepts:
                # Fallback to subject-neutral concept facets derived from topic title
                discovered_concepts = [
                    f"{topic_title} Fundamentals",
                    f"{topic_title} Mechanisms & Operations",
                    f"{topic_title} Analysis & Edge Cases",
                    f"{topic_title} Practical Application"
                ]

        for c_name in discovered_concepts:
            if len(candidate_pool) >= needed_count:
                break
            raw_q = await question_generator.generate_question(
                concept=c_name,
                topic=topic_title,
                difficulty=payload.difficulty
            )
            # Verify Question
            is_valid, msg, v_details = question_verifier.verify(raw_q)
            if is_valid:
                # Check Novelty
                is_novel, sim_score, n_msg = await novelty_checker.is_novel(raw_q["question"], candidate_pool)
                if is_novel:
                    db_q = Question(
                        question_text=raw_q["question"],
                        question_type=raw_q.get("question_type", "mcq"),
                        difficulty=raw_q.get("difficulty", payload.difficulty),
                        options=raw_q.get("options", []),
                        correct_answer=str(raw_q["correct_answer"]),
                        explanation=raw_q.get("explanation", ""),
                        topic_name=topic_title,
                        concept_name=c_name,
                        verification_status="verified",
                        verification_details=v_details,
                        novelty_hash=sim_score
                    )
                    session.add(db_q)
                    await session.flush()
                    candidate_pool.append({
                        "id": db_q.id,
                        "question_text": db_q.question_text,
                        "question_type": db_q.question_type,
                        "difficulty": db_q.difficulty,
                        "options": db_q.options,
                        "correct_answer": db_q.correct_answer,
                        "explanation": db_q.explanation,
                        "topic_name": db_q.topic_name,
                        "concept_name": db_q.concept_name
                    })

    # 3. Adaptive Question Selection
    selected_questions = adaptive_selector.select_questions(
        candidate_questions=candidate_pool,
        concept_masteries=concept_masteries,
        count=payload.question_count,
        is_cold_start=is_cold_start
    )

    # 4. Create Assessment Record
    assessment = Assessment(
        user_id=user_id,
        course_id=payload.course_id,
        topic_id=payload.topic_id,
        title=f"{'Diagnostic Placement Test' if is_cold_start else 'Adaptive Quiz'}: {topic_title}",
        difficulty=payload.difficulty,
        duration_minutes=payload.duration_minutes,
        total_questions=len(selected_questions),
        status="in_progress"
    )
    session.add(assessment)
    await session.flush()

    for idx, q_dict in enumerate(selected_questions):
        aq = AssessmentQuestion(
            assessment_id=assessment.id,
            question_id=q_dict["id"],
            order_index=idx
        )
        session.add(aq)

    await session.commit()
    await session.refresh(assessment)

    # Exclude answers & explanations from response to prevent test cheating
    client_questions = [
        {
            "id": q["id"],
            "question_text": q["question_text"],
            "question_type": q["question_type"],
            "difficulty": q["difficulty"],
            "options": q.get("options", []),
            "topic_name": q["topic_name"],
            "concept_name": q["concept_name"]
        }
        for q in selected_questions
    ]

    return format_success_response({
        "assessment_id": assessment.id,
        "title": assessment.title,
        "difficulty": assessment.difficulty,
        "duration_minutes": assessment.duration_minutes,
        "total_questions": len(client_questions),
        "is_diagnostic": is_cold_start,
        "questions": client_questions
    })

@router.get("/{assessment_id}")
async def get_assessment(
    assessment_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    result = await session.execute(select(Assessment).where(Assessment.id == assessment_id))
    a = result.scalar_one_or_none()
    if not a:
        raise EntityNotFoundError("Assessment", assessment_id)

    # Fetch questions
    aq_res = await session.execute(
        select(AssessmentQuestion, Question)
        .join(Question, AssessmentQuestion.question_id == Question.id)
        .where(AssessmentQuestion.assessment_id == assessment_id)
        .order_by(AssessmentQuestion.order_index)
    )
    questions_data = []
    for aq, q in aq_res.all():
        q_item = {
            "id": q.id,
            "question_text": q.question_text,
            "question_type": q.question_type,
            "difficulty": q.difficulty,
            "options": q.options,
            "topic_name": q.topic_name,
            "concept_name": q.concept_name
        }
        if a.status == "completed":
            q_item["correct_answer"] = q.correct_answer
            q_item["explanation"] = q.explanation
        questions_data.append(q_item)

    return format_success_response({
        "id": a.id,
        "title": a.title,
        "status": a.status,
        "difficulty": a.difficulty,
        "duration_minutes": a.duration_minutes,
        "score": a.score,
        "accuracy": a.accuracy,
        "report": a.report_json,
        "questions": questions_data
    })

@router.post("/{assessment_id}/submit")
async def submit_assessment(
    assessment_id: str,
    payload: SubmitAssessmentRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Submits student responses, calculates exact scores, updates BKT mastery,
    diagnoses misconceptions, and outputs comprehensive post-assessment diagnostic report.
    """
    a_res = await session.execute(select(Assessment).where(Assessment.id == assessment_id))
    assessment = a_res.scalar_one_or_none()
    if not assessment:
        raise EntityNotFoundError("Assessment", assessment_id)

    user_id = payload.user_id or assessment.user_id or "anonymous-student"

    # 1. Fetch questions to grade
    answers_map = {ans.question_id: ans for ans in payload.answers}
    q_res = await session.execute(
        select(Question).where(Question.id.in_(list(answers_map.keys())))
    )
    questions = {q.id: q for q in q_res.scalars().all()}

    # 2. Grade attempts and track mastery before
    mastery_before = {}
    mastery_after = {}
    attempts_records = []
    total_time_taken = 0.0

    # Load existing masteries for user
    all_mast_res = await session.execute(
        select(TopicMastery, Concept.name)
        .join(Concept, TopicMastery.concept_id == Concept.id, isouter=True)
        .where(TopicMastery.user_id == user_id)
    )
    existing_mast_map = {row[1]: row[0] for row in all_mast_res.all() if row[1]}

    for q_id, ans in answers_map.items():
        q_obj = questions.get(q_id)
        if not q_obj:
            continue

        selected = ans.selected_answer.strip()
        correct = q_obj.correct_answer.strip()
        is_correct = (selected.lower() == correct.lower())
        total_time_taken += ans.time_taken_seconds

        concept_name = q_obj.concept_name

        # BKT Mastery Update
        tm = existing_mast_map.get(concept_name)
        curr_p_l = tm.mastery if tm else 0.15
        mastery_before[concept_name] = curr_p_l

        new_p_l, delta = bkt_engine.update_mastery(
            current_p_l=curr_p_l,
            is_correct=is_correct,
            evidence_weight=1.0 # Assessment question has full evidence weight
        )
        mastery_after[concept_name] = new_p_l

        if tm:
            tm.mastery = new_p_l
            tm.evidence_count += 1
            if is_correct:
                tm.correct_count += 1
                tm.last_correct_at = datetime.now(timezone.utc)
            else:
                tm.incorrect_count += 1
                tm.last_incorrect_at = datetime.now(timezone.utc)
            tm.confidence = bkt_engine.calculate_confidence(tm.evidence_count)
            tm.last_interaction = datetime.now(timezone.utc)
        else:
            # Create new TopicMastery entry
            new_tm = TopicMastery(
                user_id=user_id,
                mastery=new_p_l,
                evidence_count=1,
                correct_count=1 if is_correct else 0,
                incorrect_count=0 if is_correct else 1,
                confidence=bkt_engine.calculate_confidence(1)
            )
            session.add(new_tm)
            existing_mast_map[concept_name] = new_tm

        # Record Question Attempt
        attempt = QuestionAttempt(
            user_id=user_id,
            assessment_id=assessment_id,
            question_id=q_id,
            selected_answer=selected,
            is_correct=is_correct,
            time_taken_seconds=ans.time_taken_seconds
        )
        session.add(attempt)

        attempts_records.append({
            "question_id": q_id,
            "concept_name": concept_name,
            "topic_name": q_obj.topic_name,
            "difficulty": q_obj.difficulty,
            "is_correct": is_correct,
            "selected_answer": selected,
            "correct_answer": correct,
            "time_taken_seconds": ans.time_taken_seconds
        })

    # 3. Generate Diagnostic Report
    report = assessment_reporter.generate_report(
        assessment_id=assessment_id,
        attempts=attempts_records,
        mastery_before=mastery_before,
        mastery_after=mastery_after,
        total_time_seconds=total_time_taken
    )

    # 4. Update Assessment Status
    assessment.status = "completed"
    assessment.score = report["score_percentage"]
    assessment.accuracy = report["accuracy_percentage"]
    assessment.report_json = report
    assessment.completed_at = datetime.now(timezone.utc)

    # 5. Update Learner Profile status (graduate from uncalibrated!)
    prof_res = await session.execute(select(LearnerProfile).where(LearnerProfile.user_id == user_id))
    profile = prof_res.scalar_one_or_none()
    if profile:
        profile.status = "active"
        profile.total_assessments_completed += 1
        profile.total_questions_answered += len(attempts_records)
        # Recalculate overall average mastery
        all_vals = list(mastery_after.values())
        if all_vals:
            profile.overall_mastery = round(sum(all_vals) / len(all_vals), 3)

    # 6. Record Episodic Memory if misconception or major improvement
    if report.get("misconception_diagnostic"):
        diag = report["misconception_diagnostic"]
        await episodic_memory_manager.record_episode(
            user_id=user_id,
            topic=assessment.title,
            concept=diag.get("concept", "General"),
            event_type="misconception_detected",
            evidence=diag.get("misconception_title", "Concept error"),
            result="struggling",
            session=session
        )

    await session.commit()
    return format_success_response(report)
