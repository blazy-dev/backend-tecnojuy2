from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.auth.dependencies import get_current_user, require_admin
from app.users.schemas import UserResponse, UserUpdate, RoleResponse
from app.users.service import UserService, RoleService
from app.db.models import User

router = APIRouter()

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener perfil del usuario actual"""
    user_with_role = db.query(User).join(User.role).filter(User.id == current_user.id).first()
    
    return UserResponse(
        id=user_with_role.id,
        email=user_with_role.email,
        name=user_with_role.name,
        avatar_url=user_with_role.avatar_url,
        google_id=user_with_role.google_id,
        is_active=user_with_role.is_active,
        has_premium_access=user_with_role.has_premium_access,
        role_name=user_with_role.role.name,
        created_at=user_with_role.created_at,
        updated_at=user_with_role.updated_at
    )

@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Actualizar perfil del usuario actual"""
    # No permitir cambio de rol o estado activo por el usuario mismo
    user_data.role_id = None
    user_data.is_active = None
    
    updated_user = UserService.update_user(db, current_user.id, user_data)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user_with_role = db.query(User).join(User.role).filter(User.id == updated_user.id).first()
    
    return UserResponse(
        id=user_with_role.id,
        email=user_with_role.email,
        name=user_with_role.name,
        avatar_url=user_with_role.avatar_url,
        google_id=user_with_role.google_id,
        is_active=user_with_role.is_active,
        has_premium_access=user_with_role.has_premium_access,
        role_name=user_with_role.role.name,
        created_at=user_with_role.created_at,
        updated_at=user_with_role.updated_at
    )

@router.get("/", response_model=List[UserResponse])
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    role_name: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Obtener lista de usuarios (solo admin)"""
    users = UserService.get_users(
        db=db,
        skip=skip,
        limit=limit,
        role_name=role_name,
        is_active=is_active
    )
    
    result = []
    for user in users:
        user_with_role = db.query(User).join(User.role).filter(User.id == user.id).first()
        result.append(UserResponse(
            id=user_with_role.id,
            email=user_with_role.email,
            name=user_with_role.name,
            avatar_url=user_with_role.avatar_url,
            google_id=user_with_role.google_id,
            is_active=user_with_role.is_active,
            has_premium_access=user_with_role.has_premium_access,
            role_name=user_with_role.role.name,
            created_at=user_with_role.created_at,
            updated_at=user_with_role.updated_at
        ))
    
    return result

@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Obtener usuario por ID (solo admin)"""
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user_with_role = db.query(User).join(User.role).filter(User.id == user.id).first()
    
    return UserResponse(
        id=user_with_role.id,
        email=user_with_role.email,
        name=user_with_role.name,
        avatar_url=user_with_role.avatar_url,
        google_id=user_with_role.google_id,
        is_active=user_with_role.is_active,
        has_premium_access=user_with_role.has_premium_access,
        role_name=user_with_role.role.name,
        created_at=user_with_role.created_at,
        updated_at=user_with_role.updated_at
    )

@router.put("/{user_id}", response_model=UserResponse)
async def update_user_by_id(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Actualizar usuario por ID (solo admin)"""
    updated_user = UserService.update_user(db, user_id, user_data)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user_with_role = db.query(User).join(User.role).filter(User.id == updated_user.id).first()
    
    return UserResponse(
        id=user_with_role.id,
        email=user_with_role.email,
        name=user_with_role.name,
        avatar_url=user_with_role.avatar_url,
        google_id=user_with_role.google_id,
        is_active=user_with_role.is_active,
        has_premium_access=user_with_role.has_premium_access,
        role_name=user_with_role.role.name,
        created_at=user_with_role.created_at,
        updated_at=user_with_role.updated_at
    )

@router.delete("/{user_id}")
async def delete_user_by_id(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Eliminar usuario por ID (solo admin)"""
    success = UserService.delete_user(db, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "User deactivated successfully"}

@router.get("/roles/", response_model=List[RoleResponse])
async def get_roles(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Obtener todos los roles (solo admin)"""
    roles = RoleService.get_roles(db)
    return [RoleResponse(id=role.id, name=role.name, description=role.description) for role in roles]

@router.get("/count")
async def get_users_count(db: Session = Depends(get_db)):
    """Obtener el número total de usuarios registrados (endpoint público)"""
    count = UserService.get_users_count(db)
    return {"count": count}


