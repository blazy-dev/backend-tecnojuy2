from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class PostBase(BaseModel):
    title: str
    content: str
    cover_image_url: Optional[str] = None
    is_published: bool = True

class PostCreate(PostBase):
    pass

class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    cover_image_url: Optional[str] = None
    is_published: Optional[bool] = None

class AuthorInfo(BaseModel):
    id: int
    name: str
    email: str
    avatar_url: Optional[str] = None

class PostResponse(PostBase):
    id: int
    author: AuthorInfo
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class PostSummary(BaseModel):
    """Resumen de post para listados"""
    id: int
    title: str
    cover_image_url: Optional[str] = None
    author_name: str
    created_at: datetime
    is_published: bool
    
    class Config:
        from_attributes = True


