from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import asyncio
import logging
import os
from urllib.parse import urlparse, urlunparse

from app.core.config import settings
from app.auth.routes import router as auth_router
from app.users.routes import router as users_router
from app.posts.routes import router as posts_router
from app.storage.routes import router as storage_router
from app.courses.routes import router as courses_router
from app.blog.routes import router as blog_router
from app.homepage.routes import router as homepage_router

app = FastAPI(
    title="TecnoJuy API",
    description="API para plataforma educativa con autenticación y blog",
    version="1.0.0"
)

# Session middleware (necesario para OAuth)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted hosts
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # En producción, especificar dominios exactos
)

# Routers
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(posts_router, prefix="/posts", tags=["posts"])
app.include_router(storage_router, prefix="/storage", tags=["storage"])
app.include_router(courses_router, prefix="/courses", tags=["courses"])
app.include_router(blog_router, prefix="/blog", tags=["blog"])
app.include_router(homepage_router, prefix="/homepage", tags=["homepage"])

# Static files
static_dir = "static"
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


def _mask_db_url(url: str) -> str:
    try:
        u = urlparse(url)
        netloc = u.netloc
        if "@" in netloc:
            creds, host = netloc.split("@", 1)
            user = creds.split(":", 1)[0] if ":" in creds else creds
            netloc = f"{user}:***@{host}"
        return urlunparse(u._replace(netloc=netloc))
    except Exception:
        return "unknown"


def _run_db_migrations() -> None:
    """Run Alembic migrations to head using Alembic API.
    This runs in a background thread so startup/healthcheck aren't blocked.
    """
    try:
        from alembic import command
        from alembic.config import Config
        # Resolve path to alembic.ini at project root (one level up from app/)
        project_root = os.path.dirname(os.path.dirname(__file__))
        alembic_ini = os.path.join(project_root, "alembic.ini")

        cfg = Config(alembic_ini)
        # Ensure the runtime DB URL is used (Railway env)
        if getattr(settings, "DATABASE_URL", None):
            cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

        logging.getLogger("uvicorn.error").info("[migrations] Running alembic upgrade head")
        command.upgrade(cfg, "head")
        logging.getLogger("uvicorn.error").info("[migrations] Alembic upgrade completed")
    except Exception as e:
        logging.getLogger("uvicorn.error").error(f"[migrations] Alembic upgrade failed: {e}")


@app.on_event("startup")
async def on_startup():
    # Log minimal info to verify DB URL source without leaking secrets
    masked = _mask_db_url(settings.DATABASE_URL or "")
    print(f"[startup] Using DATABASE_URL: {masked}")
    # Fire-and-forget DB migrations to keep startup fast
    asyncio.create_task(asyncio.to_thread(_run_db_migrations))

@app.get("/")
async def root():
    return {"message": "TecnoJuy API - Sistema educativo"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

