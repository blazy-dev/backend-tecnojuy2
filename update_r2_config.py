#!/usr/bin/env python3
"""
Script para actualizar la configuración de Cloudflare R2
"""
import os

# Configuración de Cloudflare R2
# IMPORTANTE: El usuario debe reemplazar estos valores con los suyos
R2_CONFIG = {
    'R2_ACCESS_KEY_ID': 'TU_ACCOUNT_ID_AQUI',  # Account ID de Cloudflare
    'R2_SECRET_ACCESS_KEY': '1234567893feefc5f0g5000bfc0c38d90bbeb',  # Tu API Token
    'R2_BUCKET_NAME': 'tecnojuy-uploads',  # Nombre de tu bucket
    'R2_ENDPOINT_URL': 'https://TU_ACCOUNT_ID_AQUI.r2.cloudflarestorage.com',  # Endpoint URL
    'R2_PUBLIC_URL': 'https://TU_DOMINIO_PUBLICO_AQUI',  # URL pública (opcional)
}

def update_env_file():
    """Actualizar archivo .env con configuración de R2"""
    env_path = '.env'
    
    # Leer contenido actual
    content = []
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            content = f.readlines()
    
    # Crear nuevo contenido
    new_content = []
    r2_keys = set(R2_CONFIG.keys())
    
    # Procesar líneas existentes
    for line in content:
        line = line.strip()
        if line and not line.startswith('#'):
            key = line.split('=')[0]
            if key in r2_keys:
                new_content.append(f'{key}={R2_CONFIG[key]}\n')
                r2_keys.remove(key)
            else:
                new_content.append(line + '\n')
        else:
            new_content.append(line + '\n')
    
    # Agregar keys que no existían
    if r2_keys:
        new_content.append('\n# Cloudflare R2 Configuration\n')
        for key in r2_keys:
            new_content.append(f'{key}={R2_CONFIG[key]}\n')
    
    # Escribir archivo actualizado
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(new_content)
    
    print("✅ Archivo .env actualizado con configuración de R2")
    print("\n🔧 IMPORTANTE: Actualiza estos valores en .env:")
    print("   - R2_ACCESS_KEY_ID: Tu Account ID de Cloudflare")
    print("   - R2_ENDPOINT_URL: https://TU_ACCOUNT_ID.r2.cloudflarestorage.com")
    print("   - R2_PUBLIC_URL: Tu dominio público (opcional)")

if __name__ == '__main__':
    update_env_file()

