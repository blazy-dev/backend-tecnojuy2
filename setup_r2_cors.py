#!/usr/bin/env python3
"""
Script para configurar CORS en Cloudflare R2
"""
import boto3
from app.core.config import settings

def setup_cors():
    """Configurar CORS para el bucket R2"""
    print("🔧 Configurando CORS para Cloudflare R2...")
    
    # Crear cliente S3 compatible para R2
    s3_client = boto3.client(
        's3',
        endpoint_url=settings.R2_ENDPOINT_URL,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name='auto'
    )
    
    # Configuración CORS
    cors_configuration = {
        'CORSRules': [
            {
                'AllowedOrigins': [
                    'http://localhost:4321',
                    'http://localhost:3000',
                    'https://*.pages.dev',
                    'https://*.cloudflare.net'
                ],
                'AllowedMethods': ['GET', 'PUT', 'POST', 'DELETE', 'HEAD'],
                'AllowedHeaders': ['*'],
                'ExposeHeaders': ['ETag'],
                'MaxAgeSeconds': 3600
            }
        ]
    }
    
    try:
        # Aplicar configuración CORS
        s3_client.put_bucket_cors(
            Bucket=settings.R2_BUCKET_NAME,
            CORSConfiguration=cors_configuration
        )
        
        print("✅ CORS configurado exitosamente!")
        print("📋 Configuración aplicada:")
        print(f"   - Orígenes permitidos: localhost:4321, localhost:3000, *.pages.dev")
        print(f"   - Métodos permitidos: GET, PUT, POST, DELETE, HEAD")
        print(f"   - Headers permitidos: *")
        
        # Verificar configuración
        response = s3_client.get_bucket_cors(Bucket=settings.R2_BUCKET_NAME)
        print("\n🔍 Configuración CORS actual:")
        for rule in response['CORSRules']:
            print(f"   - Orígenes: {rule['AllowedOrigins']}")
            print(f"   - Métodos: {rule['AllowedMethods']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error configurando CORS: {str(e)}")
        print("\n💡 Alternativamente, puedes configurar CORS manualmente en:")
        print("   Cloudflare Dashboard > R2 > tu-bucket > Settings > CORS policy")
        return False

if __name__ == '__main__':
    setup_cors()
