from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator
import re


# --- Schemas para Categorías ---
class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = None
    color: str = Field(default="#3B82F6", pattern=r"^#[0-9A-Fa-f]{6}$")

class CategoryCreate(CategoryBase):
    @validator('slug')
    def validate_slug(cls, v):
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('El slug solo puede contener letras minúsculas, números y guiones')
        return v

class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    slug: Optional[str] = Field(None, min_length=1, max_length=120)
    description: Optional[str] = None
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")

    @validator('slug')
    def validate_slug(cls, v):
        if v and not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('El slug solo puede contener letras minúsculas, números y guiones')
        return v

class CategoryResponse(CategoryBase):
    id: int
    created_at: datetime
    posts_count: Optional[int] = 0

    class Config:
        from_attributes = True


# --- Schemas para Tags ---
class TagBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    slug: str = Field(..., min_length=1, max_length=60)

class TagCreate(TagBase):
    @validator('slug')
    def validate_slug(cls, v):
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('El slug solo puede contener letras minúsculas, números y guiones')
        return v

class TagUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    slug: Optional[str] = Field(None, min_length=1, max_length=60)

    @validator('slug')
    def validate_slug(cls, v):
        if v and not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('El slug solo puede contener letras minúsculas, números y guiones')
        return v

class TagResponse(TagBase):
    id: int
    created_at: datetime
    posts_count: Optional[int] = 0

    class Config:
        from_attributes = True


# --- Schemas para Posts ---
class PostBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=280)
    excerpt: Optional[str] = None
    content: str = Field(..., min_length=1)
    featured_image_url: Optional[str] = None
    meta_title: Optional[str] = Field(None, max_length=60)
    meta_description: Optional[str] = Field(None, max_length=160)
    is_published: bool = False
    is_featured: bool = False
    reading_time_minutes: Optional[int] = Field(None, ge=1)
    category_id: Optional[int] = None

class PostCreate(PostBase):
    tag_ids: Optional[List[int]] = []

    @validator('slug')
    def validate_slug(cls, v):
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('El slug solo puede contener letras minúsculas, números y guiones')
        return v

    @validator('reading_time_minutes')
    def calculate_reading_time(cls, v, values):
        """Calcula automáticamente el tiempo de lectura si no se proporciona"""
        if v is None and 'content' in values:
            # Aproximadamente 200 palabras por minuto
            word_count = len(values['content'].split())
            return max(1, round(word_count / 200))
        return v

class PostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=1, max_length=280)
    excerpt: Optional[str] = None
    content: Optional[str] = Field(None, min_length=1)
    featured_image_url: Optional[str] = None
    meta_title: Optional[str] = Field(None, max_length=60)
    meta_description: Optional[str] = Field(None, max_length=160)
    is_published: Optional[bool] = None
    is_featured: Optional[bool] = None
    reading_time_minutes: Optional[int] = Field(None, ge=1)
    category_id: Optional[int] = None
    tag_ids: Optional[List[int]] = None

    @validator('slug')
    def validate_slug(cls, v):
        if v and not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('El slug solo puede contener letras minúsculas, números y guiones')
        return v

class AuthorResponse(BaseModel):
    id: int
    name: str
    email: str
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True

class PostResponse(PostBase):
    id: int
    published_at: Optional[datetime] = None
    views_count: int = 0
    author_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Relaciones
    author: AuthorResponse
    category: Optional[CategoryResponse] = None
    tags: List[TagResponse] = []

    class Config:
        from_attributes = True

class PostListResponse(BaseModel):
    id: int
    title: str
    slug: str
    excerpt: Optional[str] = None
    featured_image_url: Optional[str] = None
    is_published: bool
    is_featured: bool
    published_at: Optional[datetime] = None
    reading_time_minutes: Optional[int] = None
    views_count: int = 0
    author: AuthorResponse
    category: Optional[CategoryResponse] = None
    tags: List[TagResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True

# --- Schemas para respuestas paginadas ---
class PostsPaginatedResponse(BaseModel):
    posts: List[PostListResponse]
    total: int
    page: int
    pages: int
    has_next: bool
    has_prev: bool

class CategoriesPaginatedResponse(BaseModel):
    categories: List[CategoryResponse]
    total: int
    page: int
    pages: int
    has_next: bool
    has_prev: bool

class TagsPaginatedResponse(BaseModel):
    tags: List[TagResponse]
    total: int
    page: int
    pages: int
    has_next: bool
    has_prev: bool


# --- Schemas para estadísticas del blog ---
class BlogStatsResponse(BaseModel):
    total_posts: int
    published_posts: int
    draft_posts: int
    total_views: int
    total_categories: int
    total_tags: int
    featured_posts: int
