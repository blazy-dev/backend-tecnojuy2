from app.db.session import SessionLocal
from app.db.models import User, Role
from sqlalchemy.orm import joinedload
from app.core.security import create_access_token

# Conectar a la base de datos
db = SessionLocal()

try:
    print("🔍 DIAGNÓSTICO COMPLETO:")
    print("=" * 50)
    
    # 1. Verificar usuario en BD
    user = db.query(User).options(joinedload(User.role)).filter(User.email == 'tecno.juy.ar@gmail.com').first()
    
    if user:
        print(f"✅ Usuario encontrado:")
        print(f"   ID: {user.id}")
        print(f"   Nombre: {user.name}")
        print(f"   Email: {user.email}")
        print(f"   Rol ID: {user.role_id}")
        print(f"   Rol: {user.role.name if user.role else 'Sin rol'}")
        print(f"   Activo: {user.is_active}")
        print(f"   Premium: {user.has_premium_access}")
        
        # 2. Simular el endpoint /auth/me
        print(f"\n🔄 Simulando endpoint /auth/me:")
        user_with_role = db.query(User).join(Role).filter(User.id == user.id).first()
        if user_with_role:
            print(f"   ✅ Usuario con rol cargado correctamente")
            print(f"   📧 Email: {user_with_role.email}")
            print(f"   👑 Rol: {user_with_role.role.name}")
            
            # 3. Simular creación de token
            print(f"\n🔑 Simulando creación de token:")
            token_data = {
                "sub": str(user_with_role.id),
                "email": user_with_role.email,
                "role": user_with_role.role.name
            }
            print(f"   Datos del token: {token_data}")
            
            # 4. Simular respuesta UserInfo
            print(f"\n📋 Simulando respuesta UserInfo:")
            user_info = {
                "id": user_with_role.id,
                "email": user_with_role.email,
                "name": user_with_role.name,
                "avatar_url": user_with_role.avatar_url,
                "has_premium_access": user_with_role.has_premium_access,
                "role_name": user_with_role.role.name
            }
            print(f"   UserInfo: {user_info}")
        else:
            print("   ❌ Error: No se pudo cargar usuario con rol")
    else:
        print("❌ Usuario no encontrado")
        
    # 5. Verificar todos los roles
    print(f"\n📋 Todos los roles:")
    roles = db.query(Role).all()
    for role in roles:
        users_count = db.query(User).filter(User.role_id == role.id).count()
        print(f"   - {role.name} (ID: {role.id}) -> {users_count} usuarios")

finally:
    db.close()
