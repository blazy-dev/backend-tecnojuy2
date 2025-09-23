#!/usr/bin/env python3
"""
Script para arrancar el servidor TecnoJuy
"""
import sys
import os

# Agregar el directorio actual al Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

print(f"📁 Directorio actual: {current_dir}")
print(f"🐍 Python path: {sys.path[:3]}...")

try:
    import uvicorn
    from app.main import app
    
    print("✅ Módulos importados correctamente")
    print("🚀 Arrancando servidor en http://localhost:8000")
    
    uvicorn.run(
        app,  # Pasamos la app directamente en lugar del string
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
except ImportError as e:
    print(f"❌ Error de importación: {e}")
    print("💡 Asegúrate de que las dependencias estén instaladas:")
    print("   pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    print("📋 Detalles del error:")
    traceback.print_exc()
    sys.exit(1)