import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

class Topic(Base):
    __tablename__ = "topics"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    course_id = Column(String(36), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    course = relationship("Course", back_populates="topics")
    concepts = relationship("Concept", back_populates="topic", cascade="all, delete-orphan")
    masteries = relationship("TopicMastery", back_populates="topic", cascade="all, delete-orphan")

class Concept(Base):
    __tablename__ = "concepts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    topic_id = Column(String(36), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    subtopic = Column(String(255), nullable=True)
    definition = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    difficulty_level = Column(String(50), default="medium") # 'easy', 'medium', 'hard'
    formulas = Column(JSON, default=list)
    examples = Column(JSON, default=list)
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    topic = relationship("Topic", back_populates="concepts")
    chunks = relationship("KnowledgeChunk", back_populates="concept", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="concept", cascade="all, delete-orphan")

class ConceptRelationship(Base):
    __tablename__ = "concept_relationships"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_concept_id = Column(String(36), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False)
    target_concept_id = Column(String(36), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False)
    relationship_type = Column(String(50), default="prerequisite") # 'prerequisite', 'builds_on', 'related_to', 'part_of'
    strength = Column(Float, default=1.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    source_concept = relationship("Concept", foreign_keys=[source_concept_id])
    target_concept = relationship("Concept", foreign_keys=[target_concept_id])

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    concept_id = Column(String(36), ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True)
    
    # Text content
    content = Column(Text, nullable=False)
    chunk_type = Column(String(50), default="text") # 'text', 'heading', 'table', 'diagram_summary', 'transcript'

    # Strict Source Attribution (The canonical source anchor)
    source_type = Column(String(50), nullable=False) # 'pdf', 'pptx', 'video', 'image', 'student_note'
    source_file = Column(String(255), nullable=False)
    source_category = Column(String(50), default="course_source") # 'course_source', 'student_provided', 'outside'
    page_number = Column(Integer, nullable=True)
    slide_number = Column(Integer, nullable=True)
    timestamp_start = Column(Float, nullable=True)
    timestamp_end = Column(Float, nullable=True)
    timestamp_start_formatted = Column(String(20), nullable=True)
    timestamp_end_formatted = Column(String(20), nullable=True)
    visual_element_id = Column(String(36), nullable=True)
    
    # Metadata
    topic_name = Column(String(255), nullable=True)
    subtopic_name = Column(String(255), nullable=True)
    concept_name = Column(String(255), nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    document = relationship("Document", back_populates="knowledge_chunks")
    concept = relationship("Concept", back_populates="chunks")
