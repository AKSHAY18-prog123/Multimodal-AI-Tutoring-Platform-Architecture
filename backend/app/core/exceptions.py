from typing import Any, Dict, Optional
from datetime import datetime, timezone
import uuid
from fastapi import Request
from fastapi.responses import JSONResponse

class AppException(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

class SourceNotFoundError(AppException):
    def __init__(self, message: str = "No supporting course material was found.", details: Optional[Dict[str, Any]] = None):
        super().__init__(code="SOURCE_NOT_FOUND", message=message, status_code=404, details=details)

class OffMaterialError(AppException):
    def __init__(self, message: str = "This topic is not covered in the uploaded course material.", details: Optional[Dict[str, Any]] = None):
        super().__init__(code="OFF_MATERIAL_QUERY", message=message, status_code=400, details=details)

class EntityNotFoundError(AppException):
    def __init__(self, entity: str, entity_id: str):
        super().__init__(code="ENTITY_NOT_FOUND", message=f"{entity} with ID {entity_id} was not found.", status_code=404)

def format_success_response(data: Any, request_id: Optional[str] = None) -> Dict[str, Any]:
    return {
        "success": True,
        "data": data,
        "meta": {
            "request_id": request_id or str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        "error": None
    }

def format_error_response(code: str, message: str, details: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None) -> Dict[str, Any]:
    return {
        "success": False,
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "details": details or {}
        },
        "meta": {
            "request_id": request_id or str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }

async def app_exception_handler(request: Request, exc: AppException):
    req_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(
            code=exc.code,
            message=exc.message,
            details=exc.details,
            request_id=req_id
        )
    )
