import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

class Question(Base):
    __tablename__ = "questions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    concept_id = Column(String(36), ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(50), nullable=False) # 'mcq', 'multiple_select', 'short_answer', 'numerical', 'conceptual', 'scenario'
    difficulty = Column(String(50), default="medium")  # 'easy', 'medium', 'hard'
    
    # Options for MCQs: [{"id": "A", "text": "..."}, ...]
    options = Column(JSON, default=list)
    correct_answer = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False)
    
    # Categorization
    topic_name = Column(String(255), nullable=False)
    subtopic_name = Column(String(255), nullable=True)
    concept_name = Column(String(255), nullable=False)

    # Source Linkage
    source_anchor = Column(JSON, default=dict) # {"source_type": "...", "source_file": "...", "page": ..., "slide": ...}

    # Verification & Novelty
    verification_status = Column(String(50), default="verified") # 'verified', 'pending', 'failed'
    verification_details = Column(JSON, default=dict)
    novelty_hash = Column(String(64), index=True, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    concept = relationship("Concept", back_populates="questions")
    attempts = relationship("QuestionAttempt", back_populates="question")
    assessment_links = relationship("AssessmentQuestion", back_populates="question")

class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(String(36), ForeignKey("courses.id", ondelete="SET NULL"), nullable=True)
    topic_id = Column(String(36), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    
    title = Column(String(255), nullable=False)
    difficulty = Column(String(50), default="medium")
    duration_minutes = Column(Integer, default=15)
    total_questions = Column(Integer, default=5)
    
    status = Column(String(50), default="in_progress") # 'in_progress', 'completed'
    score = Column(Float, default=0.0)
    accuracy = Column(Float, default=0.0)
    
    report_json = Column(JSON, default=dict) # Full diagnostic post-assessment report
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    questions = relationship("AssessmentQuestion", back_populates="assessment", cascade="all, delete-orphan", order_by="AssessmentQuestion.order_index")
    attempts = relationship("QuestionAttempt", back_populates="assessment", cascade="all, delete-orphan")

class AssessmentQuestion(Base):
    __tablename__ = "assessment_questions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id = Column(String(36), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(String(36), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    order_index = Column(Integer, default=0)

    assessment = relationship("Assessment", back_populates="questions")
    question = relationship("Question", back_populates="assessment_links")

class QuestionAttempt(Base):
    __tablename__ = "question_attempts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assessment_id = Column(String(36), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=True)
    question_id = Column(String(36), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    
    selected_answer = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=False)
    time_taken_seconds = Column(Float, default=0.0)
    detected_misconception_tag = Column(String(255), nullable=True)
    attempted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="question_attempts")
    assessment = relationship("Assessment", back_populates="attempts")
    question = relationship("Question", back_populates="attempts")

class Misconception(Base):
    __tablename__ = "misconceptions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    topic_name = Column(String(255), nullable=False)
    concept_name = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    trigger_distractor = Column(String(255), nullable=True)
    remediation_guidance = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
