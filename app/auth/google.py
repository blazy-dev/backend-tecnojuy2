import httpx
from typing import Dict, Optional
from authlib.integrations.starlette_client import OAuth

from app.core.config import settings

oauth = OAuth()

oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

async def get_google_user_info(access_token: str) -> Optional[Dict]:
    """Obtener información del usuario desde Google"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if response.status_code == 200:
                return response.json()
            return None
    except Exception:
        return None

async def verify_google_token(token: str) -> Optional[Dict]:
    """Verificar token de Google y obtener información del usuario"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://oauth2.googleapis.com/tokeninfo?access_token={token}"
            )
            if response.status_code == 200:
                token_info = response.json()
                # Verificar que el token pertenezca a nuestra aplicación
                if token_info.get('aud') == settings.GOOGLE_CLIENT_ID:
                    # Obtener información del usuario
                    user_info = await get_google_user_info(token)
                    return user_info
            return None
    except Exception:
        return None

