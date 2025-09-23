from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.models import HomepageContent, HomepageGallery
from app.homepage.schemas import (
    HomepageContentCreate, HomepageContentUpdate,
    HomepageGalleryCreate, HomepageGalleryUpdate
)

class HomepageService:
    
    # ===== HOMEPAGE CONTENT =====
    
    def get_all_content(self, db: Session) -> List[HomepageContent]:
        """Obtener todo el contenido del homepage ordenado por order_index"""
        return db.query(HomepageContent).filter(
            HomepageContent.is_active == True
        ).order_by(HomepageContent.order_index).all()
    
    def get_content_by_section(self, db: Session, section: str) -> Optional[HomepageContent]:
        """Obtener contenido por sección"""
        return db.query(HomepageContent).filter(
            HomepageContent.section == section,
            HomepageContent.is_active == True
        ).first()
    
    def create_content(self, db: Session, content: HomepageContentCreate) -> HomepageContent:
        """Crear nuevo contenido del homepage"""
        db_content = HomepageContent(**content.dict())
        db.add(db_content)
        db.commit()
        db.refresh(db_content)
        return db_content
    
    def update_content(self, db: Session, content_id: int, content: HomepageContentUpdate) -> Optional[HomepageContent]:
        """Actualizar contenido existente"""
        db_content = db.query(HomepageContent).filter(HomepageContent.id == content_id).first()
        if not db_content:
            return None
        
        update_data = content.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_content, key, value)
        
        db.commit()
        db.refresh(db_content)
        return db_content
    
    def delete_content(self, db: Session, content_id: int) -> bool:
        """Eliminar contenido (soft delete)"""
        db_content = db.query(HomepageContent).filter(HomepageContent.id == content_id).first()
        if not db_content:
            return False
        
        db_content.is_active = False
        db.commit()
        return True
    
    # ===== HOMEPAGE GALLERY =====
    
    def get_all_gallery(self, db: Session, featured_only: bool = False) -> List[HomepageGallery]:
        """Obtener todas las imágenes de la galería"""
        query = db.query(HomepageGallery).filter(HomepageGallery.is_active == True)
        
        if featured_only:
            query = query.filter(HomepageGallery.is_featured == True)
        
        return query.order_by(HomepageGallery.order_index).all()
    
    def get_gallery_by_category(self, db: Session, category: str) -> List[HomepageGallery]:
        """Obtener galería por categoría"""
        return db.query(HomepageGallery).filter(
            HomepageGallery.category == category,
            HomepageGallery.is_active == True
        ).order_by(HomepageGallery.order_index).all()
    
    def create_gallery_item(self, db: Session, gallery: HomepageGalleryCreate) -> HomepageGallery:
        """Crear nuevo item de galería"""
        db_gallery = HomepageGallery(**gallery.dict())
        db.add(db_gallery)
        db.commit()
        db.refresh(db_gallery)
        return db_gallery
    
    def update_gallery_item(self, db: Session, gallery_id: int, gallery: HomepageGalleryUpdate) -> Optional[HomepageGallery]:
        """Actualizar item de galería"""
        db_gallery = db.query(HomepageGallery).filter(HomepageGallery.id == gallery_id).first()
        if not db_gallery:
            return None
        
        update_data = gallery.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_gallery, key, value)
        
        db.commit()
        db.refresh(db_gallery)
        return db_gallery
    
    def delete_gallery_item(self, db: Session, gallery_id: int) -> bool:
        """Eliminar item de galería (soft delete)"""
        db_gallery = db.query(HomepageGallery).filter(HomepageGallery.id == gallery_id).first()
        if not db_gallery:
            return False
        
        db_gallery.is_active = False
        db.commit()
        return True

# Instancia del servicio
homepage_service = HomepageService()