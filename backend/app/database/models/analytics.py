import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON, Boolean, Text
from backend.app.database.session import Base

class ModelPrediction(Base):
    __tablename__ = "model_predictions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    model_name = Column(String(100), nullable=False)       # e.g., 'readiness_random_forest', 'learning_time_gbr'
    model_version = Column(String(50), default="1.0.0")
    prediction_type = Column(String(50), nullable=False)   # 'classification', 'regression'
    input_features = Column(JSON, nullable=False)
    predicted_output = Column(JSON, nullable=False)
    actual_outcome = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic_name = Column(String(255), nullable=False)
    concept_name = Column(String(255), nullable=False)
    action_type = Column(String(50), nullable=False) # 'review_concept', 'attempt_quiz', 'prerequisite_remediation'
    title = Column(String(255), nullable=False)
    reason = Column(Text, nullable=False)
    urgency = Column(String(20), default="medium") # 'low', 'medium', 'high'
    is_dismissed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    benchmark_name = Column(String(100), nullable=False) # 'rag_faithfulness', 'citation_grounding', 'off_material_refusal'
    total_samples = Column(Float, default=0.0)
    passed_samples = Column(Float, default=0.0)
    metric_score = Column(Float, default=0.0) # e.g., 0.94
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
