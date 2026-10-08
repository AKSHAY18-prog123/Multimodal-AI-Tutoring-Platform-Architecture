from fastapi import APIRouter
from backend.app.api.v1.users import router as users_router
from backend.app.api.v1.courses import router as courses_router
from backend.app.api.v1.documents import router as documents_router
from backend.app.api.v1.chat import router as chat_router
from backend.app.api.v1.assessments import router as assessments_router
from backend.app.api.v1.learner import router as learner_router
from backend.app.api.v1.analytics import router as analytics_router
from backend.app.api.v1.memory import router as memory_router

api_v1_router = APIRouter()

api_v1_router.include_router(users_router)
api_v1_router.include_router(courses_router)
api_v1_router.include_router(documents_router)
api_v1_router.include_router(chat_router)
api_v1_router.include_router(assessments_router)
api_v1_router.include_router(learner_router)
api_v1_router.include_router(analytics_router)
api_v1_router.include_router(memory_router)
