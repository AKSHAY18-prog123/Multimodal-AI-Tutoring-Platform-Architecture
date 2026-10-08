from typing import Optional
from pydantic import BaseModel

class DocumentUploadResponse(BaseModel):
    job_id: str
    document_id: str
    filename: str
    file_type: str
    source_category: str
    status: str
    progress: int
    message: str

class DocumentStatusResponse(BaseModel):
    job_id: str
    document_id: str
    filename: str
    status: str
    progress: int
    error_message: Optional[str] = None

class DocumentItemResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    source_category: str
    file_size_bytes: int
    status: str
    progress: int
    created_at: str
