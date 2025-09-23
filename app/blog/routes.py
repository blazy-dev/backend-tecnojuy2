from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.auth.dependencies import get_current_user, require_admin
from app.db.models import User
from app.blog.service import get_blog_service, BlogService
from app.blog.schemas import (
    PostCreate, PostUpdate, PostResponse, PostListResponse, PostsPaginatedResponse,
    CategoryCreate, CategoryUpdate, CategoryResponse,
    TagCreate, TagUpdate, TagResponse,
    BlogStatsResponse
)
from app.storage.r2 import r2_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# --- Rutas Públicas del Blog ---

@router.get("/posts", response_model=PostsPaginatedResponse)
async def get_public_posts(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    category_id: Optional[int] = Query(None),
    tag_id: Optional[int] = Query(None),
    featured_only: bool = Query(False),
    search: Optional[str] = Query(None),
    sort_by: str = Query("published_at", pattern="^(title|published_at|views_count|created_at)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    blog_service: BlogService = Depends(get_blog_service)
):
    """Obtiene posts publicados con paginación y filtros (público)"""
    try:
        return blog_service.get_posts(
            page=page,
            per_page=per_page,
            published_only=True,  # Solo posts publicados para público
            category_id=category_id,
            tag_id=tag_id,
            featured_only=featured_only,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order
        )
    except Exception as e:
        logger.error(f"Error al obtener posts públicos: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/posts/{slug}", response_model=PostResponse)
async def get_public_post_by_slug(
    slug: str,
    db: Session = Depends(get_db),
    blog_service: BlogService = Depends(get_blog_service)
):
    """Obtiene un post por slug (público)"""
    post = blog_service.get_post_by_slug(slug, published_only=True)
    if not post:
        raise HTTPException(status_code=404, detail="Post no encontrado")
    
    # Incrementar contador de vistas
    blog_service.increment_views(post.id)
    
    return post

@router.get("/categories", response_model=List[CategoryResponse])
async def get_public_categories(
    db: Session = Depends(get_db),
    blog_service: BlogService = Depends(get_blog_service)
):
    """Obtiene todas las categorías (público)"""
    try:
        categories = blog_service.get_categories()
        # Agregar conteo de posts publicados para cada categoría
        result = []
        for category in categories:
            published_posts_count = len([p for p in category.posts if p.is_published])
            category_response = CategoryResponse.from_orm(category)
            category_response.posts_count = published_posts_count
            result.append(category_response)
        return result
    except Exception as e:
        logger.error(f"Error al obtener categorías: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/tags", response_model=List[TagResponse])
async def get_public_tags(
    db: Session = Depends(get_db),
    blog_service: BlogService = Depends(get_blog_service)
):
    """Obtiene todos los tags (público)"""
    try:
        tags = blog_service.get_tags()
        # Agregar conteo de posts publicados para cada tag
        result = []
        for tag in tags:
            published_posts_count = len([p for p in tag.posts if p.is_published])
            tag_response = TagResponse.from_orm(tag)
            tag_response.posts_count = published_posts_count
            result.append(tag_response)
        return result
    except Exception as e:
        logger.error(f"Error al obtener tags: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

# --- Rutas de Administración ---

@router.get("/admin/posts", response_model=PostsPaginatedResponse)
async def get_admin_posts(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    category_id: Optional[int] = Query(None),
    tag_id: Optional[int] = Query(None),
    featured_only: bool = Query(False),
    search: Optional[str] = Query(None),
    published_only: Optional[bool] = Query(None),
    sort_by: str = Query("created_at", pattern="^(title|published_at|views_count|created_at)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    blog_service: BlogService = Depends(get_blog_service)
):
    """Obtiene todos los posts para administradores"""
    try:
        return blog_service.get_posts(
            page=page,
            per_page=per_page,
            published_only=published_only if published_only is not None else False,
            category_id=category_id,
            tag_id=tag_id,
            featured_only=featured_only,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order
        )
    except Exception as e:
        logger.error(f"Error al obtener posts admin: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/admin/posts", response_model=PostResponse)
async def create_post(
    post_data: PostCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    blog_service: BlogService = Depends(get_blog_service)
):
    """Crea un nuevo post"""
    try:
        return blog_service.create_post(post_data, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error al crear post: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/admin/posts/{post_id}", response_model=PostResponse)
async def get_admin_post(
    post_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    blog_service: BlogService = Depends(get_blog_service)
):
    """Obtiene un post por ID (admin)"""
    post = blog_service.get_post_by_id(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post no encontrado")
    return post

@router.put("/admin/posts/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: int,
    post_data: PostUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    blog_service: BlogService = Depends(get_blog_service)
):
    """Actualiza un post"""
    try:
        post = blog_service.update_post(post_id, post_data)
        if not post:
            raise HTTPException(status_code=404, detail="Post no encontrado")
        return post
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error al actualizar post {post_id}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.delete("/admin/posts/{post_id}")
async def delete_post(
    post_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    blog_service: BlogService = Depends(get_blog_service)
):
    """Elimina un post"""
    try:
        success = await blog_service.delete_post(post_id)
        if not success:
            raise HTTPException(status_code=404, detail="Post no encontrado")
        return {"message": "Post eliminado exitosamente"}
    except Exception as e:
        logger.error(f"Error al eliminar post {post_id}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

# --- Rutas para Categorías (Admin) ---

@router.post("/admin/categories", response_model=CategoryResponse)
async def create_category(
    category_data: CategoryCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    blog_service: BlogService = Depends(get_blog_service)
):
    """Crea una nueva categoría"""
    try:
        return blog_service.create_category(category_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error al crear categoría: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/admin/categories", response_model=List[CategoryResponse])
async def get_admin_categories(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    blog_service: BlogService = Depends(get_blog_service)
):
    """Obtiene todas las categorías (admin)"""
    try:
        categories = blog_service.get_categories()
        result = []
        for category in categories:
            category_response = CategoryResponse.from_orm(category)
            category_response.posts_count = len(category.posts)
            result.append(category_response)
        return result
    except Exception as e:
        logger.error(f"Error al obtener categorías admin: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.put("/admin/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    blog_service: BlogService = Depends(get_blog_service)
):
    """Actualiza una categoría"""
    try:
        category = blog_service.update_category(category_id, category_data)
        if not category:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")
        return category
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error al actualizar categoría {category_id}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.delete("/admin/categories/{category_id}")
async def delete_category(
    category_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    blog_service: BlogService = Depends(get_blog_service)
):
    """Elimina una categoría"""
    try:
        success = blog_service.delete_category(category_id)
        if not success:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")
        return {"message": "Categoría eliminada exitosamente"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error al eliminar categoría {category_id}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

# --- Rutas para Tags (Admin) ---

@router.post("/admin/tags", response_model=TagResponse)
async def create_tag(
    tag_data: TagCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    blog_service: BlogService = Depends(get_blog_service)
):
    """Crea un nuevo tag"""
    try:
        return blog_service.create_tag(tag_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error al crear tag: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/admin/tags", response_model=List[TagResponse])
async def get_admin_tags(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    blog_service: BlogService = Depends(get_blog_service)
):
    """Obtiene todos los tags (admin)"""
    try:
        tags = blog_service.get_tags()
        result = []
        for tag in tags:
            tag_response = TagResponse.from_orm(tag)
            tag_response.posts_count = len(tag.posts)
            result.append(tag_response)
        return result
    except Exception as e:
        logger.error(f"Error al obtener tags admin: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.put("/admin/tags/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: int,
    tag_data: TagUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    blog_service: BlogService = Depends(get_blog_service)
):
    """Actualiza un tag"""
    try:
        tag = blog_service.update_tag(tag_id, tag_data)
        if not tag:
            raise HTTPException(status_code=404, detail="Tag no encontrado")
        return tag
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error al actualizar tag {tag_id}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.delete("/admin/tags/{tag_id}")
async def delete_tag(
    tag_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    blog_service: BlogService = Depends(get_blog_service)
):
    """Elimina un tag"""
    try:
        success = blog_service.delete_tag(tag_id)
        if not success:
            raise HTTPException(status_code=404, detail="Tag no encontrado")
        return {"message": "Tag eliminado exitosamente"}
    except Exception as e:
        logger.error(f"Error al eliminar tag {tag_id}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

# --- Rutas para Imágenes del Blog ---



@router.post("/admin/upload-featured-image")
async def upload_featured_image(
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin)
):
    """Sube una imagen destacada para posts"""
    try:
        # Validar tipo de archivo
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Solo se permiten archivos de imagen")

        # Leer contenido para validar tamaño de forma segura (máximo 5MB)
        file_content = await file.read()
        max_bytes = 5 * 1024 * 1024
        if len(file_content) > max_bytes:
            raise HTTPException(status_code=400, detail="La imagen no puede ser mayor a 5MB")

        # Limpiar nombre del archivo (remover espacios y caracteres especiales)
        import re
        clean_filename = re.sub(r'[^\w\-_\.]', '_', file.filename)
        clean_filename = re.sub(r'_+', '_', clean_filename)  # Múltiples _ a uno solo
        
        # Subir a R2
        object_key = f"blog/featured/{clean_filename}"
        
        success, error = await r2_service.upload_file_to_public_bucket(
            object_key=object_key,
            content=file_content,
            content_type=file.content_type
        )
        
        if not success:
            raise HTTPException(status_code=500, detail=f"Error al subir imagen: {error}")
        
        # Generar URL pública directa (bucket público)
        public_url = f"{r2_service.public_bucket_url}/{object_key}"
        
        return {
            "public_url": public_url,
            "object_key": object_key,
            "filename": clean_filename,
            "content_type": file.content_type,
            "size": len(file_content)
        }
        
    except Exception as e:
        logger.error(f"Error al subir imagen destacada: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

# --- Rutas de Estadísticas ---

@router.get("/admin/stats", response_model=BlogStatsResponse)
async def get_blog_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    blog_service: BlogService = Depends(get_blog_service)
):
    """Obtiene estadísticas del blog"""
    try:
        stats = blog_service.get_blog_stats()
        return BlogStatsResponse(**stats)
    except Exception as e:
        logger.error(f"Error al obtener estadísticas del blog: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")
