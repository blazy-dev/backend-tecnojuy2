from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import Role, User

def init_db():
    """Inicializar base de datos con datos básicos"""
    db: Session = SessionLocal()
    
    try:
        # Crear roles básicos si no existen
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
        print("✅ Base de datos inicializada correctamente")
        
    except Exception as e:
        print(f"❌ Error inicializando base de datos: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_db()


