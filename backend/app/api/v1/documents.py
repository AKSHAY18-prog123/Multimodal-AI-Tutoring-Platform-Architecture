import os
import shutil
import asyncio
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.database.session import get_db_session
from backend.app.database.models.document import Document, DocumentPage, Slide, Video, VideoSegment, VisualElement
from backend.app.workers.document_worker import process_document_background
from backend.app.core.exceptions import format_success_response, EntityNotFoundError

router = APIRouter(prefix="/documents", tags=["Documents"])

ALLOWED_EXTENSIONS = {".pdf", ".pptx", ".ppt", ".mp4", ".webm", ".png", ".jpg", ".jpeg", ".mp3", ".wav"}

@router.post("/upload")
async def upload_document(
    course_id: str = Form(...),
    source_category: str = Form("course_source"), # 'course_source', 'student_provided', 'outside'
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Async document upload endpoint for a single file.
    Saves file, creates DB record, starts background extraction worker, and returns job_id immediately.
    """
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file extension {file_ext}. Allowed: {ALLOWED_EXTENSIONS}")

    # Determine file type
    if file_ext == ".pdf":
        file_type = "pdf"
    elif file_ext in [".pptx", ".ppt"]:
        file_type = "pptx"
    elif file_ext in [".mp4", ".webm"]:
        file_type = "video"
    elif file_ext in [".mp3", ".wav"]:
        file_type = "audio"
    else:
        file_type = "image"

    dest_dir = Path(settings.UPLOAD_DIR)
    dest_dir.mkdir(parents=True, exist_ok=True)
    saved_path = dest_dir / f"{course_id}_{file.filename}"

    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    doc = Document(
        course_id=course_id,
        filename=file.filename,
        file_path=str(saved_path),
        file_type=file_type,
        source_category=source_category,
        file_size_bytes=saved_path.stat().st_size,
        status="uploaded",
        processing_progress=5
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)

    # Dispatch non-blocking background job
    background_tasks.add_task(process_document_background, doc.id)

    return format_success_response({
        "job_id": doc.id,
        "document_id": doc.id,
        "filename": doc.filename,
        "file_type": doc.file_type,
        "source_category": doc.source_category,
        "status": doc.status,
        "progress": doc.processing_progress,
        "message": "File uploaded successfully. Processing started in background."
    })

@router.post("/upload-batch")
async def upload_documents_batch(
    course_id: str = Form(...),
    source_category: str = Form("course_source"),
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Accepts multiple documents (PDFs, PPTXs, Images, Videos, Notes) at once,
    stores them, records DB entities, and dispatches background processing for each.
    """
    dest_dir = Path(settings.UPLOAD_DIR)
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    uploaded_docs = []
    for file in files:
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            continue
        
        if file_ext == ".pdf":
            file_type = "pdf"
        elif file_ext in [".pptx", ".ppt"]:
            file_type = "pptx"
        elif file_ext in [".mp4", ".webm"]:
            file_type = "video"
        elif file_ext in [".mp3", ".wav"]:
            file_type = "audio"
        else:
            file_type = "image"
            
        saved_path = dest_dir / f"{course_id}_{file.filename}"
        with open(saved_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        doc = Document(
            course_id=course_id,
            filename=file.filename,
            file_path=str(saved_path),
            file_type=file_type,
            source_category=source_category,
            file_size_bytes=saved_path.stat().st_size,
            status="uploaded",
            processing_progress=5
        )
        session.add(doc)
        uploaded_docs.append(doc)
        
    await session.commit()
    for doc in uploaded_docs:
        await session.refresh(doc)
        background_tasks.add_task(process_document_background, doc.id)
        
    return format_success_response({
        "uploaded_count": len(uploaded_docs),
        "job_ids": [d.id for d in uploaded_docs],
        "documents": [
            {
                "job_id": d.id,
                "document_id": d.id,
                "filename": d.filename,
                "file_type": d.file_type,
                "status": d.status,
                "progress": d.processing_progress
            }
            for d in uploaded_docs
        ],
        "message": f"Successfully queued {len(uploaded_docs)} files for processing."
    })

@router.get("/{document_id}/status")
async def get_document_status(
    document_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    result = await session.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise EntityNotFoundError("Document", document_id)

    return format_success_response({
        "job_id": doc.id,
        "document_id": doc.id,
        "filename": doc.filename,
        "status": doc.status,
        "progress": doc.processing_progress,
        "error_message": doc.error_message
    })

@router.get("/{document_id}")
async def get_document_details(
    document_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    result = await session.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise EntityNotFoundError("Document", document_id)

    # Fetch pages or slides
    pages_res = await session.execute(select(DocumentPage).where(DocumentPage.document_id == document_id))
    slides_res = await session.execute(select(Slide).where(Slide.document_id == document_id))
    visuals_res = await session.execute(select(VisualElement).where(VisualElement.document_id == document_id))

    return format_success_response({
        "id": doc.id,
        "course_id": doc.course_id,
        "filename": doc.filename,
        "file_type": doc.file_type,
        "source_category": doc.source_category,
        "status": doc.status,
        "progress": doc.processing_progress,
        "pages_count": len(pages_res.scalars().all()),
        "slides_count": len(slides_res.scalars().all()),
        "visual_elements_count": len(visuals_res.scalars().all()),
        "created_at": doc.created_at.isoformat()
    })

@router.get("/course/{course_id}")
async def list_course_documents(
    course_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    result = await session.execute(
        select(Document).where(Document.course_id == course_id).order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    return format_success_response([
        {
            "id": d.id,
            "filename": d.filename,
            "file_type": d.file_type,
            "source_category": d.source_category,
            "file_size_bytes": d.file_size_bytes,
            "status": d.status,
            "progress": d.processing_progress,
            "created_at": d.created_at.isoformat()
        }
        for d in docs
    ])
