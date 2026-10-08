import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

class LearnerProfile(Base):
    __tablename__ = "learner_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    status = Column(String(50), default="uncalibrated") # 'uncalibrated', 'active', 'advanced'
    overall_mastery = Column(Float, default=0.15) # Prior baseline 0.15 for novice
    
    # Non-sensitive Learning Behavior Profile
    learning_behavior = Column(JSON, default=lambda: {
        "prefers_examples_before_theory": True,
        "prefers_formal_math": False,
        "explanation_preference": "balanced_scaffolded", # 'concise', 'detailed', 'step_by_step', 'balanced_scaffolded'
        "pacing": "moderate",
        "common_struggles": [],
        "strengths": []
    })

    # Time tracking aggregates
    total_active_study_minutes = Column(Float, default=0.0)
    total_questions_answered = Column(Integer, default=0)
    total_assessments_completed = Column(Integer, default=0)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="learner_profile")

class TopicMastery(Base):
    __tablename__ = "topic_mastery"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic_id = Column(String(36), ForeignKey("topics.id", ondelete="CASCADE"), nullable=True)
    concept_id = Column(String(36), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=True)
    
    # Bayesian Knowledge Tracing (BKT) State
    mastery = Column(Float, default=0.15)       # P(L_t) - Current mastery probability
    p_transit = Column(Float, default=0.10)     # P(T) - Learning transition rate
    p_guess = Column(Float, default=0.20)       # P(G) - Guess probability
    p_slip = Column(Float, default=0.10)        # P(S) - Slip probability
    
    confidence = Column(Float, default=0.2)     # Confidence in the estimate (scales with evidence)
    evidence_count = Column(Integer, default=0) # Number of observations
    correct_count = Column(Integer, default=0)
    incorrect_count = Column(Integer, default=0)

    last_interaction = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_correct_at = Column(DateTime, nullable=True)
    last_incorrect_at = Column(DateTime, nullable=True)
    
    # Spaced Repetition / Forgetting
    difficulty_exposure = Column(Float, default=0.5)
    estimated_forgetting = Column(Float, default=0.0)
    recommended_review_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    topic = relationship("Topic", back_populates="masteries")
    concept = relationship("Concept")

class LearningEvent(Base):
    __tablename__ = "learning_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic_name = Column(String(255), nullable=True)
    concept_name = Column(String(255), nullable=True)
    event_type = Column(String(100), nullable=False) # 'question_answered', 'concept_explained', 'misconception_flagged', 'session_started'
    evidence_weight = Column(Float, default=1.0)     # Exam=1.0, ShortAnswer=0.7, Conversation=0.3
    payload = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class EpisodicMemory(Base):
    __tablename__ = "episodic_memories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic = Column(String(255), nullable=False)
    concept = Column(String(255), nullable=False)
    event_type = Column(String(100), nullable=False) # 'misconception_resolved', 'prerequisite_struggle', 'breakthrough'
    evidence = Column(Text, nullable=False)          # Description of what happened
    result = Column(String(50), default="improved")  # 'improved', 'struggling', 'resolved'
    context_summary = Column(Text, nullable=True)    # Summary for prompt injection
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="episodic_memories")

class StudySession(Base):
    __tablename__ = "study_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(String(36), ForeignKey("courses.id", ondelete="SET NULL"), nullable=True)
    session_start = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    session_end = Column(DateTime, nullable=True)
    active_study_seconds = Column(Float, default=0.0)
    reading_seconds = Column(Float, default=0.0)
    answering_seconds = Column(Float, default=0.0)
    concepts_covered = Column(JSON, default=list)

    user = relationship("User", back_populates="study_sessions")
