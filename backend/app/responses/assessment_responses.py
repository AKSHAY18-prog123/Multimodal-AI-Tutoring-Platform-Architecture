from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class GenerateAssessmentRequest(BaseModel):
    user_id: Optional[str] = None
    course_id: Optional[str] = None
    topic_id: Optional[str] = None
    difficulty: str = "medium"
    question_count: int = 5
    duration_minutes: int = 15
    is_diagnostic: bool = False

class SubmitAnswerItem(BaseModel):
    question_id: str
    selected_answer: str
    time_taken_seconds: float = 30.0

class SubmitAssessmentRequest(BaseModel):
    user_id: Optional[str] = None
    answers: List[SubmitAnswerItem]

class OptionItem(BaseModel):
    id: str
    text: str

class AssessmentQuestionClient(BaseModel):
    id: str
    question_text: str
    question_type: str
    difficulty: str
    options: List[OptionItem] = []
    topic_name: str
    concept_name: str
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None

class GeneratedAssessmentResponse(BaseModel):
    assessment_id: str
    title: str
    difficulty: str
    duration_minutes: int
    total_questions: int
    is_diagnostic: bool
    questions: List[AssessmentQuestionClient]

class MasteryChangeItem(BaseModel):
    concept: str
    before: float
    after: float
    improvement: float
    direction: str

class RecommendationItem(BaseModel):
    action: str
    title: str
    guidance: str

class MisconceptionDiagnosticResponse(BaseModel):
    detected: bool
    concept: str
    misconception_title: str
    remediation_guidance: str
    recommended_action: Optional[str] = None

class AssessmentReportResponse(BaseModel):
    assessment_id: str
    total_questions: int
    correct_answers: int
    accuracy_percentage: float
    score_percentage: float
    total_time_seconds: float
    avg_time_per_question: float
    concept_performance: Dict[str, Any]
    difficulty_performance: Dict[str, Any]
    mastery_changes: List[MasteryChangeItem]
    weak_concepts: List[str]
    strong_concepts: List[str]
    misconception_diagnostic: Optional[MisconceptionDiagnosticResponse] = None
    recommendations: List[RecommendationItem]
