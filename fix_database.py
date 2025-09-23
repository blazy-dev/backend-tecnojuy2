#!/usr/bin/env python3
"""
Script para verificar y corregir la estructura de la base de datos
"""
import os
import sys
from sqlalchemy import create_engine, text, inspect

# Configurar la ruta para que pueda importar el módulo app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def fix_database():
    """Verificar y corregir la estructura de la base de datos"""
    print("🔧 Verificando estructura de la base de datos...")
    
    try:
        # Crear engine
        engine = create_engine(settings.DATABASE_URL)
        inspector = inspect(engine)
        
        # Verificar si la tabla users existe
        if 'users' not in inspector.get_table_names():
            print("❌ Tabla users no existe!")
            return False
        
        # Verificar columnas de la tabla users
        columns = inspector.get_columns('users')
        column_names = [col['name'] for col in columns]
        
        print(f"📊 Columnas existentes en users: {column_names}")
        
        # Verificar si has_premium_access existe
        if 'has_premium_access' not in column_names:
            print("🔧 Agregando columna has_premium_access...")
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN has_premium_access BOOLEAN DEFAULT FALSE;"))
                conn.commit()
            print("✅ Columna has_premium_access agregada!")
        else:
            print("✅ Columna has_premium_access ya existe!")
        
        # Verificar otras tablas
        tables_to_check = ['courses', 'lessons', 'course_enrollments']
        
        for table in tables_to_check:
            if table not in inspector.get_table_names():
                print(f"🔧 Creando tabla {table}...")
                
                if table == 'courses':
                    sql = """
                    CREATE TABLE courses (
                        id SERIAL PRIMARY KEY,
                        title VARCHAR(255) NOT NULL,
                        description TEXT,
                        cover_image_url VARCHAR(500),
                        is_published BOOLEAN DEFAULT FALSE,
                        is_premium BOOLEAN DEFAULT TRUE,
                        price VARCHAR(50),
                        instructor_id INTEGER NOT NULL REFERENCES users(id),
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE
                    );
                    """
                elif table == 'lessons':
                    sql = """
                    CREATE TABLE lessons (
                        id SERIAL PRIMARY KEY,
                        title VARCHAR(255) NOT NULL,
                        description TEXT,
                        video_url VARCHAR(500),
                        video_object_key VARCHAR(500),
                        duration_minutes INTEGER,
                        order_index INTEGER NOT NULL,
                        is_published BOOLEAN DEFAULT FALSE,
                        is_free BOOLEAN DEFAULT FALSE,
                        course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE
                    );
                    """
                elif table == 'course_enrollments':
                    sql = """
                    CREATE TABLE course_enrollments (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id),
                        course_id INTEGER NOT NULL REFERENCES courses(id),
                        has_access BOOLEAN DEFAULT FALSE,
                        enrollment_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        access_granted_date TIMESTAMP WITH TIME ZONE,
                        access_granted_by INTEGER REFERENCES users(id),
                        UNIQUE(user_id, course_id)
                    );
                    """
                
                with engine.connect() as conn:
                    conn.execute(text(sql))
                    conn.commit()
                print(f"✅ Tabla {table} creada!")
            else:
                print(f"✅ Tabla {table} ya existe!")
        
        print("🎉 Base de datos verificada y corregida exitosamente!")
        return True
        
    except Exception as e:
        print(f"❌ Error verificando base de datos: {str(e)}")
        return False

if __name__ == '__main__':
    success = fix_database()
    sys.exit(0 if success else 1)

