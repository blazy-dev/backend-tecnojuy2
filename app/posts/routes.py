from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.auth.dependencies import get_current_user, require_admin
from app.posts.schemas import PostResponse, PostCreate, PostUpdate, PostSummary, AuthorInfo
from app.posts.service import PostService
from app.db.models import User, Post

router = APIRouter()

@router.get("/", response_model=List[PostSummary])
async def get_posts(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    author_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Obtener lista pública de posts"""
    
    if search:
        # Búsqueda por término
        posts = PostService.search_posts(
            db=db,
            search_term=search,
            skip=skip,
            limit=limit,
            include_unpublished=False
        )
    else:
        # Lista normal
        posts = PostService.get_posts(
            db=db,
            skip=skip,
            limit=limit,
            author_id=author_id,
            include_unpublished=False
        )
    
    # Convertir a PostSummary
    result = []
    for post in posts:
        result.append(PostSummary(
            id=post.id,
            title=post.title,
            cover_image_url=getattr(post, 'cover_image_url', None),
            author_name=post.author.name,
            created_at=post.created_at,
            is_published=post.is_published
        ))
    
    return result

@router.get("/{post_id}", response_model=PostResponse)
async def get_post_by_id(
    post_id: int,
    db: Session = Depends(get_db)
):
    """Obtener post por ID (público)"""
    post = PostService.get_post_by_id(db, post_id, include_unpublished=False)
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    return PostResponse(
        id=post.id,
        title=post.title,
        content=post.content,
        cover_image_url=post.cover_image_url,
        is_published=post.is_published,
        author=AuthorInfo(
            id=post.author.id,
            name=post.author.name,
            email=post.author.email,
            avatar_url=post.author.avatar_url
        ),
        created_at=post.created_at,
        updated_at=post.updated_at
    )

@router.post("/", response_model=PostResponse)
async def create_post(
    post_data: PostCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Crear nuevo post (solo admin)"""
    
    post = PostService.create_post(
        db=db,
        post_data=post_data,
        author_id=current_user.id
    )
    
    # Recargar post con información del autor
    post_with_author = PostService.get_post_by_id(db, post.id, include_unpublished=True)
    
    return PostResponse(
        id=post_with_author.id,
        title=post_with_author.title,
        content=post_with_author.content,
        cover_image_url=post_with_author.cover_image_url,
        is_published=post_with_author.is_published,
        author=AuthorInfo(
            id=post_with_author.author.id,
            name=post_with_author.author.name,
            email=post_with_author.author.email,
            avatar_url=post_with_author.author.avatar_url
        ),
        created_at=post_with_author.created_at,
        updated_at=post_with_author.updated_at
    )

@router.put("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: int,
    post_data: PostUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Actualizar post (solo admin)"""
    
    updated_post = PostService.update_post(
        db=db,
        post_id=post_id,
        post_data=post_data
    )
    
    if not updated_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # Recargar post con información del autor
    post_with_author = PostService.get_post_by_id(db, updated_post.id, include_unpublished=True)
    
    return PostResponse(
        id=post_with_author.id,
        title=post_with_author.title,
        content=post_with_author.content,
        cover_image_url=post_with_author.cover_image_url,
        is_published=post_with_author.is_published,
        author=AuthorInfo(
            id=post_with_author.author.id,
            name=post_with_author.author.name,
            email=post_with_author.author.email,
            avatar_url=post_with_author.author.avatar_url
        ),
        created_at=post_with_author.created_at,
        updated_at=post_with_author.updated_at
    )

@router.delete("/{post_id}")
async def delete_post(
    post_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Eliminar post (solo admin)"""
    
    success = PostService.delete_post(db=db, post_id=post_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    return {"message": "Post deleted successfully"}

@router.get("/admin/all/", response_model=List[PostSummary])
async def get_all_posts_admin(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    is_published: Optional[bool] = Query(None),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Obtener todos los posts incluyendo no publicados (solo admin)"""
    
    posts = PostService.get_posts(
        db=db,
        skip=skip,
        limit=limit,
        is_published=is_published,
        include_unpublished=True
    )
    
    # Convertir a PostSummary
    result = []
    for post in posts:
        result.append(PostSummary(
            id=post.id,
            title=post.title,
            cover_image_url=getattr(post, 'cover_image_url', None),
            author_name=post.author.name,
            created_at=post.created_at,
            is_published=post.is_published
        ))
    
    return result

@router.get("/admin/{post_id}/", response_model=PostResponse)
async def get_post_admin(
    post_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Obtener post por ID incluyendo no publicados (solo admin)"""
    
    post = PostService.get_post_by_id(db, post_id, include_unpublished=True)
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    return PostResponse(
        id=post.id,
        title=post.title,
        content=post.content,
        cover_image_url=post.cover_image_url,
        is_published=post.is_published,
        author=AuthorInfo(
            id=post.author.id,
            name=post.author.name,
            email=post.author.email,
            avatar_url=post.author.avatar_url
        ),
        created_at=post.created_at,
        updated_at=post.updated_at
    )


