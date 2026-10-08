import time
import uuid
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from backend.app.core.config import settings
from backend.app.core.logging import setup_logging, logger
from backend.app.core.exceptions import AppException, app_exception_handler, format_error_response
from backend.app.database.init_db import init_database
from backend.app.api.v1.router import api_v1_router

setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode...")
    await init_database()
    yield
    logger.info(f"Shutting down {settings.APP_NAME}...")

app = FastAPI(
    title=settings.APP_NAME,
    description="Track D: Personalized Tutoring & Adaptive Learning - Production Architecture",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID & Observability Latency Middleware
@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = req_id
    start_time = time.time()

    try:
        response = await call_next(request)
        process_time_ms = round((time.time() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Process-Time-Ms"] = str(process_time_ms)
        logger.info(f"[{req_id}] {request.method} {request.url.path} - {response.status_code} ({process_time_ms}ms)")
        return response
    except Exception as e:
        process_time_ms = round((time.time() - start_time) * 1000, 2)
        logger.error(f"[{req_id}] Unhandled Exception: {e} ({process_time_ms}ms)")
        return JSONResponse(
            status_code=500,
            content=format_error_response(
                code="INTERNAL_SERVER_ERROR",
                message="An unexpected server error occurred.",
                details={"error": str(e)},
                request_id=req_id
            )
        )

# Register Custom Exception Handler
app.add_exception_handler(AppException, app_exception_handler)

# Include API Router
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

# Static file serving for Source Viewer (PDFs, PPT images, video frames)
storage_dir = Path(settings.STORAGE_DIR).resolve()
if storage_dir.exists():
    app.mount("/static/storage", StaticFiles(directory=str(storage_dir)), name="storage")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "llm_provider": settings.LLM_PROVIDER
    }
