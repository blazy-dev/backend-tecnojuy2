#!/usr/bin/env python3
"""
Script para inicializar contenido predeterminado de la homepage
"""

import sys
import os
from sqlalchemy.orm import Session

# Agregar el directorio del proyecto al PATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import get_db
from app.db.models import HomepageContent, HomepageGallery

def init_homepage_content():
    """Inicializa contenido predeterminado para la homepage"""
    
    # Obtener la sesión de la base de datos
    db = next(get_db())
    
    try:
        # Verificar si ya existe contenido del hero
        existing_hero = db.query(HomepageContent).filter(HomepageContent.section == 'hero').first()
        
        if not existing_hero:
            # Crear contenido predeterminado para el hero
            hero_content = HomepageContent(
                section='hero',
                title='Aprende Tecnología del Futuro',
                subtitle='Con TecnoJuy',
                description='Descubre cursos diseñados por expertos para llevarte al siguiente nivel profesional.',
                button_text='Comenzar Ahora',
                button_url='/cursos',
                order_index=0,
                is_active=True
            )
            db.add(hero_content)
            print("✅ Contenido del hero creado")
        else:
            print("ℹ️ Contenido del hero ya existe")
        
        # Verificar si ya existe contenido features
        existing_features = db.query(HomepageContent).filter(HomepageContent.section == 'features').first()
        
        if not existing_features:
            # Crear contenido predeterminado para features
            features_content = HomepageContent(
                section='features',
                title='¿Por qué elegir TecnoJuy?',
                subtitle='La mejor educación tecnológica',
                description='Ofrecemos una experiencia de aprendizaje única con metodología práctica, proyectos reales y mentoría personalizada.',
                order_index=1,
                is_active=True
            )
            db.add(features_content)
            print("✅ Contenido de features creado")
        else:
            print("ℹ️ Contenido de features ya existe")
            
        # Verificar si ya existe contenido stats
        existing_stats = db.query(HomepageContent).filter(HomepageContent.section == 'stats').first()
        
        if not existing_stats:
            # Crear contenido predeterminado para stats
            stats_content = HomepageContent(
                section='stats',
                title='Resultados que hablan por sí solos',
                subtitle='Números que nos respaldan',
                description='Miles de estudiantes han transformado sus carreras con nuestros cursos especializados.',
                order_index=2,
                is_active=True
            )
            db.add(stats_content)
            print("✅ Contenido de stats creado")
        else:
            print("ℹ️ Contenido de stats ya existe")
        
        # Verificar si ya existe contenido about
        existing_about = db.query(HomepageContent).filter(HomepageContent.section == 'about').first()
        
        if not existing_about:
            # Crear contenido predeterminado para about
            about_content = HomepageContent(
                section='about',
                title='¿Por qué elegir TecnoJuy?',
                description='Ofrecemos una experiencia de aprendizaje única, diseñada para el mundo moderno. Nuestros cursos están actualizados con las últimas tecnologías y son impartidos por expertos de la industria.',
                order_index=1,
                is_active=True
            )
            db.add(about_content)
            print("✅ Contenido de about creado")
        else:
            print("ℹ️ Contenido de about ya existe")
            
        # Verificar si ya existe contenido CTA
        existing_cta = db.query(HomepageContent).filter(HomepageContent.section == 'cta').first()
        
        if not existing_cta:
            # Crear contenido predeterminado para CTA
            cta_content = HomepageContent(
                section='cta',
                title='¿Listo para transformar tu carrera?',
                description='Únete a miles de estudiantes que ya están construyendo su futuro en tecnología.',
                button_text='Comenzar Ahora',
                button_url='/login',
                order_index=2,
                is_active=True
            )
            db.add(cta_content)
            print("✅ Contenido de CTA creado")
        else:
            print("ℹ️ Contenido de CTA ya existe")
        
        # Confirmar los cambios
        db.commit()
        print("🎉 Inicialización de contenido completada!")
        
    except Exception as e:
        print(f"❌ Error al inicializar contenido: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Iniciando inicialización de contenido de homepage...")
    init_homepage_content()