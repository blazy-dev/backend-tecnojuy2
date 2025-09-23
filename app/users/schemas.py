from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr
    name: str
    avatar_url: Optional[str] = None

class UserCreate(UserBase):
    google_id: str
    role_id: int

class UserUpdate(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = None
    role_id: Optional[int] = None

class UserResponse(UserBase):
    id: int
    google_id: str
    is_active: bool
    has_premium_access: bool
    role_name: str
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None

class RoleCreate(RoleBase):
    pass

class RoleResponse(RoleBase):
    id: int
    
    class Config:
        from_attributes = True

