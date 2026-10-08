from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class ScoreHistoryItem(BaseModel):
    id: str
    title: str
    score: float
    accuracy: float
    date: str

class MasteryTimelineItem(BaseModel):
    session: str
    mastery: int

class AnalyticsProgressResponse(BaseModel):
    overall_mastery_pct: int
    assessments_completed: int
    total_study_minutes: float
    reading_minutes: float
    answering_minutes: float
    score_history: List[ScoreHistoryItem]
    mastery_timeline: List[MasteryTimelineItem]
    novelty_metrics: Dict[str, Any]
    learning_gains: str

class FeedbackSubmitRequest(BaseModel):
    user_id: Optional[str] = None
    category: str = "explanation_style"
    rating: int = 5
    comment: str = ""
