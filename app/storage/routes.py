from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Form, Query
from pydantic import BaseModel
from typing import Optional

from app.auth.dependencies import get_current_user
from app.core.config import settings
from app.db.models import User
from app.storage.r2 import r2_service

router = APIRouter()

class UploadUrlRequest(BaseModel):
    filename: str
    content_type: str
    folder: Optional[str] = "uploads"

class UploadUrlResponse(BaseModel):
    upload_url: str
    public_url: str
    object_key: str
    filename: str

class DownloadUrlResponse(BaseModel):
    download_url: str

@router.post("/upload-url", response_model=UploadUrlResponse)
async def get_upload_url(
    request: UploadUrlRequest,
    current_user: User = Depends(get_current_user)
):
    """Generar URL firmada para subida de archivos a R2"""
    try:
        # Extraer extensión del archivo
        file_extension = request.filename.split('.')[-1].lower()
        
        # Validar tipos de archivo permitidos
        allowed_extensions = {
            'jpg', 'jpeg', 'png', 'gif', 'webp',  # Imágenes
            'pdf', 'doc', 'docx',                  # Documentos
            'mp4', 'mov', 'avi'                    # Videos (si los necesitas)
        }
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de archivo no permitido: .{file_extension}"
            )
        
        # Generar URL firmada
        result = r2_service.generate_presigned_url(
            file_extension=file_extension,
            content_type=request.content_type,
            folder=request.folder
        )
        
        return UploadUrlResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generando URL de subida: {str(e)}"
        )

@router.delete("/file/{object_key:path}")
async def delete_file(
    object_key: str,
    current_user: User = Depends(get_current_user)
):
    """Eliminar archivo de R2"""
    try:
        success = r2_service.delete_object(object_key)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Archivo no encontrado"
            )
        
        return {"message": "Archivo eliminado exitosamente"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error eliminando archivo: {str(e)}"
        )

@router.get("/file-info/{object_key:path}")
async def get_file_info(
    object_key: str,
    current_user: User = Depends(get_current_user)
):
    """Obtener información de un archivo en R2"""
    try:
        exists = r2_service.check_object_exists(object_key)
        
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Archivo no encontrado"
            )
        
        public_url = r2_service.get_object_url(object_key)
        
        return {
            "object_key": object_key,
            "public_url": public_url,
            "exists": True
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo información del archivo: {str(e)}"
        )

@router.get("/download-url", response_model=DownloadUrlResponse)
async def get_download_url(
    object_key: str = Query(..., description="Key del objeto en R2"),
    current_user: User = Depends(get_current_user)
):
    """Generar URL firmada temporal para descargar un archivo (bucket privado)."""
    try:
        # Normalizar: si recibimos una URL completa, extraer el path
        key = object_key
        if key.startswith("http://") or key.startswith("https://"):
            from urllib.parse import urlparse
            parsed = urlparse(key)
            key = parsed.path.lstrip('/')
        # Si incluye el nombre del bucket como prefijo, quitarlo
        bucket_prefix = f"{settings.R2_BUCKET_NAME}/"
        if key.startswith(bucket_prefix):
            key = key[len(bucket_prefix):]

        # Generar URL firmada directamente; si el objeto no existe, el GET firmando fallará
        url = r2_service.generate_presigned_get_url(key)
        return {"download_url": url}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generando URL de descarga: {str(e)}"
        )

@router.post("/proxy-upload")
async def proxy_upload(
    file: UploadFile = File(...),
    folder: str = Form("uploads"),
    current_user: User = Depends(get_current_user)
):
    """
    Proxy upload: El frontend envía el archivo al backend,
    el backend lo sube a R2 y devuelve la URL pública
    """
    try:
        # Generar nombre único para el archivo
        from datetime import datetime
        import uuid
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        file_extension = file.filename.split('.')[-1] if '.' in file.filename else ''
        object_key = f"{folder}/{timestamp}_{unique_id}.{file_extension}"
        
        # Leer contenido del archivo
        content = await file.read()
        
        # Subir directamente a R2 usando el servicio
        success, error_message = await r2_service.upload_file_direct(
            object_key=object_key,
            content=content,
            content_type=file.content_type
        )
        
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to upload file to R2: {error_message}")
        
        # Generar URL firmada (presigned) con larga duración para portadas
        presigned_url = r2_service.generate_presigned_get_url(object_key, expiration=86400*7)  # 7 días
        
        return {
            "public_url": presigned_url,
            "object_key": object_key,
            "filename": f"{timestamp}_{unique_id}.{file_extension}",
            "content_type": file.content_type,
            "size": len(content)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")