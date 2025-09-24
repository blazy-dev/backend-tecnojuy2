from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.db.session import get_db
from app.db.models import HomepageContent, HomepageGallery, User
from app.auth.dependencies import require_admin
from app.homepage.service import homepage_service
from app.core.config import settings
from app.homepage.schemas import (
    HomepageContentCreate, HomepageContentUpdate, HomepageContentResponse,
    HomepageGalleryCreate, HomepageGalleryUpdate, HomepageGalleryResponse,
    HomepageData
)
from app.storage.r2 import r2_service

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/debug-r2-public")
async def debug_r2_config_public():
    """Debug R2 configuration - PUBLIC ENDPOINT - TEMPORARY"""
    from app.core.config import settings
    return {
        "r2_enabled": r2_service.enabled,
        "has_client": r2_service.client is not None,
        "bucket_name": bool(r2_service.bucket_name),
        "public_url": bool(r2_service.public_url),
        "public_bucket_name": bool(r2_service.public_bucket_name),
        "public_bucket_url": bool(r2_service.public_bucket_url),
        "has_endpoint": bool(settings.R2_ENDPOINT_URL),
        "has_access_key": bool(settings.R2_ACCESS_KEY_ID),
        "has_secret_key": bool(settings.R2_SECRET_ACCESS_KEY),
        # Mostrar solo los primeros/últimos caracteres para debug
        "endpoint_preview": settings.R2_ENDPOINT_URL[:20] + "..." + settings.R2_ENDPOINT_URL[-10:] if settings.R2_ENDPOINT_URL else None,
        "bucket_preview": r2_service.bucket_name if r2_service.bucket_name else None,
        "public_bucket_preview": r2_service.public_bucket_name if r2_service.public_bucket_name else None,
    }

# ===== ENDPOINTS PÚBLICOS =====

@router.get("/", response_model=HomepageData)
async def get_homepage_data(db: Session = Depends(get_db)):
    """Obtener todos los datos del homepage para la página pública"""
    content = homepage_service.get_all_content(db)
    gallery = homepage_service.get_all_gallery(db, featured_only=True)
    
    return HomepageData(
        content=[HomepageContentResponse.from_orm(c) for c in content],
        gallery=[HomepageGalleryResponse.from_orm(g) for g in gallery]
    )

@router.get("/users-count")
async def get_users_count_public(db: Session = Depends(get_db)):
    """Obtener el número total de usuarios registrados (endpoint público)"""
    count = db.query(User).count()
    return {"count": count}

@router.get("/content/{section}", response_model=HomepageContentResponse)
async def get_content_by_section(section: str, db: Session = Depends(get_db)):
    """Obtener contenido específico por sección"""
    content = homepage_service.get_content_by_section(db, section)
    if not content:
        raise HTTPException(status_code=404, detail="Sección no encontrada")
    return HomepageContentResponse.from_orm(content)

@router.get("/gallery", response_model=List[HomepageGalleryResponse])
async def get_gallery(
    category: Optional[str] = None,
    featured_only: bool = False,
    db: Session = Depends(get_db)
):
    """Obtener galería de imágenes"""
    if category:
        gallery = homepage_service.get_gallery_by_category(db, category)
    else:
        gallery = homepage_service.get_all_gallery(db, featured_only)
    
    return [HomepageGalleryResponse.from_orm(g) for g in gallery]

# ===== ENDPOINTS DE ADMINISTRACIÓN =====

@router.get("/admin/debug-r2")
async def debug_r2_config(
    _: dict = Depends(require_admin)
):
    """Debug R2 configuration - TEMPORARY ENDPOINT"""
    return {
        "r2_enabled": r2_service.enabled,
        "has_client": r2_service.client is not None,
        "bucket_name": r2_service.bucket_name,
        "public_url": r2_service.public_url,
        "public_bucket_name": r2_service.public_bucket_name,
        "public_bucket_url": r2_service.public_bucket_url,
        "has_endpoint": bool(settings.R2_ENDPOINT_URL),
        "has_access_key": bool(settings.R2_ACCESS_KEY_ID),
        "has_secret_key": bool(settings.R2_SECRET_ACCESS_KEY),
    }

