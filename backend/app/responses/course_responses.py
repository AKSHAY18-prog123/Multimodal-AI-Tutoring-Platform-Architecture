from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class CourseCreateRequest(BaseModel):
    title: str
    code: Optional[str] = None
    description: Optional[str] = None
    subject: Optional[str] = None

class ConceptResponse(BaseModel):
    id: str
    name: str
    subtopic: Optional[str] = None
    definition: Optional[str] = None
    difficulty: str

class TopicResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    concepts: List[ConceptResponse] = []

class CourseResponse(BaseModel):
    id: str
    title: str
    code: Optional[str] = None
    description: Optional[str] = None
    subject: Optional[str] = None
    created_at: str
    topics: Optional[List[TopicResponse]] = None

class KnowledgeGraphResponse(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
