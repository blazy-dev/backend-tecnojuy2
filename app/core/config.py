import os
from typing import Optional
from pydantic_settings import BaseSettings


def _resolve_database_url() -> str:
    """Resolve DATABASE_URL from common env var patterns used by Railway/PG.

    Priority:
    1) DATABASE_URL
    2) POSTGRES_URL
    3) Construct from PG* variables (PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE)
    Fallback to local dev URL as last resort.
    """
    url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
    if not url:
        host = os.getenv("PGHOST")
        user = os.getenv("PGUSER")
        password = os.getenv("PGPASSWORD")
        db = os.getenv("PGDATABASE")
        port = os.getenv("PGPORT", "5432")
        if all([host, user, password, db]):
            url = f"postgresql://{user}:{password}@{host}:{port}/{db}"
            sslmode = os.getenv("PGSSLMODE") or os.getenv("DB_SSLMODE")
            if sslmode:
                sep = "?" if "?" not in url else "&"
                url = f"{url}{sep}sslmode={sslmode}"
    # Final fallback (local dev)
    return url or "postgresql://postgres:postgres@localhost:5432/tecnojuy"

class Settings(BaseSettings):
    # Database
    # Value will be overridden below via _resolve_database_url() if env vars are present
    DATABASE_URL: str = _resolve_database_url()
    
    # JWT
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"
    
    # Cloudflare R2 - Bucket privado (cursos, documentos)
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = ""
    R2_ENDPOINT_URL: str = ""
    R2_PUBLIC_URL: str = ""
    
    # Cloudflare R2 - Bucket público (blog, assets)
    R2_PUBLIC_BUCKET_NAME: str = ""
    R2_PUBLIC_BUCKET_URL: str = ""
    
    # CORS / Frontend origins (puede ser uno o varios separados por coma)
    FRONTEND_URL: str = "http://localhost:4321"

    # Environment: development | staging | production
    ENV: str = "development"
    
    class Config:
        env_file = ".env"

settings = Settings()
"""Ensure DATABASE_URL picks up environment overrides even if pydantic settings loaded defaults first."""
settings.DATABASE_URL = _resolve_database_url() or settings.DATABASE_URL

def get_frontend_origins() -> list[str]:
    raw = settings.FRONTEND_URL or ""
    origins: list[str] = []
    for part in raw.split(','):
        p = part.strip()
        if not p:
            continue
        # Si el usuario pegó accidentalmente 'FRONTEND_URL=https://dominio' dentro del valor:
        if p.lower().startswith('frontend_url='):
            p = p.split('=', 1)[1].strip()
        p = p.rstrip('/')
        origins.append(p)
    # Añadir variante www si no está y el dominio es raíz (ej: https://tecnojuy.com)
    augmented: list[str] = []
    for o in origins:
        augmented.append(o)
        try:
            from urllib.parse import urlparse
            parsed = urlparse(o)
            host = parsed.hostname or ""
            if host.count('.') == 1 and not host.startswith('www.'):
                www_variant = o.replace('://', '://www.')
                if www_variant not in origins and www_variant not in augmented:
                    augmented.append(www_variant)
        except Exception:
            pass
    # Eliminar duplicados preservando orden
    seen = set()
    result = []
    for o in augmented:
        if o not in seen:
            seen.add(o)
            result.append(o)
    return result

FRONTEND_ORIGINS = get_frontend_origins()
