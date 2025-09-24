#!/usr/bin/env python3
"""
Script para hacer a un usuario administrador
"""
import sys
import os

# Añadir el directorio del proyecto al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.db.models import User, Role

def make_user_admin(email: str):
    """Hace a un usuario administrador"""
    db = SessionLocal()
    try:
        # Buscar el usuario
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"❌ Usuario con email {email} no encontrado")
            return False
        
        print(f"✅ Usuario encontrado: {user.name} ({user.email})")
        print(f"   Rol actual: {user.role.name if user.role else 'Sin rol'}")
        
        # Buscar el rol de administrador
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if not admin_role:
            print("❌ Rol 'admin' no encontrado en la base de datos")
            return False
        
        # Actualizar el rol del usuario
        user.role_id = admin_role.id
        db.commit()
        
        print(f"✅ Usuario {user.email} ahora es administrador")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    email = "tecno.juy.ar@gmail.com"
    print(f"🔧 Haciendo administrador a: {email}")
    
    if make_user_admin(email):
        print("✅ Operación completada exitosamente")
    else:
        print("❌ La operación falló")