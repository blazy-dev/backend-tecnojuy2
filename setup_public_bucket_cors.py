#!/usr/bin/env python3
"""
Script para configurar CORS en el bucket PÚBLICO de Cloudflare R2
"""
import boto3
from app.core.config import settings

def setup_public_cors():
    """Configurar CORS para el bucket público R2"""
    print("🔧 Configurando CORS para bucket PÚBLICO de R2...")
    
    # Crear cliente S3 compatible para R2
    s3_client = boto3.client(
        's3',
        endpoint_url=settings.R2_ENDPOINT_URL,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name='auto'
    )
    
    # Configuración CORS más permisiva para el bucket público
    cors_configuration = {
        'CORSRules': [
            {
                'AllowedOrigins': [
                    'http://localhost:4321',
                    'http://localhost:3000',
                    'https://*.pages.dev',
                    'https://tecnojuy.com',
                    'https://www.tecnojuy.com'
                ],
                'AllowedMethods': ['GET', 'PUT', 'POST', 'DELETE', 'HEAD'],
                'AllowedHeaders': ['*'],
                'ExposeHeaders': ['ETag', 'Content-Length'],
                'MaxAgeSeconds': 3600
            }
        ]
    }
    
    try:
        # Aplicar configuración CORS al bucket PÚBLICO
        bucket_name = settings.R2_PUBLIC_BUCKET_NAME
        print(f"📦 Configurando CORS para bucket: {bucket_name}")
        
        s3_client.put_bucket_cors(
            Bucket=bucket_name,
            CORSConfiguration=cors_configuration
        )
        
        print("✅ CORS configurado exitosamente en bucket PÚBLICO!")
        print("📋 Configuración aplicada:")
        print(f"   - Bucket: {bucket_name}")
        print(f"   - Orígenes permitidos: localhost:4321, localhost:3000, *.pages.dev, tecnojuy.com")
        print(f"   - Métodos permitidos: GET, PUT, POST, DELETE, HEAD")
        print(f"   - Headers permitidos: *")
        print(f"   - Headers expuestos: ETag, Content-Length")
        
        # Verificar configuración
        response = s3_client.get_bucket_cors(Bucket=bucket_name)
        print("\n🔍 Configuración CORS actual:")
        for rule in response['CORSRules']:
            print(f"   - Orígenes: {rule['AllowedOrigins']}")
            print(f"   - Métodos: {rule['AllowedMethods']}")
            print(f"   - Headers: {rule['AllowedHeaders']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error configurando CORS: {str(e)}")
        print(f"\n💡 Configuración manual necesaria:")
        print(f"   1. Ve a Cloudflare Dashboard > R2")
        print(f"   2. Selecciona el bucket: {settings.R2_PUBLIC_BUCKET_NAME}")
        print(f"   3. Ve a Settings > CORS policy")
        print(f"   4. Pega esta configuración:")
        print("""
[
  {
    "AllowedOrigins": [
      "https://tecnojuy.com",
      "https://www.tecnojuy.com",
      "http://localhost:4321",
      "https://*.pages.dev"
    ],
    "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
    "AllowedHeaders": ["*"],
    "ExposeHeaders": ["ETag", "Content-Length"],
    "MaxAgeSeconds": 3600
  }
]
        """)
        return False

if __name__ == '__main__':
    setup_public_cors()
