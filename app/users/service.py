from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db.models import User, Role
from app.users.schemas import UserCreate, UserUpdate

class UserService:
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """Obtener usuario por ID"""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Obtener usuario por email"""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_user_by_google_id(db: Session, google_id: str) -> Optional[User]:
        """Obtener usuario por Google ID"""
        return db.query(User).filter(User.google_id == google_id).first()
    
    @staticmethod
    def get_users(
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        role_name: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[User]:
        """Obtener lista de usuarios con filtros"""
        query = db.query(User).join(Role)
        
        if role_name:
            query = query.filter(Role.name == role_name)
        
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def get_users_count(db: Session) -> int:
        """Obtener el número total de usuarios registrados"""
        return db.query(User).count()
    
    @staticmethod
    def create_user(db: Session, user_data: UserCreate) -> User:
        """Crear nuevo usuario"""
        user = User(**user_data.model_dump())
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def update_user(db: Session, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """Actualizar usuario"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        for field, value in user_data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)
        
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def delete_user(db: Session, user_id: int) -> bool:
        """Eliminar usuario (soft delete)"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        user.is_active = False
        db.commit()
        return True

class RoleService:
    @staticmethod
    def get_roles(db: Session) -> List[Role]:
        """Obtener todos los roles"""
        return db.query(Role).all()
    
    @staticmethod
    def get_role_by_name(db: Session, name: str) -> Optional[Role]:
        """Obtener rol por nombre"""
        return db.query(Role).filter(Role.name == name).first()
    
    @staticmethod
    def create_role(db: Session, name: str, description: str = None) -> Role:
        """Crear nuevo rol"""
        role = Role(name=name, description=description)
        db.add(role)
        db.commit()
        db.refresh(role)
        return role

