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

        is_prod = settings.ENV == "production"
        cookie_secure = is_prod  # solo secure con HTTPS
        same_site = "none" if is_prod else "lax"  # none para permitir third-party / subdominios

        # Configurar cookies seguras
        response = RedirectResponse(url=f"{primary_frontend}/dashboard")
        # Nota: path="/" explícito para claridad
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=cookie_secure,
            samesite=same_site,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=cookie_secure,
            samesite=same_site,
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        )
        
        return response
        
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

