from typing import Optional
from fastapi import Depends, HTTPException, status, Request, Cookie
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import User, Role
from app.core.security import verify_token

def get_current_user(
    request: Request,
    access_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
) -> User:
    """Obtener usuario actual desde el token JWT"""
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No access token provided"
        )
    
    # Verificar token
    payload = verify_token(access_token, "access")
    user_id = payload.get("sub")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Buscar usuario en base de datos
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive"
        )
    
    return user

def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Obtener usuario activo actual"""
    return current_user

def require_role(required_role: str):
    """Dependency factory para requerir un rol específico"""
    def role_checker(
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ) -> User:
        # Cargar rol del usuario
        user_with_role = db.query(User).join(Role).filter(User.id == current_user.id).first()
        
        if not user_with_role or user_with_role.role.name != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required"
            )
        
        return user_with_role
    
    return role_checker

# Shortcuts para roles específicos
require_admin = require_role("admin")
require_alumno = require_role("alumno")

def get_current_user_optional(
    request: Request,
    access_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Obtener usuario actual opcionalmente (sin lanzar error si no está autenticado)"""
    print(f"[DEBUG] get_current_user_optional called")
    print(f"[DEBUG] access_token from Cookie: {access_token}")
    print(f"[DEBUG] request.cookies: {dict(request.cookies)}")
    
    if not access_token:
        return None
    
    try:
        # Verificar token
        print(f"[DEBUG] Trying to verify access token: {access_token[:50]}...")
        payload = verify_token(access_token, "access")
        user_id = payload.get("sub")
        print(f"[DEBUG] Token verified, user_id: {user_id}")
        
        if not user_id:
            return None
        
        # Buscar usuario en base de datos
        user = db.query(User).filter(User.id == user_id).first()
        print(f"[DEBUG] User found: {user}")
        if not user or not user.is_active:
            return None
        
        return user
    except Exception as e:
        # Si hay cualquier error en la verificación, simplemente devolver None
        print(f"[DEBUG] Exception in get_current_user_optional: {e}")
        return None

