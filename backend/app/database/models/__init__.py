from backend.app.database.session import Base
from backend.app.database.models.user import User
from backend.app.database.models.course import Course
from backend.app.database.models.document import Document, DocumentPage, Slide, Video, VideoSegment, VisualElement
from backend.app.database.models.knowledge import Topic, Concept, ConceptRelationship, KnowledgeChunk
from backend.app.database.models.chat import ChatSession, ChatMessage
from backend.app.database.models.learner import LearnerProfile, TopicMastery, LearningEvent, EpisodicMemory, StudySession
from backend.app.database.models.assessment import Question, Assessment, AssessmentQuestion, QuestionAttempt, Misconception
from backend.app.database.models.analytics import ModelPrediction, Recommendation, EvaluationRun

__all__ = [
    "Base",
    "User",
    "Course",
    "Document",
    "DocumentPage",
    "Slide",
    "Video",
    "VideoSegment",
    "VisualElement",
    "Topic",
    "Concept",
    "ConceptRelationship",
    "KnowledgeChunk",
    "ChatSession",
    "ChatMessage",
    "LearnerProfile",
    "TopicMastery",
    "LearningEvent",
    "EpisodicMemory",
    "StudySession",
    "Question",
    "Assessment",
    "AssessmentQuestion",
    "QuestionAttempt",
    "Misconception",
    "ModelPrediction",
    "Recommendation",
    "EvaluationRun",
]
