import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from backend.app.database.session import get_db_session
from backend.app.database.models.course import Course
from backend.app.database.models.document import Document
from backend.app.database.models.knowledge import Topic, Concept, ConceptRelationship
from backend.app.knowledge_base.prerequisite_graph import prerequisite_engine
from backend.app.core.exceptions import format_success_response, EntityNotFoundError

router = APIRouter(prefix="/courses", tags=["Courses"])

class CourseCreateRequest(BaseModel):
    title: str
    code: Optional[str] = None
    description: Optional[str] = None
    subject: Optional[str] = None
    user_id: Optional[str] = None

@router.post("")
async def create_course(
    payload: CourseCreateRequest,
    session: AsyncSession = Depends(get_db_session)
):
    course = Course(
        title=payload.title,
        code=payload.code,
        description=payload.description,
        subject=payload.subject,
        user_id=payload.user_id
    )
    session.add(course)
    await session.commit()
    await session.refresh(course)

    return format_success_response({
        "id": course.id,
        "title": course.title,
        "code": course.code,
        "description": course.description,
        "subject": course.subject,
        "user_id": course.user_id,
        "created_at": course.created_at.isoformat()
    })

@router.get("")
async def list_courses(
    user_id: Optional[str] = None,
    session: AsyncSession = Depends(get_db_session)
):
    query = select(Course).order_by(Course.created_at.desc())
    if user_id:
        query = query.where((Course.user_id == user_id) | (Course.user_id.is_(None)))
    result = await session.execute(query)
    courses = result.scalars().all()

    data = [
        {
            "id": c.id,
            "title": c.title,
            "code": c.code,
            "description": c.description,
            "subject": c.subject,
            "user_id": c.user_id,
            "created_at": c.created_at.isoformat()
        }
        for c in courses
    ]
    return format_success_response(data)

@router.get("/{course_id}")
async def get_course(course_id: str, session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise EntityNotFoundError("Course", course_id)

    # Fetch topics and concepts
    topics_res = await session.execute(
        select(Topic).where(Topic.course_id == course_id).order_by(Topic.order_index)
    )
    topics = topics_res.scalars().all()

    topic_data = []
    for t in topics:
        c_res = await session.execute(
            select(Concept).where(Concept.topic_id == t.id).order_by(Concept.order_index)
        )
        concepts = c_res.scalars().all()
        topic_data.append({
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "concepts": [
                {
                    "id": c.id,
                    "name": c.name,
                    "subtopic": c.subtopic,
                    "definition": c.definition,
                    "difficulty": c.difficulty_level
                }
                for c in concepts
            ]
        })

    return format_success_response({
        "id": course.id,
        "title": course.title,
        "code": course.code,
        "description": course.description,
        "subject": course.subject,
        "topics": topic_data
    })

@router.get("/{course_id}/knowledge-graph")
async def get_knowledge_graph(course_id: str, session: AsyncSession = Depends(get_db_session)):
    """Exports concept nodes and prerequisite directed edges for interactive knowledge graph rendering."""
    # Fetch course
    c_res = await session.execute(select(Course).where(Course.id == course_id))
    course = c_res.scalar_one_or_none()
    course_title = course.title if course else "Course Curriculum"

    # Fetch concepts for this course
    concepts_res = await session.execute(
        select(Concept, Topic.title)
        .join(Topic, Concept.topic_id == Topic.id)
        .where(Topic.course_id == course_id)
        .order_by(Concept.order_index)
    )
    rows = concepts_res.all()

    concepts_list = []
    concept_ids = set()
    for c, t_title in rows:
        concept_ids.add(c.id)
        concepts_list.append({
            "id": c.id,
            "name": c.name,
            "topic_id": c.topic_id,
            "topic_title": t_title or course_title,
            "difficulty_level": c.difficulty_level or "medium",
            "summary": c.summary or c.definition or f"Key concept under {t_title or course_title}."
        })

    # If no concepts exist under topics, fall back to topics as conceptual nodes
    if not concepts_list:
        t_res = await session.execute(
            select(Topic).where(Topic.course_id == course_id).order_by(Topic.order_index)
        )
        topics = t_res.scalars().all()
        for idx, t in enumerate(topics):
            tid = f"concept-{t.id}"
            concept_ids.add(tid)
            concepts_list.append({
                "id": tid,
                "name": t.title,
                "topic_id": t.id,
                "topic_title": t.title,
                "difficulty_level": "medium" if idx % 2 == 0 else "hard",
                "summary": t.description or f"Core curriculum module exploring {t.title} principles and applications."
            })

    # Fetch relationships
    rels_res = await session.execute(select(ConceptRelationship))
    relationships = [
        {
            "source_concept_id": r.source_concept_id,
            "target_concept_id": r.target_concept_id,
            "relationship_type": r.relationship_type,
            "strength": r.strength
        }
        for r in rels_res.scalars().all()
        if r.source_concept_id in concept_ids and r.target_concept_id in concept_ids
    ]

    prerequisite_engine.load_graph(concepts_list, relationships)
    graph_viz = prerequisite_engine.export_graph_visualization()

    return format_success_response(graph_viz)

@router.delete("/{course_id}")
async def delete_course(
    course_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    result = await session.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise EntityNotFoundError("Course", course_id)

    # Delete associated files on disk
    doc_res = await session.execute(select(Document).where(Document.course_id == course_id))
    docs = doc_res.scalars().all()
    for doc in docs:
        if doc.file_path and os.path.exists(doc.file_path):
            try:
                os.remove(doc.file_path)
            except Exception:
                pass

    # Delete all course vectors from ChromaDB
    try:
        from backend.app.knowledge_base.vector_store import vector_store
        vector_store.delete_by_course_id(course_id)
    except Exception as e:
        logger.error(f"Failed to delete ChromaDB vectors for course {course_id}: {e}")

    await session.delete(course)
    await session.commit()

    return format_success_response({
        "deleted": True,
        "course_id": course_id,
        "message": f"Course '{course.title}' and all associated materials were successfully deleted."
    })
