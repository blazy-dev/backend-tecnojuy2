from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.db.models import User, Role
from app.core.security import create_access_token, create_refresh_token, verify_token
from app.core.config import settings, FRONTEND_ORIGINS
from app.auth.google import oauth, get_google_user_info
from app.auth.dependencies import get_current_user
from app.auth.dependencies import get_current_user_optional
from app.core.security import verify_token
from app.core.config import FRONTEND_ORIGINS

router = APIRouter()

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict

class UserInfo(BaseModel):
    id: int
    email: str
    name: str
    avatar_url: str | None
    has_premium_access: bool
    role_name: str

@router.get("/debug/cookies")
async def debug_cookies(request: Request):
    """Devuelve las cookies recibidas para depurar problemas de autenticación.
    IMPORTANTE: No dejar este endpoint expuesto en producción final; eliminar cuando esté estable.
    """
    return {"cookies": dict(request.cookies)}

@router.get("/session-info")
async def session_info(request: Request):
    """Devuelve información básica de los tokens (sin requerir DB) para depurar 401.
    Si el token de acceso no es válido intenta inspeccionar el refresh.
    """
    access_cookie = request.cookies.get("access_token")
    refresh_cookie = request.cookies.get("refresh_token")
    info = {
        "has_access_cookie": bool(access_cookie),
        "has_refresh_cookie": bool(refresh_cookie)
    }
    try:
        if access_cookie:
            info["access_claims"] = verify_token(access_cookie, "access")
    except Exception as e:
        info["access_error"] = str(e)
    try:
        if refresh_cookie:
            info["refresh_claims"] = verify_token(refresh_cookie, "refresh")
    except Exception as e:
        info["refresh_error"] = str(e)
    return info

@router.get("/debug/cors")
async def debug_cors(request: Request):
    origin = request.headers.get("origin") or request.headers.get("Origin")
    host = request.headers.get("host")
    return {
        "request_origin": origin,
        "request_host": host,
        "configured_frontend_origins": FRONTEND_ORIGINS,
    }

