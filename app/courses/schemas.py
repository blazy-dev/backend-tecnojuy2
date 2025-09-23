from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, validator
from enum import Enum

# Enums para tipos de contenido
class ContentType(str, Enum):
    VIDEO = "video"
    PDF = "pdf"
    IMAGE = "image"
    TEXT = "text"
    QUIZ = "quiz"

class CourseLevel(str, Enum):
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"

# Esquemas base
class ChapterBase(BaseModel):
    title: str
    description: Optional[str] = None
    order_index: int
    is_published: bool = False

class ChapterCreate(ChapterBase):
    course_id: int

class ChapterUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    order_index: Optional[int] = None
    is_published: Optional[bool] = None

class LessonBase(BaseModel):
    title: str
    description: Optional[str] = None
    content_type: ContentType
    order_index: int
    estimated_duration_minutes: Optional[int] = None
    is_published: bool = False
    is_free: bool = False
    can_download: bool = False

class LessonCreate(LessonBase):
    chapter_id: int
    course_id: int
    # Contenido específico según el tipo
    video_object_key: Optional[str] = None
    video_duration_seconds: Optional[int] = None
    file_object_key: Optional[str] = None
    file_type: Optional[str] = None
    file_size_bytes: Optional[int] = None
    text_content: Optional[str] = None

class LessonUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    content_type: Optional[ContentType] = None
    order_index: Optional[int] = None
    estimated_duration_minutes: Optional[int] = None
    is_published: Optional[bool] = None
    is_free: Optional[bool] = None
    can_download: Optional[bool] = None
    # URLs directas cuando se sube/reemplaza contenido
    video_url: Optional[str] = None
    video_object_key: Optional[str] = None
    video_duration_seconds: Optional[int] = None
    file_url: Optional[str] = None
    file_object_key: Optional[str] = None
    file_type: Optional[str] = None
    file_size_bytes: Optional[int] = None
    text_content: Optional[str] = None

class CourseBase(BaseModel):
    title: str
    description: Optional[str] = None
    short_description: Optional[str] = None
    level: CourseLevel = CourseLevel.BEGINNER
    language: str = "Español"
    category: Optional[str] = None
    tags: Optional[str] = None  # Tags separados por comas
    estimated_duration_hours: Optional[int] = None
    is_published: bool = False
    is_premium: bool = True
    price: Optional[str] = None

class CourseCreate(CourseBase):
    instructor_id: int
    cover_image_url: Optional[str] = None
    trailer_video_url: Optional[str] = None

class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    short_description: Optional[str] = None
    level: Optional[CourseLevel] = None
    language: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None
    estimated_duration_hours: Optional[int] = None
    is_published: Optional[bool] = None
    is_premium: Optional[bool] = None
    price: Optional[str] = None
    cover_image_url: Optional[str] = None
    trailer_video_url: Optional[str] = None

# Esquemas de respuesta
class LessonResponse(LessonBase):
    id: int
    chapter_id: int
    course_id: int
    video_url: Optional[str] = None
    file_url: Optional[str] = None
    file_type: Optional[str] = None
    file_size_bytes: Optional[int] = None
    text_content: Optional[str] = None
    has_access: Optional[bool] = None  # Si el usuario tiene acceso
    progress_percentage: Optional[int] = None
    is_completed: Optional[bool] = None
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class ChapterResponse(ChapterBase):
    id: int
    course_id: int
    lessons: List[LessonResponse] = []
    lesson_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class CourseResponse(CourseBase):
    id: int
    instructor_id: int
    instructor_name: str
    cover_image_url: Optional[str] = None
    trailer_video_url: Optional[str] = None
    chapters: List[ChapterResponse] = []
    chapter_count: int = 0
    lesson_count: int = 0
    total_duration_minutes: int = 0
    has_access: Optional[bool] = None
    progress_percentage: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class CourseListResponse(BaseModel):
    id: int
    title: str
    short_description: Optional[str] = None
    cover_image_url: Optional[str] = None
    level: str
    language: str
    category: Optional[str] = None
    price: Optional[str] = None
    is_premium: bool
    is_published: Optional[bool] = None
    instructor_name: str
    lesson_count: int = 0
    estimated_duration_hours: Optional[int] = None
    has_access: Optional[bool] = None
    progress_percentage: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Esquemas para progreso
class LessonProgressUpdate(BaseModel):
    progress_percentage: int = 0
    time_spent_seconds: int = 0
    last_position_seconds: int = 0
    is_completed: bool = False

    @validator('progress_percentage')
    def validate_progress(cls, v):
        if v < 0 or v > 100:
            raise ValueError('Progress must be between 0 and 100')
        return v

class LessonProgressResponse(BaseModel):
    id: int
    lesson_id: int
    is_completed: bool
    progress_percentage: int
    time_spent_seconds: int
    last_position_seconds: int
    completed_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

# Esquemas para archivos
class FileUploadResponse(BaseModel):
    upload_url: str
    public_url: str
    object_key: str
    file_type: str

class VideoUrlResponse(BaseModel):
    video_url: str
    expires_in: int
