from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class LearnerProfileResponse(BaseModel):
    user_id: str
    status: str
    overall_mastery: float
    learning_behavior: Dict[str, Any]
    total_active_study_minutes: float
    total_questions_answered: int
    total_assessments_completed: int
    is_cold_start: bool

class TopicMasteryItem(BaseModel):
    id: Optional[str] = None
    concept_name: str
    topic_title: str
    difficulty: str
    mastery_score: float
    raw_mastery: float
    confidence: float
    evidence_count: int
    correct_count: int
    incorrect_count: int
    last_interaction: Optional[str] = None

class MLPredictionsResponse(BaseModel):
    concept: str
    readiness_classification: Dict[str, Any]
    time_to_mastery_regression: Dict[str, Any]

class RecommendationResponse(BaseModel):
    title: str
    topic: str
    reason: str
    action_type: str
    urgency: str