@router.post("/init-roles")
async def init_roles(db: Session = Depends(get_db)):
    """
    ENDPOINT TEMPORAL - Inicializar roles básicos en producción
    ELIMINAR después de usar
    """
    try:
        roles_created = []
        
        # Crear rol admin si no existe
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if not admin_role:
            admin_role = Role(
                name="admin",
                description="Administrador del sistema con todos los permisos"
            )
            db.add(admin_role)
            roles_created.append("admin")
        
        # Crear rol alumno si no existe
        alumno_role = db.query(Role).filter(Role.name == "alumno").first()
        if not alumno_role:
            alumno_role = Role(
                name="alumno",
                description="Estudiante de la plataforma"
            )
            db.add(alumno_role)
            roles_created.append("alumno")
        
        db.commit()
        
        # Listar todos los roles existentes
        all_roles = db.query(Role).all()
        
        return {
            "success": True,
            "roles_created": roles_created,
            "all_roles": [{"id": role.id, "name": role.name, "description": role.description} for role in all_roles],
            "message": f"Roles inicializados. Creados: {', '.join(roles_created) if roles_created else 'ninguno (ya existían)'}"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/make-admin/{user_email}")
async def make_admin(user_email: str, db: Session = Depends(get_db)):
    """
    ENDPOINT TEMPORAL - Solo para hacer admin a tecno.juy.ar@gmail.com
    ELIMINAR después de usar
    """
    # Solo permitir para el email específico de seguridad
    if user_email != "tecno.juy.ar@gmail.com":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        # Buscar el usuario
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_email} not found")
        
        # Buscar el rol de administrador
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if not admin_role:
            raise HTTPException(status_code=404, detail="Admin role not found. Run /auth/init-roles first")
        
        # Actualizar el rol del usuario
        current_role = user.role.name if user.role else "No role"
        user.role_id = admin_role.id
        db.commit()
        
        return {
            "success": True,
            "message": f"User {user_email} is now admin",
            "previous_role": current_role,
            "new_role": "admin"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/session")
async def session(request: Request, current_user: User | None = Depends(get_current_user_optional), db: Session = Depends(get_db)):
    """Endpoint idempotente que devuelve 200 siempre.
    Sirve para que el frontend obtenga estado de sesión sin disparar 401 cuando el usuario es anónimo.
    Updated: force deploy.
    """
    print(f"[DEBUG] /auth/session called")
    print(f"[DEBUG] Cookies received: {dict(request.cookies)}")
    print(f"[DEBUG] current_user: {current_user}")
    
    if not current_user:
        return {"authenticated": False}
    # Cargar rol completo
    user_with_role = db.query(User).join(Role).filter(User.id == current_user.id).first()
    return {
        "authenticated": True,
        "user": {
            "id": user_with_role.id,
            "email": user_with_role.email,
            "name": user_with_role.name,
            "avatar_url": user_with_role.avatar_url,
            "has_premium_access": user_with_role.has_premium_access,
            "role_name": user_with_role.role.name if user_with_role.role else None
        }
    }

@router.get("/google/login")
async def google_login(request: Request):
    """Iniciar proceso de login con Google"""
    google = oauth.create_client('google')
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    
    # Forzar selección de cuenta y consentimiento
    return await google.authorize_redirect(
        request, 
        redirect_uri,
        prompt='select_account',  # Fuerza la selección de cuenta
        access_type='offline'     # Para obtener refresh token
    )

@router.get("/google/callback")
async def google_callback(
    request: Request, 
    response: Response,
    db: Session = Depends(get_db)
):
    """Callback de Google OAuth"""
    try:
        google = oauth.create_client('google')
        token = await google.authorize_access_token(request)
        
        # Obtener información del usuario
        user_info = await get_google_user_info(token['access_token'])
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not get user info from Google"
            )
        
        # Buscar o crear usuario
        user = db.query(User).filter(User.email == user_info['email']).first()
        
        if not user:
            # Crear nuevo usuario con rol de alumno por defecto
            alumno_role = db.query(Role).filter(Role.name == "alumno").first()
            if not alumno_role:
                # Crear rol alumno si no existe
                alumno_role = Role(name="alumno", description="Estudiante de la plataforma")
                db.add(alumno_role)
                db.commit()
                db.refresh(alumno_role)
            
            user = User(
                email=user_info['email'],
                google_id=user_info['id'],
                name=user_info['name'],
                avatar_url=user_info.get('picture'),
                role_id=alumno_role.id
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # Actualizar información del usuario existente
            user.name = user_info['name']
            user.avatar_url = user_info.get('picture')
            user.google_id = user_info['id']
            db.commit()
        
        # Recargar usuario con rol para los tokens
        user_with_role = db.query(User).join(Role).filter(User.id == user.id).first()
        
        # Crear tokens con información del rol
        token_data = {
            "sub": str(user_with_role.id),
            "email": user_with_role.email,
            "role": user_with_role.role.name if user_with_role.role else "alumno"
        }
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token({"sub": str(user.id)})
        
        # Dominio principal: primer origen configurado
        primary_frontend = FRONTEND_ORIGINS[0] if FRONTEND_ORIGINS else settings.FRONTEND_URL.rstrip('/')

        # En lugar de cookies, vamos a devolver los tokens para que el frontend los maneje
        redirect_url = f"{primary_frontend}/auth-success"
        redirect_response = RedirectResponse(url=redirect_url)
        
        # Devolver tokens como query parameters para que el frontend los capture
        # IMPORTANTE: Solo hacer esto en HTTPS, nunca en HTTP production
        token_params = f"?access_token={access_token}&refresh_token={refresh_token}"
        final_redirect = f"{primary_frontend}/auth-success{token_params}"
        
        return RedirectResponse(url=final_redirect)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Authentication failed: {str(e)}"
        )

@router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """Refrescar token de acceso"""
    refresh_token = request.cookies.get("refresh_token")
    
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token provided"
        )
    
    # Verificar refresh token
    payload = verify_token(refresh_token, "refresh")
    user_id = payload.get("sub")
    
    # Verificar que el usuario existe y cargar rol
    user = db.query(User).join(Role).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user"
        )
    
    # Crear nuevo access token con información del rol
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.name if user.role else "alumno"
    }
    new_access_token = create_access_token(token_data)
    
    # Configurar cookie
    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        secure=False,  # False para desarrollo local (HTTP)
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    
    return {"message": "Token refreshed successfully"}

@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener información del usuario actual"""
    # Cargar rol del usuario
    user_with_role = db.query(User).join(Role).filter(User.id == current_user.id).first()
    
    return UserInfo(
        id=user_with_role.id,
        email=user_with_role.email,
        name=user_with_role.name,
        avatar_url=user_with_role.avatar_url,
        has_premium_access=user_with_role.has_premium_access,
        role_name=user_with_role.role.name
    )

@router.post("/logout")
async def logout(response: Response):
    """Cerrar sesión"""
    from app.core.config import settings
    is_prod = settings.ENV == "production"
    cookie_secure = is_prod
    same_site = "none" if is_prod else "lax"
    # Eliminar cookies con todos los parámetros para asegurar que se borren
    response.delete_cookie(
        key="access_token",
        path="/",
        domain=None,
        secure=cookie_secure,
        httponly=True,
        samesite=same_site
    )
    response.delete_cookie(
        key="refresh_token",
        path="/",
        domain=None,
        secure=cookie_secure,
        httponly=True,
        samesite=same_site
    )
    return {"message": "Successfully logged out"}

