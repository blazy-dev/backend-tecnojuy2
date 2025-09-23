#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para inicializar el proyecto TecnoJuy
"""

import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configurar encoding para Windows
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Añadir el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.models import Base, Role, User
from app.core.config import settings

def create_database():
    """Crear las tablas de la base de datos"""
    try:
        engine = create_engine(settings.DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        print("✅ Tablas de base de datos creadas exitosamente")
        return engine
    except Exception as e:
        print(f"❌ Error creando tablas: {e}")
        return None

def create_initial_data(engine):
    """Crear datos iniciales"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Crear roles si no existen
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if not admin_role:
            admin_role = Role(
                name="admin",
                description="Administrador del sistema con todos los permisos"
            )
            db.add(admin_role)
            print("✅ Rol 'admin' creado")
        
        alumno_role = db.query(Role).filter(Role.name == "alumno").first()
        if not alumno_role:
            alumno_role = Role(
                name="alumno",
                description="Estudiante de la plataforma"
            )
            db.add(alumno_role)
            print("✅ Rol 'alumno' creado")
        
        db.commit()
        print("✅ Datos iniciales creados exitosamente")
        
    except Exception as e:
        print(f"❌ Error creando datos iniciales: {e}")
        db.rollback()
    finally:
        db.close()

def main():
    """Función principal"""
    print("🚀 Inicializando proyecto TecnoJuy...")
    print("=" * 50)
    
    # Verificar variables de entorno
    print("📋 Verificando configuración...")
    
    required_env_vars = [
        "DATABASE_URL",
        "SECRET_KEY",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET"
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not getattr(settings, var, None):
            missing_vars.append(var)
    
    if missing_vars:
        print("⚠️  Variables de entorno faltantes:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 Asegúrate de configurar estas variables antes de continuar.")
        print("   Puedes copiar el archivo env.example a .env y completar los valores.")
        return False
    
    # Crear base de datos
    print("\n🗃️  Configurando base de datos...")
    engine = create_database()
    if not engine:
        return False
    
    # Crear datos iniciales
    print("\n📊 Creando datos iniciales...")
    create_initial_data(engine)
    
    print("\n" + "=" * 50)
    print("🎉 ¡Proyecto inicializado exitosamente!")
    print("\n📚 Próximos pasos:")
    print("1. Configura tu Google OAuth en la Google Cloud Console")
    print("2. Configura tu bucket de Cloudflare R2")
    print("3. Ejecuta: uvicorn app.main:app --reload")
    print("4. Visita: http://localhost:8000/docs para ver la API")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
