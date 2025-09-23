from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

# Esquemas para HomepageContent
class HomepageContentBase(BaseModel):
    section: str
    title: Optional[str] = None
    subtitle: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    button_text: Optional[str] = None
    button_url: Optional[str] = None
    order_index: int = 0
    is_active: bool = True
    extra_data: Optional[str] = None  # JSON string

class HomepageContentCreate(HomepageContentBase):
    pass

class HomepageContentUpdate(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    button_text: Optional[str] = None
    button_url: Optional[str] = None
    order_index: Optional[int] = None
    is_active: Optional[bool] = None
    extra_data: Optional[str] = None

class HomepageContentResponse(HomepageContentBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

# Esquemas para HomepageGallery
class HomepageGalleryBase(BaseModel):
    title: str
    description: Optional[str] = None
    image_url: str
    category: Optional[str] = None
    order_index: int = 0
    is_featured: bool = False
    is_active: bool = True

class HomepageGalleryCreate(HomepageGalleryBase):
    pass

class HomepageGalleryUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    order_index: Optional[int] = None
    is_featured: Optional[bool] = None
    is_active: Optional[bool] = None

class HomepageGalleryResponse(HomepageGalleryBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

# Esquema completo para la homepage
class HomepageData(BaseModel):
    content: List[HomepageContentResponse]
    gallery: List[HomepageGalleryResponse]