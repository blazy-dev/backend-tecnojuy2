#!/usr/bin/env python3
"""
Script para probar la configuración de Cloudflare R2
"""
import os
import sys
from app.core.config import settings
from app.storage.r2 import r2_service

def test_r2_configuration():
    """Probar la configuración de R2"""
    print("🔧 Probando configuración de Cloudflare R2...")
    print(f"📍 Endpoint URL: {settings.R2_ENDPOINT_URL}")
    print(f"🗃️ Bucket Name: {settings.R2_BUCKET_NAME}")
    print(f"🌐 Public URL: {settings.R2_PUBLIC_URL}")
    print()
    
    try:
        # Probar generación de URL firmada
        print("🔗 Generando URL firmada de prueba...")
        result = r2_service.generate_presigned_url(
            file_extension="jpg",
            content_type="image/jpeg",
            folder="test"
        )
        
        print("✅ URL firmada generada exitosamente!")
        print(f"📤 Upload URL: {result['upload_url'][:100]}...")
        print(f"🌐 Public URL: {result['public_url']}")
        print(f"🔑 Object Key: {result['object_key']}")
        print(f"📄 Filename: {result['filename']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error al probar R2: {str(e)}")
        print()
        print("🔧 Verifica que:")
        print("   - El Account ID sea correcto")
        print("   - El API Token tenga permisos suficientes")
        print("   - El bucket exista en Cloudflare")
        print("   - El endpoint URL esté bien formado")
        return False

if __name__ == '__main__':
    # Establecer la ruta para que pueda importar el módulo app
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    success = test_r2_configuration()
    sys.exit(0 if success else 1)

