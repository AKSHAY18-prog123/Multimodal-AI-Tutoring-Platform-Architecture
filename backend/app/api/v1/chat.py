from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from backend.app.database.session import get_db_session
from backend.app.database.models.chat import ChatSession, ChatMessage
from backend.app.database.models.course import Course
from backend.app.memory.short_term_memory import short_term_memory
from backend.app.memory.long_term_memory import long_term_memory
from backend.app.memory.episodic_memory import episodic_memory_manager
from backend.app.rag.grounded_generation import grounded_generator
from backend.app.core.exceptions import format_success_response, EntityNotFoundError

router = APIRouter(prefix="/chat", tags=["Chat & Tutor"])

class CreateSessionRequest(BaseModel):
    user_id: Optional[str] = None
    course_id: Optional[str] = None
    title: Optional[str] = "New Conversation"
    topic: Optional[str] = None

class UpdateSessionRequest(BaseModel):
    title: Optional[str] = None
    pinned: Optional[bool] = None

class SendMessageRequest(BaseModel):
    user_id: Optional[str] = None
    message: str
    allow_outside_knowledge: bool = False

@router.post("/sessions")
async def create_chat_session(
    payload: CreateSessionRequest,
    session: AsyncSession = Depends(get_db_session)
):
    chat = ChatSession(
        user_id=payload.user_id or "anonymous-student",
        course_id=payload.course_id,
        title=payload.title or "New Conversation",
        topic=payload.topic,
        pinned=False
    )
    session.add(chat)
    await session.commit()
    await session.refresh(chat)

    return format_success_response({
        "id": chat.id,
        "user_id": chat.user_id,
        "course_id": chat.course_id,
        "title": chat.title,
        "topic": chat.topic,
        "pinned": chat.pinned,
        "created_at": chat.created_at.isoformat(),
        "updated_at": chat.updated_at.isoformat()
    })

@router.get("/sessions")
async def list_chat_sessions(
    user_id: Optional[str] = None,
    session: AsyncSession = Depends(get_db_session)
):
    query = select(ChatSession)
    if user_id:
        query = query.where(ChatSession.user_id == user_id)
    query = query.order_by(ChatSession.pinned.desc(), ChatSession.updated_at.desc())
    result = await session.execute(query)
    chats = result.scalars().all()

    return format_success_response([
        {
            "id": c.id,
            "title": c.title,
            "topic": c.topic,
            "summary": c.summary,
            "pinned": c.pinned,
            "course_id": c.course_id,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat()
        }
        for c in chats
    ])

@router.get("/sessions/{chat_id}")
async def get_chat_session(
    chat_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    result = await session.execute(select(ChatSession).where(ChatSession.id == chat_id))
    chat = result.scalar_one_or_none()
    if not chat:
        raise EntityNotFoundError("ChatSession", chat_id)

    # Fetch messages
    msg_res = await session.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == chat_id)
        .order_by(ChatMessage.created_at.asc())
    )
    messages = msg_res.scalars().all()

    return format_success_response({
        "id": chat.id,
        "title": chat.title,
        "topic": chat.topic,
        "summary": chat.summary,
        "pinned": chat.pinned,
        "course_id": chat.course_id,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "citations": m.citations or [],
                "is_outside_knowledge": m.is_outside_knowledge,
                "outside_knowledge_offered": m.outside_knowledge_offered,
                "suggested_followups": m.suggested_followups or [],
                "created_at": m.created_at.isoformat()
            }
            for m in messages
        ]
    })

@router.put("/sessions/{chat_id}")
async def update_chat_session(
    chat_id: str,
    payload: UpdateSessionRequest,
    session: AsyncSession = Depends(get_db_session)
):
    result = await session.execute(select(ChatSession).where(ChatSession.id == chat_id))
    chat = result.scalar_one_or_none()
    if not chat:
        raise EntityNotFoundError("ChatSession", chat_id)

    if payload.title is not None:
        chat.title = payload.title
    if payload.pinned is not None:
        chat.pinned = payload.pinned
    chat.updated_at = datetime.now(timezone.utc)

    await session.commit()
    return format_success_response({"message": "Session updated successfully."})

@router.delete("/sessions/{chat_id}")
async def delete_chat_session(
    chat_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    result = await session.execute(select(ChatSession).where(ChatSession.id == chat_id))
    chat = result.scalar_one_or_none()
    if not chat:
        raise EntityNotFoundError("ChatSession", chat_id)

    await session.delete(chat)
    await session.commit()
    return format_success_response({"message": "Session deleted."})

@router.post("/sessions/{chat_id}/messages")
async def send_chat_message(
    chat_id: str,
    payload: SendMessageRequest,
    session: AsyncSession = Depends(get_db_session)
):
    # 1. Fetch Session
    result = await session.execute(select(ChatSession).where(ChatSession.id == chat_id))
    chat = result.scalar_one_or_none()
    if not chat:
        raise EntityNotFoundError("ChatSession", chat_id)

    user_query = payload.message.strip()

    # Auto-generate title from first message if title is default
    if chat.title == "New Conversation" and len(user_query) > 0:
        clean_title = user_query[:32] + ("..." if len(user_query) > 32 else "")
        chat.title = clean_title

    # 2. Save User Message
    user_msg = ChatMessage(
        session_id=chat_id,
        role="user",
        content=user_query
    )
    session.add(user_msg)
    await session.flush()

    active_user_id = payload.user_id or chat.user_id or "anonymous-student"

    # 3. Add to Short-Term Memory
    short_term_memory.add_turn(chat_id, active_user_id, "user", user_query)

    # 4. Fetch Long-Term Learner Profile & Episodic Memories
    learner_ctx = await long_term_memory.get_learner_context(active_user_id, session)
    episodes = await episodic_memory_manager.get_episodes_for_topic(
        active_user_id,
        chat.topic or "General",
        session,
        limit=2
    )

    # Fetch Course Subject if available
    course_subject = ""
    if chat.course_id:
        c_res = await session.execute(select(Course).where(Course.id == chat.course_id))
        c_obj = c_res.scalar_one_or_none()
        if c_obj:
            course_subject = c_obj.subject or c_obj.title

    # 5. Execute Grounded Generation
    gen_result = await grounded_generator.answer_question(
        query=user_query,
        course_id=chat.course_id,
        course_subject=course_subject,
        student_profile=learner_ctx.get("behavior"),
        episodic_memories=episodes,
        allow_outside_knowledge=payload.allow_outside_knowledge
    )

    # 6. Save Assistant Message
    assistant_msg = ChatMessage(
        session_id=chat_id,
        role="assistant",
        content=gen_result["answer"],
        citations=gen_result["citations"],
        is_outside_knowledge=gen_result["is_outside_knowledge"],
        outside_knowledge_offered=gen_result["outside_knowledge_offered"],
        suggested_followups=gen_result["suggested_followups"]
    )
    session.add(assistant_msg)
    chat.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(assistant_msg)

    # Add to Short-Term Memory
    short_term_memory.add_turn(chat_id, payload.user_id, "assistant", gen_result["answer"])

    return format_success_response({
        "id": assistant_msg.id,
        "role": assistant_msg.role,
        "content": assistant_msg.content,
        "citations": assistant_msg.citations,
        "is_outside_knowledge": assistant_msg.is_outside_knowledge,
        "outside_knowledge_offered": assistant_msg.outside_knowledge_offered,
        "suggested_followups": assistant_msg.suggested_followups,
        "created_at": assistant_msg.created_at.isoformat()
    })
