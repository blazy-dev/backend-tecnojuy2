from datetime import datetime
from typing import List, Optional, Tuple
from fastapi import Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, asc, func, or_
from app.db.models import Post, Category, Tag, User
from app.db.session import get_db
from app.blog.schemas import (
    PostCreate, PostUpdate, CategoryCreate, CategoryUpdate, 
    TagCreate, TagUpdate, PostsPaginatedResponse, PostListResponse
)
from app.storage.r2 import r2_service
import re
import logging

logger = logging.getLogger(__name__)


class BlogService:
    def __init__(self, db: Session):
        self.db = db

    def generate_slug(self, title: str, model_class, exclude_id: Optional[int] = None) -> str:
        """Genera un slug único basado en el título"""
        # Convertir a minúsculas y reemplazar caracteres especiales
        slug = re.sub(r'[^a-zA-Z0-9\s-]', '', title.lower())
        slug = re.sub(r'\s+', '-', slug).strip('-')
        
        # Verificar unicidad
        counter = 0
        original_slug = slug
        
        while True:
            query = self.db.query(model_class).filter(model_class.slug == slug)
            if exclude_id:
                query = query.filter(model_class.id != exclude_id)
            
            if not query.first():
                break
                
            counter += 1
            slug = f"{original_slug}-{counter}"
        
        return slug

    def calculate_reading_time(self, content: str) -> int:
        """Calcula el tiempo estimado de lectura (200 palabras por minuto)"""
        word_count = len(content.split())
        return max(1, round(word_count / 200))

    # --- Métodos para Posts ---

    def create_post(self, post_data: PostCreate, author_id: int) -> Post:
        """Crea un nuevo post"""
        # Generar slug único si no se proporciona
        if not post_data.slug:
            post_data.slug = self.generate_slug(post_data.title, Post)
        else:
            # Verificar que el slug sea único
            existing = self.db.query(Post).filter(Post.slug == post_data.slug).first()
            if existing:
                raise ValueError(f"Ya existe un post con el slug: {post_data.slug}")

        # Calcular tiempo de lectura si no se proporciona
        reading_time = post_data.reading_time_minutes
        if not reading_time:
            reading_time = self.calculate_reading_time(post_data.content)

        # Crear el post
        post = Post(
            title=post_data.title,
            slug=post_data.slug,
            excerpt=post_data.excerpt,
            content=post_data.content,
            featured_image_url=post_data.featured_image_url,
            meta_title=post_data.meta_title,
            meta_description=post_data.meta_description,
            is_published=post_data.is_published,
            is_featured=post_data.is_featured,
            reading_time_minutes=reading_time,
            category_id=post_data.category_id,
            author_id=author_id,
            published_at=datetime.utcnow() if post_data.is_published else None
        )

        self.db.add(post)
        self.db.flush()  # Para obtener el ID

        # Asignar tags
        if post_data.tag_ids:
            tags = self.db.query(Tag).filter(Tag.id.in_(post_data.tag_ids)).all()
            post.tags = tags

        self.db.commit()
        self.db.refresh(post)
        return post

    def get_posts(
        self, 
        page: int = 1, 
        per_page: int = 10,
        published_only: bool = False,
        category_id: Optional[int] = None,
        tag_id: Optional[int] = None,
        featured_only: bool = False,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> PostsPaginatedResponse:
        """Obtiene posts con paginación y filtros"""
        query = self.db.query(Post).options(
            joinedload(Post.author),
            joinedload(Post.category),
            joinedload(Post.tags)
        )

        # Aplicar filtros
        if published_only:
            query = query.filter(Post.is_published == True)
        
        if category_id:
            query = query.filter(Post.category_id == category_id)
        
        if tag_id:
            query = query.join(Post.tags).filter(Tag.id == tag_id)
        
        if featured_only:
            query = query.filter(Post.is_featured == True)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Post.title.ilike(search_term),
                    Post.excerpt.ilike(search_term),
                    Post.content.ilike(search_term)
                )
            )

        # Aplicar ordenamiento
        if sort_by == "title":
            order_col = Post.title
        elif sort_by == "published_at":
            order_col = Post.published_at
        elif sort_by == "views_count":
            order_col = Post.views_count
        else:  # created_at por defecto
            order_col = Post.created_at

        if sort_order == "asc":
            query = query.order_by(asc(order_col))
        else:
            query = query.order_by(desc(order_col))

        # Paginación
        total = query.count()
        posts = query.offset((page - 1) * per_page).limit(per_page).all()
        
        pages = (total + per_page - 1) // per_page
        has_next = page < pages
        has_prev = page > 1

        # Convertir a response schema
        post_responses = []
        for post in posts:
            post_responses.append(PostListResponse.from_orm(post))

        return PostsPaginatedResponse(
            posts=post_responses,
            total=total,
            page=page,
            pages=pages,
            has_next=has_next,
            has_prev=has_prev
        )

    def get_post_by_id(self, post_id: int, published_only: bool = False) -> Optional[Post]:
        """Obtiene un post por ID"""
        query = self.db.query(Post).options(
            joinedload(Post.author),
            joinedload(Post.category),
            joinedload(Post.tags)
        ).filter(Post.id == post_id)
        
        if published_only:
            query = query.filter(Post.is_published == True)
        
        return query.first()

    def get_post_by_slug(self, slug: str, published_only: bool = False) -> Optional[Post]:
        """Obtiene un post por slug"""
        query = self.db.query(Post).options(
            joinedload(Post.author),
            joinedload(Post.category),
            joinedload(Post.tags)
        ).filter(Post.slug == slug)
        
        if published_only:
            query = query.filter(Post.is_published == True)
        
        return query.first()

    def update_post(self, post_id: int, post_data: PostUpdate) -> Optional[Post]:
        """Actualiza un post"""
        post = self.db.query(Post).filter(Post.id == post_id).first()
        if not post:
            return None

        # Actualizar campos
        for field, value in post_data.dict(exclude_unset=True).items():
            if field == "tag_ids":
                if value is not None:
                    tags = self.db.query(Tag).filter(Tag.id.in_(value)).all()
                    post.tags = tags
            elif field == "slug" and value:
                # Verificar unicidad del slug
                existing = self.db.query(Post).filter(
                    Post.slug == value, 
                    Post.id != post_id
                ).first()
                if existing:
                    raise ValueError(f"Ya existe un post con el slug: {value}")
                setattr(post, field, value)
            else:
                if hasattr(post, field) and value is not None:
                    setattr(post, field, value)

        # Actualizar published_at si se está publicando
        if post_data.is_published and not post.published_at:
            post.published_at = datetime.utcnow()
        elif post_data.is_published is False:
            post.published_at = None

        post.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(post)
        return post

    async def delete_post(self, post_id: int) -> bool:
        """Elimina un post y sus archivos asociados"""
        post = self.db.query(Post).filter(Post.id == post_id).first()
        if not post:
            return False

        try:
            # Eliminar imagen destacada de R2 si existe
            if post.featured_image_object_key:
                try:
                    await r2_service.delete_file(post.featured_image_object_key)
                    logger.info(f"Imagen destacada eliminada de R2: {post.featured_image_object_key}")
                except Exception as e:
                    logger.warning(f"Error al eliminar imagen de R2: {e}")

            # Eliminar el post de la base de datos
            self.db.delete(post)
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error al eliminar post {post_id}: {e}")
            self.db.rollback()
            return False

    def increment_views(self, post_id: int) -> bool:
        """Incrementa el contador de vistas de un post"""
        try:
            self.db.query(Post).filter(Post.id == post_id).update({
                Post.views_count: Post.views_count + 1
            })
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error al incrementar vistas del post {post_id}: {e}")
            self.db.rollback()
            return False

    # --- Métodos para Categorías ---

    def create_category(self, category_data: CategoryCreate) -> Category:
        """Crea una nueva categoría"""
        # Verificar unicidad del slug
        existing = self.db.query(Category).filter(Category.slug == category_data.slug).first()
        if existing:
            raise ValueError(f"Ya existe una categoría con el slug: {category_data.slug}")

        category = Category(**category_data.dict())
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    def get_categories(self) -> List[Category]:
        """Obtiene todas las categorías con conteo de posts"""
        return self.db.query(Category).order_by(Category.name).all()

    def get_category_by_id(self, category_id: int) -> Optional[Category]:
        """Obtiene una categoría por ID"""
        return self.db.query(Category).filter(Category.id == category_id).first()

    def update_category(self, category_id: int, category_data: CategoryUpdate) -> Optional[Category]:
        """Actualiza una categoría"""
        category = self.db.query(Category).filter(Category.id == category_id).first()
        if not category:
            return None

        for field, value in category_data.dict(exclude_unset=True).items():
            if field == "slug" and value:
                # Verificar unicidad del slug
                existing = self.db.query(Category).filter(
                    Category.slug == value,
                    Category.id != category_id
                ).first()
                if existing:
                    raise ValueError(f"Ya existe una categoría con el slug: {value}")
            
            if hasattr(category, field) and value is not None:
                setattr(category, field, value)

        self.db.commit()
        self.db.refresh(category)
        return category

    def delete_category(self, category_id: int) -> bool:
        """Elimina una categoría"""
        category = self.db.query(Category).filter(Category.id == category_id).first()
        if not category:
            return False

        # Verificar si tiene posts asociados
        posts_count = self.db.query(Post).filter(Post.category_id == category_id).count()
        if posts_count > 0:
            raise ValueError("No se puede eliminar una categoría que tiene posts asociados")

        self.db.delete(category)
        self.db.commit()
        return True

    # --- Métodos para Tags ---

    def create_tag(self, tag_data: TagCreate) -> Tag:
        """Crea un nuevo tag"""
        # Verificar unicidad del slug
        existing = self.db.query(Tag).filter(Tag.slug == tag_data.slug).first()
        if existing:
            raise ValueError(f"Ya existe un tag con el slug: {tag_data.slug}")

        tag = Tag(**tag_data.dict())
        self.db.add(tag)
        self.db.commit()
        self.db.refresh(tag)
        return tag

    def get_tags(self) -> List[Tag]:
        """Obtiene todos los tags con conteo de posts"""
        return self.db.query(Tag).order_by(Tag.name).all()

    def get_tag_by_id(self, tag_id: int) -> Optional[Tag]:
        """Obtiene un tag por ID"""
        return self.db.query(Tag).filter(Tag.id == tag_id).first()

    def update_tag(self, tag_id: int, tag_data: TagUpdate) -> Optional[Tag]:
        """Actualiza un tag"""
        tag = self.db.query(Tag).filter(Tag.id == tag_id).first()
        if not tag:
            return None

        for field, value in tag_data.dict(exclude_unset=True).items():
            if field == "slug" and value:
                # Verificar unicidad del slug
                existing = self.db.query(Tag).filter(
                    Tag.slug == value,
                    Tag.id != tag_id
                ).first()
                if existing:
                    raise ValueError(f"Ya existe un tag con el slug: {value}")
            
            if hasattr(tag, field) and value is not None:
                setattr(tag, field, value)

        self.db.commit()
        self.db.refresh(tag)
        return tag

    def delete_tag(self, tag_id: int) -> bool:
        """Elimina un tag"""
        tag = self.db.query(Tag).filter(Tag.id == tag_id).first()
        if not tag:
            return False

        self.db.delete(tag)
        self.db.commit()
        return True

    # --- Métodos de estadísticas ---

    def get_blog_stats(self) -> dict:
        """Obtiene estadísticas del blog"""
        total_posts = self.db.query(Post).count()
        published_posts = self.db.query(Post).filter(Post.is_published == True).count()
        draft_posts = total_posts - published_posts
        total_views = self.db.query(func.sum(Post.views_count)).scalar() or 0
        total_categories = self.db.query(Category).count()
        total_tags = self.db.query(Tag).count()
        featured_posts = self.db.query(Post).filter(Post.is_featured == True).count()

        return {
            "total_posts": total_posts,
            "published_posts": published_posts,
            "draft_posts": draft_posts,
            "total_views": total_views,
            "total_categories": total_categories,
            "total_tags": total_tags,
            "featured_posts": featured_posts
        }


def get_blog_service(db: Session = Depends(get_db)) -> BlogService:
    """Factory function para obtener una instancia del servicio de blog"""
    return BlogService(db)
