#!/usr/bin/env python3
"""
Script para crear las tablas del sistema premium manualmente
"""
import os
import sys
from sqlalchemy import create_engine, text

# Configurar la ruta para que pueda importar el módulo app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.db.models import Base

def create_premium_tables():
    """Crear las tablas del sistema premium"""
    print("🔧 Creando tablas del sistema premium...")
    
    try:
        # Crear engine
        engine = create_engine(settings.DATABASE_URL)
        
        # SQL para agregar la columna has_premium_access a users
        alter_users_sql = """
        ALTER TABLE users ADD COLUMN IF NOT EXISTS has_premium_access BOOLEAN DEFAULT FALSE;
        """
        
        # SQL para crear tabla courses
        create_courses_sql = """
        CREATE TABLE IF NOT EXISTS courses (
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
        
        # SQL para crear tabla lessons
        create_lessons_sql = """
        CREATE TABLE IF NOT EXISTS lessons (
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
        
        # SQL para crear tabla course_enrollments
        create_enrollments_sql = """
        CREATE TABLE IF NOT EXISTS course_enrollments (
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
        
        # Ejecutar SQL
        with engine.connect() as conn:
            print("📊 Modificando tabla users...")
            conn.execute(text(alter_users_sql))
            
            print("🎓 Creando tabla courses...")
            conn.execute(text(create_courses_sql))
            
            print("📝 Creando tabla lessons...")
            conn.execute(text(create_lessons_sql))
            
            print("👥 Creando tabla course_enrollments...")
            conn.execute(text(create_enrollments_sql))
            
            # Commit changes
            conn.commit()
        
        print("✅ Tablas del sistema premium creadas exitosamente!")
        return True
        
    except Exception as e:
        print(f"❌ Error creando tablas: {str(e)}")
        return False

if __name__ == '__main__':
    success = create_premium_tables()
    sys.exit(0 if success else 1)

