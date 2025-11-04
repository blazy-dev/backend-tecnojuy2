from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.auth.dependencies import get_current_user, require_admin
from app.users.schemas import UserResponse, UserUpdate, RoleResponse
from app.users.service import UserService, RoleService
from app.db.models import User

router = APIRouter()

@router.get("/debug-users-public")
async def debug_users_public(db: Session = Depends(get_db)):
    """Debug users - PUBLIC ENDPOINT - TEMPORARY"""
    from app.db.models import Role
    
    total_users = db.query(User).count()
    users = db.query(User).join(Role).limit(5).all()
    
    return {
        "total_users": total_users,
        "users_sample": [
            {
                "id": u.id,
                "name": u.name,
                "email": u.email[:10] + "...",  # Truncar email por privacidad
                "role_name": u.role.name if u.role else "No role",
                "is_active": u.is_active,
                "has_premium_access": u.has_premium_access,
                "created_at": u.created_at.isoformat() if u.created_at else None
            } for u in users
        ]
    }

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

@router.get("/admin/stats/")
async def get_users_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Obtener estadísticas de usuarios para el dashboard admin"""
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    premium_users = db.query(User).filter(User.has_premium_access == True).count()
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "premium_users": premium_users,
        "inactive_users": total_users - active_users
    }

@router.get("/")
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    role_name: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    course_id: Optional[int] = Query(None, description="Filtrar por curso con acceso"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Obtener lista de usuarios con paginación y filtros (solo admin)"""
    from app.db.models import CourseAccess
    
    # Query base
    query = db.query(User).join(User.role)
    
    # Filtrar por rol
    if role_name:
        query = query.filter(User.role.has(name=role_name))
    
    # Filtrar por estado activo
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    # Filtrar por curso con acceso
    if course_id:
        query = query.join(CourseAccess).filter(CourseAccess.course_id == course_id)
    
    # Contar total antes de paginar
    total = query.count()
    
    # Ordenar por fecha de creación (más recientes primero)
    query = query.order_by(User.created_at.desc())
    
    # Paginar
    users = query.offset(skip).limit(limit).all()
    
    # Formatear respuesta
    result = []
    for user in users:
        result.append({
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "avatar_url": user.avatar_url,
            "google_id": user.google_id,
            "is_active": user.is_active,
            "has_premium_access": user.has_premium_access,
            "role_name": user.role.name,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None
        })
    
    # Si NO hay filtro de curso, devolver lista simple (compatibilidad con código antiguo)
    # Si HAY filtro de curso, devolver objeto con metadata
    if course_id:
        return {
            "users": result,
            "total": total,
            "skip": skip,
            "limit": limit,
            "has_more": (skip + limit) < total
        }
    else:
        # Devolver lista simple para mantener compatibilidad
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


