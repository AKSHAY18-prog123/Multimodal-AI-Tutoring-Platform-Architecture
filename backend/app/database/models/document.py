import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    course_id = Column(String(36), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_type = Column(String(50), nullable=False) # 'pdf', 'pptx', 'video', 'image', 'audio'
    source_category = Column(String(50), default="course_source") # 'course_source', 'student_provided', 'outside'
    file_size_bytes = Column(Integer, default=0)
    status = Column(String(50), default="uploaded") # 'uploaded', 'processing', 'completed', 'failed'
    processing_progress = Column(Integer, default=0) # 0 to 100
    error_message = Column(Text, nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    course = relationship("Course", back_populates="documents")
    pages = relationship("DocumentPage", back_populates="document", cascade="all, delete-orphan")
    slides = relationship("Slide", back_populates="document", cascade="all, delete-orphan")
    videos = relationship("Video", back_populates="document", cascade="all, delete-orphan")
    visual_elements = relationship("VisualElement", back_populates="document", cascade="all, delete-orphan")
    knowledge_chunks = relationship("KnowledgeChunk", back_populates="document", cascade="all, delete-orphan")

class DocumentPage(Base):
    __tablename__ = "document_pages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=False)
    raw_text = Column(Text, nullable=True)
    headings = Column(JSON, default=list) # List of extracted headings
    tables = Column(JSON, default=list)   # Extracted tabular structures
    equations = Column(JSON, default=list) # Extracted math/formulas
    image_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    document = relationship("Document", back_populates="pages")

class Slide(Base):
    __tablename__ = "slides"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    slide_number = Column(Integer, nullable=False)
    title = Column(String(255), nullable=True)
    bullet_points = Column(JSON, default=list)
    raw_text = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    tables = Column(JSON, default=list)
    shape_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    document = relationship("Document", back_populates="slides")

class Video(Base):
    __tablename__ = "videos"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    duration_seconds = Column(Float, default=0.0)
    resolution = Column(String(50), nullable=True)
    frame_rate = Column(Float, nullable=True)
    audio_extracted = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    document = relationship("Document", back_populates="videos")
    segments = relationship("VideoSegment", back_populates="video", cascade="all, delete-orphan")

class VideoSegment(Base):
    __tablename__ = "video_segments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id = Column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    timestamp_start = Column(Float, nullable=False) # In seconds
    timestamp_end = Column(Float, nullable=False)   # In seconds
    timestamp_start_formatted = Column(String(20), nullable=False) # e.g. "32:14"
    timestamp_end_formatted = Column(String(20), nullable=False)   # e.g. "35:48"
    transcript_text = Column(Text, nullable=False)
    key_concepts = Column(JSON, default=list)
    frame_image_path = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    video = relationship("Video", back_populates="segments")

class VisualElement(Base):
    __tablename__ = "visual_elements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    visual_type = Column(String(50), nullable=False) # 'diagram', 'chart', 'graph', 'table', 'figure', 'screenshot'
    image_path = Column(String(512), nullable=False)
    page_number = Column(Integer, nullable=True)
    slide_number = Column(Integer, nullable=True)
    caption = Column(String(512), nullable=True)
    description = Column(Text, nullable=True)
    concept = Column(String(255), nullable=True)
    entities = Column(JSON, default=list)
    relationships = Column(JSON, default=list)
    vision_understanding_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    document = relationship("Document", back_populates="visual_elements")