@router.get("/admin/content", response_model=List[HomepageContentResponse])
async def get_all_content_admin(
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Obtener todo el contenido para administración"""
    content = db.query(HomepageContent).all()  # Incluir inactivos
    return [HomepageContentResponse.from_orm(c) for c in content]

@router.post("/admin/content", response_model=HomepageContentResponse)
async def create_content(
    content: HomepageContentCreate,
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Crear nuevo contenido del homepage"""
    db_content = homepage_service.create_content(db, content)
    return HomepageContentResponse.from_orm(db_content)

@router.put("/admin/content/{content_id}", response_model=HomepageContentResponse)
async def update_content(
    content_id: int,
    content: HomepageContentUpdate,
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Actualizar contenido existente"""
    db_content = homepage_service.update_content(db, content_id, content)
    if not db_content:
        raise HTTPException(status_code=404, detail="Contenido no encontrado")
    return HomepageContentResponse.from_orm(db_content)

@router.delete("/admin/content/{content_id}")
async def delete_content(
    content_id: int,
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Eliminar contenido"""
    success = homepage_service.delete_content(db, content_id)
    if not success:
        raise HTTPException(status_code=404, detail="Contenido no encontrado")
    return {"message": "Contenido eliminado exitosamente"}

# ===== GALERÍA =====

@router.get("/admin/gallery", response_model=List[HomepageGalleryResponse])
async def get_all_gallery_admin(
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Obtener toda la galería para administración"""
    gallery = db.query(HomepageGallery).all()
    return [HomepageGalleryResponse.from_orm(g) for g in gallery]

@router.post("/admin/gallery", response_model=HomepageGalleryResponse)
async def create_gallery_item(
    gallery: HomepageGalleryCreate,
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Crear nuevo item de galería"""
    db_gallery = homepage_service.create_gallery_item(db, gallery)
    return HomepageGalleryResponse.from_orm(db_gallery)

@router.put("/admin/gallery/{gallery_id}", response_model=HomepageGalleryResponse)
async def update_gallery_item(
    gallery_id: int,
    gallery: HomepageGalleryUpdate,
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Actualizar item de galería"""
    db_gallery = homepage_service.update_gallery_item(db, gallery_id, gallery)
    if not db_gallery:
        raise HTTPException(status_code=404, detail="Item de galería no encontrado")
    return HomepageGalleryResponse.from_orm(db_gallery)

@router.delete("/admin/gallery/{gallery_id}")
async def delete_gallery_item(
    gallery_id: int,
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Eliminar item de galería"""
    success = homepage_service.delete_gallery_item(db, gallery_id)
    if not success:
        raise HTTPException(status_code=404, detail="Item de galería no encontrado")
    return {"message": "Item de galería eliminado exitosamente"}

# ===== SUBIDA DE IMÁGENES =====

@router.post("/admin/upload-image")
async def upload_homepage_image(
    file: UploadFile = File(...),
    _: dict = Depends(require_admin)
):
    """Subir imagen para el homepage usando R2"""
    try:
        # Validar tipo de archivo
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Solo se permiten archivos de imagen")
        
        # Generar nombre único para R2
        import uuid
        file_extension = file.filename.split('.')[-1] if file.filename and '.' in file.filename else 'jpg'
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        object_key = f"homepage/{unique_filename}"
        
        # Leer el contenido del archivo
        content = await file.read()
        
        # Subir a R2
        success, public_url = await r2_service.upload_file_to_public_bucket(
            object_key=object_key,
            content=content,
            content_type=file.content_type
        )
        
        if not success or not public_url:
            raise HTTPException(status_code=500, detail="Error al subir imagen a R2")
        
        return {
            "success": True,
            "object_key": object_key,
            "url": public_url,
            "message": "Imagen subida exitosamente"
        }
            
    except Exception as e:
        logger.error(f"Error al subir imagen: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al subir imagen: {str(e)}")