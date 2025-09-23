from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from app.db.models import Post, User
from app.posts.schemas import PostCreate, PostUpdate

class PostService:
    @staticmethod
    def get_post_by_id(db: Session, post_id: int, include_unpublished: bool = False) -> Optional[Post]:
        """Obtener post por ID"""
        query = db.query(Post).join(User).filter(Post.id == post_id)
        
        if not include_unpublished:
            query = query.filter(Post.is_published == True)
        
        return query.first()
    
    @staticmethod
    def get_posts(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        author_id: Optional[int] = None,
        is_published: Optional[bool] = None,
        include_unpublished: bool = False
    ) -> List[Post]:
        """Obtener lista de posts con filtros"""
        query = db.query(Post).join(User)
        
        # Filtro por autor
        if author_id:
            query = query.filter(Post.author_id == author_id)
        
        # Filtro por estado de publicación
        if is_published is not None:
            query = query.filter(Post.is_published == is_published)
        elif not include_unpublished:
            # Por defecto, solo mostrar posts publicados
            query = query.filter(Post.is_published == True)
        
        # Ordenar por fecha de creación (más reciente primero)
        query = query.order_by(desc(Post.created_at))
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def create_post(db: Session, post_data: PostCreate, author_id: int) -> Post:
        """Crear nuevo post"""
        post = Post(
            **post_data.model_dump(),
            author_id=author_id
        )
        db.add(post)
        db.commit()
        db.refresh(post)
        return post
    
    @staticmethod
    def update_post(
        db: Session, 
        post_id: int, 
        post_data: PostUpdate,
        author_id: Optional[int] = None
    ) -> Optional[Post]:
        """Actualizar post"""
        query = db.query(Post).filter(Post.id == post_id)
        
        # Si se especifica author_id, verificar que sea el autor
        if author_id:
            query = query.filter(Post.author_id == author_id)
        
        post = query.first()
        if not post:
            return None
        
        # Actualizar campos
        for field, value in post_data.model_dump(exclude_unset=True).items():
            setattr(post, field, value)
        
        db.commit()
        db.refresh(post)
        return post
    
    @staticmethod
    def delete_post(db: Session, post_id: int, author_id: Optional[int] = None) -> bool:
        """Eliminar post"""
        query = db.query(Post).filter(Post.id == post_id)
        
        # Si se especifica author_id, verificar que sea el autor
        if author_id:
            query = query.filter(Post.author_id == author_id)
        
        post = query.first()
        if not post:
            return False
        
        db.delete(post)
        db.commit()
        return True
    
    @staticmethod
    def get_posts_count(
        db: Session,
        author_id: Optional[int] = None,
        is_published: Optional[bool] = None,
        include_unpublished: bool = False
    ) -> int:
        """Obtener conteo total de posts"""
        query = db.query(Post)
        
        if author_id:
            query = query.filter(Post.author_id == author_id)
        
        if is_published is not None:
            query = query.filter(Post.is_published == is_published)
        elif not include_unpublished:
            query = query.filter(Post.is_published == True)
        
        return query.count()
    
    @staticmethod
    def search_posts(
        db: Session,
        search_term: str,
        skip: int = 0,
        limit: int = 100,
        include_unpublished: bool = False
    ) -> List[Post]:
        """Buscar posts por término"""
        query = db.query(Post).join(User)
        
        if not include_unpublished:
            query = query.filter(Post.is_published == True)
        
        # Buscar en título y contenido
        search_filter = Post.title.contains(search_term) | Post.content.contains(search_term)
        query = query.filter(search_filter)
        
        # Ordenar por relevancia (título primero) y fecha
        query = query.order_by(
            Post.title.contains(search_term).desc(),
            desc(Post.created_at)
        )
        
        return query.offset(skip).limit(limit).all()


