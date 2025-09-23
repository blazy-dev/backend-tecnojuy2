import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:bejulu230903@localhost:5432/tecnojuy"
    
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
    
    # CORS
    FRONTEND_URL: str = "http://localhost:4321"
    
    class Config:
        env_file = ".env"

settings = Settings()
