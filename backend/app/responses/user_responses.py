from typing import Optional, List
from pydantic import BaseModel

class UserBasicInfo(BaseModel):
    id: str
    name: str
    email: Optional[str] = None
    created_at: Optional[str] = None
    onboarding_completed: Optional[bool] = False

class UserStatusData(BaseModel):
    exists: bool
    onboarding_completed: bool
    user: Optional[UserBasicInfo] = None

class UserListResponse(BaseModel):
    users: List[UserBasicInfo]

class OnboardRequest(BaseModel):
    name: str
    email: Optional[str] = None
    user_id: Optional[str] = None

class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
