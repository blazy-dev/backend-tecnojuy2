#!/usr/bin/env python3
"""
Script para probar el endpoint de storage
"""
import requests
import json

def test_storage_endpoint():
    """Probar el endpoint de storage"""
    print("🔧 Probando endpoint de storage...")
    
    url = "http://localhost:8000/storage/upload-url"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "filename": "test.jpg",
        "content_type": "image/jpeg",
        "folder": "courses"
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        print(f"📡 Status: {response.status_code}")
        print(f"📄 Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Endpoint funcionando correctamente")
            return True
        else:
            print("❌ Error en el endpoint")
            return False
            
    except Exception as e:
        print(f"❌ Error conectando: {str(e)}")
        return False

if __name__ == '__main__':
    test_storage_endpoint()
