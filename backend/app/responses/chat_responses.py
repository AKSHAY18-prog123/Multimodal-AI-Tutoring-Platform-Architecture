from typing import Optional, List, Dict, Any
from pydantic import BaseModel

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

class CitationResponse(BaseModel):
    chunk_id: Optional[str] = None
    source_type: str
    source_file: str
    page_number: Optional[int] = None
    slide_number: Optional[int] = None
    timestamp_formatted: Optional[str] = None
    label: str
    rerank_score: Optional[float] = None

class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    citations: List[CitationResponse] = []
    is_outside_knowledge: bool = False
    outside_knowledge_offered: bool = False
    suggested_followups: List[str] = []
    created_at: str

class ChatSessionResponse(BaseModel):
    id: str
    user_id: str
    course_id: Optional[str] = None
    title: str
    topic: Optional[str] = None
    summary: Optional[str] = None
    pinned: bool
    created_at: str
    updated_at: str
    messages: Optional[List[ChatMessageResponse]] = None
