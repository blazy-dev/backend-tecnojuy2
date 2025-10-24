import boto3
from botocore.exceptions import ClientError
from typing import Optional
import uuid
from datetime import datetime
import logging

from app.core.config import settings

# Configurar logger
logger = logging.getLogger(__name__)


class R2Service:
    def __init__(self):
        # Leer config desde variables de entorno
        endpoint_url = (settings.R2_ENDPOINT_URL or "").strip()
        access_key = (settings.R2_ACCESS_KEY_ID or "").strip()
        secret_key = (settings.R2_SECRET_ACCESS_KEY or "").strip()

        # Buckets/URLs (pueden estar vacíos en entornos sin R2)
        self.bucket_name = (settings.R2_BUCKET_NAME or "").strip()
        self.public_url = (settings.R2_PUBLIC_URL or "").strip()
        self.public_bucket_name = (settings.R2_PUBLIC_BUCKET_NAME or "").strip()
        self.public_bucket_url = (settings.R2_PUBLIC_BUCKET_URL or "").strip()

        # Solo crea el cliente si hay endpoint y credenciales; si no, deja deshabilitado
        if endpoint_url and access_key and secret_key:
            try:
                self.client = boto3.client(
                    's3',
                    endpoint_url=endpoint_url,
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    region_name='auto'
                )
                self.enabled = True
                logger.info("R2 client initialized for endpoint %s", endpoint_url)
            except Exception:
                # No bloquea el arranque si falla aquí
                self.client = None
                self.enabled = False
                logger.exception("Failed to initialize R2 client; R2 features disabled")
        else:
            self.client = None
            self.enabled = False
            logger.warning("R2 not configured (missing endpoint and/or credentials); storage features disabled")

    def _require_client(self) -> None:
        if not self.client:
            raise Exception("R2 is not configured. Set R2_ENDPOINT_URL, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, and bucket variables.")
    
    def generate_presigned_url(
        self,
        file_extension: str,
        content_type: str,
        expiration: int = 3600,
        folder: str = "uploads"
    ) -> dict:
        """Generar URL firmada para subida directa a R2"""
        try:
            self._require_client()
            # Generar nombre único para el archivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"{timestamp}_{unique_id}.{file_extension}"
            object_key = f"{folder}/{filename}"
            
            # Generar URL firmada
            url = self.client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_key,
                    'ContentType': content_type
                },
                ExpiresIn=expiration
            )
            
            # URL pública del archivo después de la subida
            public_url = f"{self.public_url}/{object_key}"
            
            return {
                "upload_url": url,
                "public_url": public_url,
                "object_key": object_key,
                "filename": filename
            }
            
        except ClientError as e:
            raise Exception(f"Error generating presigned URL: {str(e)}")
    
    def delete_object(self, object_key: str) -> bool:
        """Eliminar objeto de R2"""
        try:
            self._require_client()
            self.client.delete_object(Bucket=self.bucket_name, Key=object_key)
            return True
        except ClientError:
            return False
    
    def get_object_url(self, object_key: str) -> str:
        """Obtener URL pública del objeto"""
        return f"{self.public_url}/{object_key}"
    
    def check_object_exists(self, object_key: str) -> bool:
        """Verificar si un objeto existe en R2"""
        try:
            self._require_client()
            self.client.head_object(Bucket=self.bucket_name, Key=object_key)
            return True
        except ClientError:
            return False

    def generate_presigned_get_url(self, object_key: str, expiration: int = 3600) -> str:
        """Generar URL firmada para descargar un objeto"""
        try:
            self._require_client()
            return self.client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_key,
                },
                ExpiresIn=expiration
            )
        except ClientError as e:
            raise Exception(f"Error generating presigned GET URL: {str(e)}")

    def generate_public_presigned_put_url(self, object_key: str, content_type: str, expiration: int = 3600) -> str:
        """Generar URL firmada para subir un archivo directamente al bucket PÚBLICO"""
        try:
            self._require_client()
            return self.client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.public_bucket_name,
                    'Key': object_key,
                    'ContentType': content_type
                },
                ExpiresIn=expiration
            )
        except ClientError as e:
            raise Exception(f"Error generating presigned PUT URL for public bucket: {str(e)}")

    def get_public_object_url(self, object_key: str) -> str:
        """Obtener URL pública del objeto en el bucket público"""
        if self.public_bucket_url:
            return f"{self.public_bucket_url.rstrip('/')}/{object_key}"
        else:
            # Fallback si no hay URL personalizada configurada
            return f"https://{self.public_bucket_name}.r2.dev/{object_key}"

    async def upload_file_to_public_bucket(self, object_key: str, content: bytes, content_type: str) -> tuple[bool, str | None]:
        """
        Subir archivo directamente al bucket público para contenido del blog
        """
        import asyncio
        try:
            self._require_client()
            logger.info("Uploading object to public R2 bucket")
            logger.debug(
                "bucket=%s key=%s content_type=%s size_bytes=%s",
                self.public_bucket_name,
                object_key,
                content_type,
                len(content),
            )

            def _put_object() -> None:
                self.client.put_object(
                    Bucket=self.public_bucket_name,
                    Key=object_key,
                    Body=content,
                    ContentType=content_type,
                )

            try:
                await asyncio.to_thread(_put_object)
            except ClientError as ce:
                err = ce.response.get("Error", {}) if hasattr(ce, "response") else {}
                code = err.get("Code")
                msg = err.get("Message")
                logger.error(
                    "R2 ClientError on put_object to public bucket: code=%s message=%s key=%s",
                    code,
                    msg,
                    object_key,
                )
                return False, f"ClientError {code}: {msg}"

            logger.info("R2 public upload OK: %s", object_key)
            
            # Construir URL pública del archivo
            if self.public_bucket_url:
                public_url = f"{self.public_bucket_url.rstrip('/')}/{object_key}"
            else:
                # Fallback si no hay URL personalizada configurada
                public_url = f"https://{self.public_bucket_name}.r2.dev/{object_key}"
            
            return True, public_url

        except Exception as e:
            logger.exception("Unexpected error uploading to public R2 bucket for key=%s", object_key)
            return False, str(e)

    async def upload_file_direct(self, object_key: str, content: bytes, content_type: str) -> tuple[bool, str | None]:
        """
        Subir archivo directamente desde el backend a R2 (asíncrono, no bloqueante),
        reutilizando el cliente boto3 ya configurado. Devuelve (success, error_message).
        """
        import asyncio
        try:
            self._require_client()
            logger.info("Uploading object to R2")
            logger.debug(
                "bucket=%s key=%s content_type=%s size_bytes=%s",
                self.bucket_name,
                object_key,
                content_type,
                len(content),
            )

            def _put_object() -> None:
                self.client.put_object(
                    Bucket=self.bucket_name,
                    Key=object_key,
                    Body=content,
                    ContentType=content_type,
                )

            try:
                await asyncio.to_thread(_put_object)
            except ClientError as ce:  # type: ignore[name-defined]
                err = ce.response.get("Error", {}) if hasattr(ce, "response") else {}
                code = err.get("Code")
                msg = err.get("Message")
                logger.error(
                    "R2 ClientError on put_object: code=%s message=%s key=%s",
                    code,
                    msg,
                    object_key,
                )
                return False, f"ClientError {code}: {msg}"

            logger.info("R2 upload OK: %s", object_key)
            return True, None

        except Exception as e:
            logger.exception("Unexpected error uploading to R2 for key=%s", object_key)
            return False, str(e)

# Instancia global del servicio (no falla si no está configurado)
r2_service = R2Service()


