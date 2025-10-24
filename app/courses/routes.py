from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.db.session import get_db
from app.db.models import User, Course, Chapter, Lesson, CourseEnrollment, LessonProgress
from app.auth.dependencies import get_current_user, require_admin, get_current_user_optional
from app.courses.service import course_service
from app.courses.schemas import (
    CourseCreate, CourseUpdate, CourseResponse, CourseListResponse,
    ChapterCreate, ChapterUpdate, ChapterResponse, ChapterReorderRequest,
    LessonCreate, LessonUpdate, LessonResponse, LessonReorderRequest,
    LessonProgressUpdate, LessonProgressResponse,
    VideoUrlResponse, FileUploadResponse
)
from app.storage.r2 import r2_service
from sqlalchemy import and_, func

router = APIRouter()

# Función auxiliar para generar URLs seguras de portadas
def get_safe_cover_url(cover_url: str | None) -> str | None:
    """Genera URL segura para la portada del curso con expiración de 1 hora"""
    if not cover_url:
        return None
    
    # Si es una URL de R2, generar URL firmada temporal
    if cover_url.startswith("https://") and "r2.dev" in cover_url:
        try:
            from urllib.parse import urlparse
            from app.core.config import settings
            
            parsed_url = urlparse(cover_url)
            object_key = parsed_url.path.lstrip('/')
            
            # Remover el nombre del bucket si está presente
            bucket_prefix = f"{settings.R2_BUCKET_NAME}/"
            if object_key.startswith(bucket_prefix):
                object_key = object_key[len(bucket_prefix):]
            
            # Generar URL firmada con 1 hora de duración (3600 segundos)
            # Se regenera automáticamente cada vez que el usuario carga la lista de cursos
            return r2_service.generate_presigned_get_url(object_key, expiration=3600)
        except Exception as e:
            print(f"Error generando URL firmada para cover: {e}")
            return cover_url
    
    return cover_url

# Esquemas específicos para esta ruta
class AccessGrantRequest(BaseModel):
    user_id: int
    course_id: int

# Rutas públicas (para alumnos)
@router.get("/", response_model=List[CourseListResponse])
async def get_available_courses(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Obtener cursos disponibles públicamente con progreso si está autenticado"""
    # Obtener todos los cursos publicados
    courses = db.query(Course).filter(Course.is_published == True).all()
    
    response = []
    for course in courses:
        has_access = False
        progress_percentage = 0
        
        # Si el usuario está autenticado, verificar acceso y progreso
        if current_user:
            # Verificar si tiene acceso al curso
            if not course.is_premium:
                has_access = True
            else:
                enrollment = db.query(CourseEnrollment).filter(
                    and_(
                        CourseEnrollment.user_id == current_user.id,
                        CourseEnrollment.course_id == course.id,
                        CourseEnrollment.has_access == True
                    )
                ).first()
                has_access = enrollment is not None
            
            # Si tiene acceso, calcular progreso
            if has_access:
                # Contar lecciones totales del curso
                total_lessons = db.query(Lesson).filter(
                    Lesson.course_id == course.id,
                    Lesson.is_published == True
                ).count()
                
                if total_lessons > 0:
                    # Contar lecciones completadas por el usuario
                    completed_lessons = db.query(LessonProgress).join(Lesson).filter(
                        and_(
                            LessonProgress.user_id == current_user.id,
                            LessonProgress.is_completed == True,
                            Lesson.course_id == course.id,
                            Lesson.is_published == True
                        )
                    ).count()
                    
                    progress_percentage = round((completed_lessons / total_lessons) * 100)
        
        # Cargar instructor
        instructor = db.query(User).filter(User.id == course.instructor_id).first()
        
        # Contar lecciones
        lesson_count = db.query(Lesson).filter(
            Lesson.course_id == course.id,
            Lesson.is_published == True
        ).count()
        
        response.append(CourseListResponse(
            id=course.id,
            title=course.title,
            short_description=course.short_description,
            cover_image_url=get_safe_cover_url(course.cover_image_url),
            level=course.level or "Beginner",
            language=course.language or "Español",
            category=course.category,
            price=course.price,
            is_premium=course.is_premium,
            instructor_name=instructor.name if instructor else "Desconocido",
            lesson_count=lesson_count,
            estimated_duration_hours=course.estimated_duration_hours,
            has_access=has_access,
            progress_percentage=progress_percentage,
            created_at=course.created_at
        ))
    
    return response

@router.get("/debug-courses")
async def debug_courses(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Endpoint de debug para verificar progreso"""
    return {
        "user_authenticated": current_user is not None,
        "user_id": current_user.id if current_user else None,
        "user_name": current_user.name if current_user else None,
        "message": "Debug endpoint funcionando correctamente"
    }

@router.get("/my-courses", response_model=List[CourseListResponse])
async def get_my_courses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener cursos a los que el usuario logueado tiene acceso"""
    
    # Obtener cursos del usuario usando el servicio
    user_courses = course_service.get_user_courses(db, current_user.id)
    
    response = []
    for course in user_courses:
        # Verificar acceso
        has_access = course_service.check_user_access(db, current_user.id, course.id)
        
        # Cargar instructor
        instructor = db.query(User).filter(User.id == course.instructor_id).first()
        
        # Contar lecciones
        lesson_count = db.query(Lesson).filter(
            Lesson.course_id == course.id,
            Lesson.is_published == True
        ).count()
        
        # TODO: Calcular progreso real del usuario
        progress_percentage = 0  # Implementar más adelante
        
        response.append(CourseListResponse(
            id=course.id,
            title=course.title,
            short_description=course.short_description,
            cover_image_url=get_safe_cover_url(course.cover_image_url),
            level=course.level or "Beginner",
            language=course.language or "Español",
            category=course.category,
            price=course.price,
            is_premium=course.is_premium,
            instructor_name=instructor.name if instructor else "Desconocido",
            lesson_count=lesson_count,
            estimated_duration_hours=course.estimated_duration_hours,
            has_access=has_access,
            progress_percentage=progress_percentage,
            created_at=course.created_at
        ))
    
    return response

@router.get("/my-courses-all", response_model=List[CourseListResponse])
async def get_my_courses_all(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener TODOS los cursos con indicación de acceso para la página Mis Cursos"""
    
    # Obtener TODOS los cursos activos
    all_courses = db.query(Course).filter(Course.is_published == True).all()
    
    response = []
    for course in all_courses:
        # Verificar acceso del usuario a este curso
        has_access = course_service.check_user_access(db, current_user.id, course.id)
        
        # Solo incluir cursos a los que tiene acceso O cursos premium bloqueados para mostrar estado
        include_course = has_access or course.is_premium
        
        if include_course:
            # Cargar instructor
            instructor = db.query(User).filter(User.id == course.instructor_id).first()
            
            # Contar lecciones
            lesson_count = db.query(Lesson).filter(
                Lesson.course_id == course.id,
                Lesson.is_published == True
            ).count()
            
            # Calcular progreso real del usuario
            progress_percentage = 0
            if has_access and lesson_count > 0:
                # Contar lecciones completadas por el usuario
                completed_lessons = db.query(LessonProgress).join(Lesson).filter(
                    and_(
                        LessonProgress.user_id == current_user.id,
                        LessonProgress.is_completed == True,
                        Lesson.course_id == course.id,
                        Lesson.is_published == True
                    )
                ).count()
                
                progress_percentage = round((completed_lessons / lesson_count) * 100)
            
            response.append(CourseListResponse(
                id=course.id,
                title=course.title,
                short_description=course.short_description,
                cover_image_url=get_safe_cover_url(course.cover_image_url),
                level=course.level or "Beginner",
                language=course.language or "Español",
                category=course.category,
                price=course.price,
                is_premium=course.is_premium,
                instructor_name=instructor.name if instructor else "Desconocido",
                lesson_count=lesson_count,
                estimated_duration_hours=course.estimated_duration_hours,
                has_access=has_access,
                progress_percentage=progress_percentage,
                created_at=course.created_at
            ))
    
    return response

@router.get("/{course_id}/structure")
async def get_course_structure_public(
    course_id: int,
    db: Session = Depends(get_db)
):
    """Obtener estructura completa del curso (capítulos y lecciones) para vista pública"""
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.is_published == True
    ).first()
    
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    
    # Obtener capítulos publicados con sus lecciones
    chapters = db.query(Chapter).filter(
        Chapter.course_id == course_id,
        Chapter.is_published == True
    ).order_by(Chapter.order_index).all()
    
    result = []
    for chapter in chapters:
        # Obtener lecciones publicadas del capítulo
        lessons = db.query(Lesson).filter(
            Lesson.chapter_id == chapter.id,
            Lesson.is_published == True
        ).order_by(Lesson.order_index).all()
        
        lesson_list = []
        for lesson in lessons:
            lesson_list.append({
                "id": lesson.id,
                "title": lesson.title,
                "description": lesson.description,
                "content_type": lesson.content_type,
                "estimated_duration_minutes": lesson.estimated_duration_minutes,
                "is_free": lesson.is_free,
                "can_download": lesson.can_download,
                "order_index": lesson.order_index,
                # No incluimos URLs de archivos para vista pública
                "video_duration_seconds": lesson.video_duration_seconds,
                "file_type": lesson.file_type,
                "file_size_bytes": lesson.file_size_bytes
            })
        
        result.append({
            "id": chapter.id,
            "title": chapter.title,
            "description": chapter.description,
            "order_index": chapter.order_index,
            "lessons": lesson_list
        })
    
    return {
        "course": {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "short_description": course.short_description,
            "level": course.level,
            "language": course.language,
            "category": course.category,
            "estimated_duration_hours": course.estimated_duration_hours,
            "cover_image_url": get_safe_cover_url(course.cover_image_url)
        },
        "chapters": result
    }

@router.get("/{course_id}/structure-with-access")
async def get_course_structure_with_access(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener estructura del curso con verificación de acceso para usuarios logueados"""
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.is_published == True
    ).first()
    
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    
    # Verificar acceso del usuario al curso
    has_course_access = course_service.check_user_access(db, current_user.id, course_id)
    
    # Obtener capítulos publicados con sus lecciones
    chapters = db.query(Chapter).filter(
        Chapter.course_id == course_id,
        Chapter.is_published == True
    ).order_by(Chapter.order_index).all()
    
    result = []
    for chapter in chapters:
        # Obtener lecciones publicadas del capítulo
        lessons = db.query(Lesson).filter(
            Lesson.chapter_id == chapter.id,
            Lesson.is_published == True
        ).order_by(Lesson.order_index).all()
        
        lesson_list = []
        for lesson in lessons:
            # Verificar acceso a cada lección
            has_lesson_access = lesson.is_free or has_course_access or current_user.role.name == 'admin'
            
            lesson_data = {
                "id": lesson.id,
                "title": lesson.title,
                "description": lesson.description,
                "content_type": lesson.content_type,
                "estimated_duration_minutes": lesson.estimated_duration_minutes,
                "is_free": lesson.is_free,
                "can_download": lesson.can_download,
                "order_index": lesson.order_index,
                "video_duration_seconds": lesson.video_duration_seconds,
                "file_type": lesson.file_type,
                "file_size_bytes": lesson.file_size_bytes,
                "has_access": has_lesson_access
            }
            
            # Solo incluir URLs si tiene acceso
            if has_lesson_access:
                lesson_data["video_url"] = lesson.video_url
                lesson_data["file_url"] = lesson.file_url
                lesson_data["text_content"] = lesson.text_content
            
            lesson_list.append(lesson_data)
        
        result.append({
            "id": chapter.id,
            "title": chapter.title,
            "description": chapter.description,
            "order_index": chapter.order_index,
            "lessons": lesson_list
        })
    
    return {
        "course": {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "short_description": course.short_description,
            "level": course.level,
            "language": course.language,
            "category": course.category,
            "estimated_duration_hours": course.estimated_duration_hours,
            "cover_image_url": get_safe_cover_url(course.cover_image_url),
            "has_access": has_course_access
        },
        "chapters": result
    }

@router.get("/lessons/{lesson_id}/content")
async def get_lesson_content(
    lesson_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener contenido de una lección específica (requiere acceso)"""
    lesson = db.query(Lesson).filter(
        Lesson.id == lesson_id,
        Lesson.is_published == True
    ).first()
    
    if not lesson:
        raise HTTPException(status_code=404, detail="Lección no encontrada")
    
    # Verificar acceso al curso
    has_access = course_service.check_user_access(db, current_user.id, lesson.course_id)
    
    # Permitir acceso si es admin, la lección es gratuita, o el usuario tiene acceso al curso
    if not (current_user.role.name == 'admin' or lesson.is_free or has_access):
        raise HTTPException(
            status_code=403,
            detail="No tienes acceso a esta lección. Contacta al administrador."
        )
    
    # Generar URLs firmadas para archivos con 1 hora de duración
    def get_signed_url(url: str | None) -> str | None:
        if not url:
            return None
        
        # Si es una URL de R2, generar URL firmada temporal
        if url.startswith("https://") and "r2.dev" in url:
            try:
                from urllib.parse import urlparse
                from app.core.config import settings
                
                parsed_url = urlparse(url)
                object_key = parsed_url.path.lstrip('/')
                
                # Remover el nombre del bucket si está presente
                bucket_prefix = f"{settings.R2_BUCKET_NAME}/"
                if object_key.startswith(bucket_prefix):
                    object_key = object_key[len(bucket_prefix):]
                
                # Generar URL firmada con 1 hora de duración (3600 segundos)
                # Suficiente para una sesión de visualización completa
                signed_url = r2_service.generate_presigned_get_url(object_key, expiration=3600)
                return signed_url
            except Exception as e:
                print(f"Error generando URL firmada para {url}: {e}")
                return url
        
        # Si no es URL de R2, devolver tal cual
        return url
    
    return {
        "id": lesson.id,
        "title": lesson.title,
        "description": lesson.description,
        "content_type": lesson.content_type,
        "video_url": get_signed_url(lesson.video_url),
        "video_duration_seconds": lesson.video_duration_seconds,
        "file_url": get_signed_url(lesson.file_url),
        "file_type": lesson.file_type,
        "file_size_bytes": lesson.file_size_bytes,
        "text_content": lesson.text_content,
        "estimated_duration_minutes": lesson.estimated_duration_minutes,
        "is_free": lesson.is_free,
        "can_download": lesson.can_download,
        "chapter_id": lesson.chapter_id,
        "course_id": lesson.course_id,
        "thumbnail_url": get_signed_url(lesson.thumbnail_url) if hasattr(lesson, 'thumbnail_url') else None
    }

@router.post("/lessons/{lesson_id}/complete")
async def mark_lesson_complete(
    lesson_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Marcar una lección como completa"""
    from app.db.models import LessonProgress, CourseEnrollment
    from sqlalchemy import and_
    
    # Verificar que la lección existe
    lesson = db.query(Lesson).filter(
        Lesson.id == lesson_id,
        Lesson.is_published == True
    ).first()
    
    if not lesson:
        raise HTTPException(status_code=404, detail="Lección no encontrada")
    
    # Verificar acceso al curso
    has_access = course_service.check_user_access(db, current_user.id, lesson.course_id)
    
    if not (current_user.role.name == 'admin' or lesson.is_free or has_access):
        raise HTTPException(
            status_code=403,
            detail="No tienes acceso a esta lección"
        )
    
    # Buscar o crear progreso de lección
    lesson_progress = db.query(LessonProgress).filter(
        and_(
            LessonProgress.user_id == current_user.id,
            LessonProgress.lesson_id == lesson_id
        )
    ).first()
    
    if not lesson_progress:
        lesson_progress = LessonProgress(
            user_id=current_user.id,
            lesson_id=lesson_id,
            is_completed=True,
            progress_percentage=100,
            completed_at=func.now()
        )
        db.add(lesson_progress)
    else:
        lesson_progress.is_completed = True
        lesson_progress.progress_percentage = 100
        lesson_progress.completed_at = func.now()
    
    # Actualizar progreso del curso
    await update_course_progress(db, current_user.id, lesson.course_id)
    
    db.commit()
    
    return {
        "message": "Lección marcada como completa",
        "lesson_id": lesson_id,
        "is_completed": True
    }

@router.get("/courses/{course_id}/progress")
async def get_course_progress(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener progreso detallado de un curso"""
    from app.db.models import LessonProgress, CourseEnrollment
    from sqlalchemy import and_
    
    # Verificar acceso al curso
    has_access = course_service.check_user_access(db, current_user.id, course_id)
    
    if not has_access:
        raise HTTPException(
            status_code=403,
            detail="No tienes acceso a este curso"
        )
    
    # Obtener todas las lecciones del curso
    course_lessons = db.query(Lesson).join(Chapter).filter(
        Chapter.course_id == course_id,
        Lesson.is_published == True
    ).all()
    
    # Obtener progreso de cada lección
    progress_data = []
    completed_lessons = 0
    
    for lesson in course_lessons:
        lesson_progress = db.query(LessonProgress).filter(
            and_(
                LessonProgress.user_id == current_user.id,
                LessonProgress.lesson_id == lesson.id
            )
        ).first()
        
        is_completed = lesson_progress.is_completed if lesson_progress else False
        if is_completed:
            completed_lessons += 1
            
        progress_data.append({
            "lesson_id": lesson.id,
            "lesson_title": lesson.title,
            "is_completed": is_completed,
            "progress_percentage": lesson_progress.progress_percentage if lesson_progress else 0,
            "last_position_seconds": lesson_progress.last_position_seconds if lesson_progress else 0
        })
    
    total_lessons = len(course_lessons)
    course_progress_percentage = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
    
    return {
        "course_id": course_id,
        "total_lessons": total_lessons,
        "completed_lessons": completed_lessons,
        "progress_percentage": round(course_progress_percentage, 1),
        "lessons_progress": progress_data
    }

async def update_course_progress(db: Session, user_id: int, course_id: int):
    """Función auxiliar para actualizar el progreso del curso"""
    from app.db.models import LessonProgress, CourseEnrollment
    from sqlalchemy import and_
    
    # Contar lecciones totales y completadas
    total_lessons = db.query(Lesson).join(Chapter).filter(
        Chapter.course_id == course_id,
        Lesson.is_published == True
    ).count()
    
    completed_lessons = db.query(LessonProgress).join(Lesson).join(Chapter).filter(
        and_(
            LessonProgress.user_id == user_id,
            LessonProgress.is_completed == True,
            Chapter.course_id == course_id,
            Lesson.is_published == True
        )
    ).count()
    
    # Calcular porcentaje
    progress_percentage = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
    
    # Actualizar o crear enrollment
    enrollment = db.query(CourseEnrollment).filter(
        and_(
            CourseEnrollment.user_id == user_id,
            CourseEnrollment.course_id == course_id
        )
    ).first()
    
    if enrollment:
        enrollment.progress_percentage = round(progress_percentage, 1)
        enrollment.completed_lessons = completed_lessons
        enrollment.last_accessed_at = func.now()
    
    return progress_percentage

@router.get("/lessons/{lesson_id}/media-url")
async def get_lesson_media_url(
    lesson_id: int,
    media_type: str,  # "video" o "file"
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Regenerar URL firmada para archivos de lección (video o archivo descargable).
    Útil cuando la URL expira durante la visualización.
    """
    # Verificar que la lección existe
    lesson = db.query(Lesson).filter(
        Lesson.id == lesson_id,
        Lesson.is_published == True
    ).first()
    
    if not lesson:
        raise HTTPException(status_code=404, detail="Lección no encontrada")
    
    # Verificar acceso al curso
    has_access = course_service.check_user_access(db, current_user.id, lesson.course_id)
    
    if not (current_user.role.name == 'admin' or lesson.is_free or has_access):
        raise HTTPException(
            status_code=403,
            detail="No tienes acceso a esta lección"
        )
    
    # Obtener la URL según el tipo de media
    url = None
    if media_type == "video":
        url = lesson.video_url
    elif media_type == "file":
        url = lesson.file_url
    else:
        raise HTTPException(status_code=400, detail="Tipo de media inválido. Use 'video' o 'file'")
    
    if not url:
        raise HTTPException(status_code=404, detail=f"No hay {media_type} disponible para esta lección")
    
    # Generar URL firmada si es de R2
    if url.startswith("https://") and "r2.dev" in url:
        try:
            from urllib.parse import urlparse
            from app.core.config import settings
            
            parsed_url = urlparse(url)
            object_key = parsed_url.path.lstrip('/')
            
            # Remover el nombre del bucket si está presente
            bucket_prefix = f"{settings.R2_BUCKET_NAME}/"
            if object_key.startswith(bucket_prefix):
                object_key = object_key[len(bucket_prefix):]
            
            # Generar URL firmada con 1 hora de duración
            signed_url = r2_service.generate_presigned_get_url(object_key, expiration=3600)
            
            return {
                "media_type": media_type,
                "url": signed_url,
                "expires_in_seconds": 3600,
                "expires_in_minutes": 60
            }
        except Exception as e:
            print(f"Error generando URL firmada: {e}")
            raise HTTPException(status_code=500, detail="Error generando URL de acceso")
    
    # Si no es de R2, devolver la URL directamente
    return {
        "media_type": media_type,
        "url": url,
        "expires_in_seconds": None,
        "expires_in_minutes": None
    }

@router.get("/test-r2/{object_key:path}")
async def test_r2_signed_url(
    object_key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Endpoint de prueba para verificar URLs firmadas de R2"""
    try:
        print(f"🧪 Probando URL firmada para: {object_key}")
        signed_url = r2_service.generate_presigned_get_url(object_key, expiration=3600)
        print(f"✅ URL firmada generada: {signed_url}")
        
        return {
            "object_key": object_key,
            "signed_url": signed_url,
            "status": "success"
        }
    except Exception as e:
        print(f"❌ Error en test R2: {e}")
        import traceback
        traceback.print_exc()
        return {
            "object_key": object_key,
            "error": str(e),
            "status": "error"
        }

@router.get("/{course_id}", response_model=CourseResponse)
async def get_course_detail(
    course_id: int,
    db: Session = Depends(get_db)
):
    """Obtener detalles públicos de un curso específico"""
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.is_published == True
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado"
        )
    
    # Para vista pública, no verificamos acceso individual
    has_access = False
    lesson_count = db.query(Lesson).filter(
        Lesson.course_id == course.id,
        Lesson.is_published == True
    ).count()
    
    return CourseResponse(
        id=course.id,
        title=course.title,
        description=course.description or "",
        cover_image_url=get_safe_cover_url(course.cover_image_url),
        is_premium=course.is_premium,
        price=course.price,
        instructor_name=course.instructor.name,
        lesson_count=lesson_count,
        has_access=has_access
    )

@router.get("/{course_id}/lessons", response_model=List[LessonResponse])
async def get_course_lessons(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener lecciones de un curso"""
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.is_published == True
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado"
        )
    
    has_course_access = course_service.check_user_access(db, current_user.id, course.id)
    
    lessons = db.query(Lesson).filter(
        Lesson.course_id == course_id,
        Lesson.is_published == True
    ).order_by(Lesson.order_index).all()
    
    response = []
    for lesson in lessons:
        # Para lecciones gratuitas o si tiene acceso al curso
        has_access = lesson.is_free or has_course_access
        
        response.append(LessonResponse(
            id=lesson.id,
            title=lesson.title,
            description=lesson.description,
            duration_minutes=lesson.duration_minutes,
            order_index=lesson.order_index,
            is_free=lesson.is_free,
            has_access=has_access
        ))
    
    return response

@router.get("/lessons/{lesson_id}/video", response_model=VideoUrlResponse)
async def get_lesson_video_url(
    lesson_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener URL temporal para el video de una lección"""
    expiration = 3600  # 1 hora
    
    video_url = course_service.get_secure_video_url(
        db, current_user.id, lesson_id, expiration
    )
    
    return VideoUrlResponse(
        video_url=video_url,
        expires_in=expiration
    )

# Rutas de administración
@router.post("/access/grant-lifetime/{user_id}")
async def grant_lifetime_access(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Otorgar acceso premium de por vida a un alumno (después del pago)"""
    user = course_service.grant_lifetime_access(
        db, user_id, current_user.id, "Pago verificado - Acceso de por vida otorgado"
    )
    
    return {
        "message": f"✅ Acceso de por vida otorgado a {user.name}",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "has_premium_access": user.has_premium_access
        }
    }

@router.post("/premium/grant/{user_id}")
async def grant_premium_access(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Otorgar acceso premium general a un usuario"""
    success = course_service.grant_premium_access(db, user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    return {"message": "Acceso premium otorgado exitosamente"}

@router.post("/premium/revoke/{user_id}")
async def revoke_premium_access(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Revocar acceso premium general de un usuario"""
    success = course_service.revoke_premium_access(db, user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    return {"message": "Acceso premium revocado exitosamente"}

@router.post("/access/grant-course")
async def grant_course_access(
    request: AccessGrantRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Otorgar acceso a un curso específico (pago individual)"""
    enrollment = course_service.grant_course_access(
        db, request.user_id, request.course_id, current_user.id
    )
    
    # Cargar información del usuario y curso para la respuesta
    user = db.query(User).filter(User.id == request.user_id).first()
    course = db.query(Course).filter(Course.id == request.course_id).first()
    
    return {
        "message": f"✅ Acceso otorgado al curso '{course.title}' para {user.name}",
        "enrollment": {
            "id": enrollment.id,
            "user_name": user.name,
            "user_email": user.email,
            "course_title": course.title,
            "has_access": enrollment.has_access,
            "access_granted_date": enrollment.access_granted_date
        }
    }

@router.post("/access/revoke-course")
async def revoke_course_access_endpoint(
    request: AccessGrantRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Revocar acceso a un curso específico"""
    success = course_service.revoke_course_access(
        db, request.user_id, request.course_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment no encontrado"
        )
    
    # Cargar información del usuario y curso para la respuesta
    user = db.query(User).filter(User.id == request.user_id).first()
    course = db.query(Course).filter(Course.id == request.course_id).first()
    
    return {
        "message": f"❌ Acceso revocado al curso '{course.title}' para {user.name}"
    }

@router.get("/admin/enrollments")
async def get_all_enrollments(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Obtener todos los enrollments para administración"""
    enrollments = db.query(CourseEnrollment).all()
    
    response = []
    for enrollment in enrollments:
        response.append({
            "id": enrollment.id,
            "user_name": enrollment.user.name,
            "user_email": enrollment.user.email,
            "course_title": enrollment.course.title,
            "has_access": enrollment.has_access,
            "enrollment_date": enrollment.enrollment_date,
            "access_granted_date": enrollment.access_granted_date,
            "granted_by": enrollment.granted_by.name if enrollment.granted_by else None
        })
    
    return response

@router.get("/admin/user/{user_id}/courses")
async def get_user_courses_with_access_status(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Obtener todos los cursos con el estado de acceso de un usuario específico"""
    
    # Verificar que el usuario existe
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Obtener todos los cursos premium
    courses = db.query(Course).filter(Course.is_premium == True).all()
    
    response = []
    for course in courses:
        # Verificar si el usuario tiene acceso a este curso específico
        has_individual_access = course_service.check_user_access(db, user_id, course.id)
        
        # Cargar instructor
        instructor = db.query(User).filter(User.id == course.instructor_id).first()
        
        response.append({
            "id": course.id,
            "title": course.title,
            "short_description": course.short_description,
            "price": course.price,
            "is_premium": course.is_premium,
            "instructor_name": instructor.name if instructor else "Desconocido",
            "has_access": has_individual_access,
            "has_premium_global": target_user.has_premium_access
        })
    
    return response

# ===== RUTAS PARA GESTIÓN COMPLETA DE CURSOS (ADMIN) =====

# Gestión de Cursos
@router.post("/admin/courses/", response_model=CourseResponse)
async def create_course_admin(
    course_data: CourseCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Crear un nuevo curso"""
    course = course_service.create_course(db, course_data)
    
    # Cargar datos relacionados para la respuesta
    instructor = db.query(User).filter(User.id == course.instructor_id).first()
    return CourseResponse(
        **course.__dict__,
        instructor_name=instructor.name,
        chapter_count=0,
        lesson_count=0,
        total_duration_minutes=0,
        chapters=[]
    )

@router.put("/admin/courses/{course_id}")
async def update_course_admin(
    course_id: int,
    course_data: CourseUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Actualizar información del curso (solo admin)"""
    try:
        course = course_service.update_course(db, course_id, course_data)
        if not course:
            raise HTTPException(status_code=404, detail="Curso no encontrado")
        
        return {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "short_description": course.short_description,
            "cover_image_url": course.cover_image_url,
            "level": course.level,
            "language": course.language,
            "category": course.category,
            "estimated_duration_hours": course.estimated_duration_hours,
            "price": course.price,
            "is_premium": course.is_premium,
            "is_published": course.is_published,
            "updated_at": course.updated_at
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/admin/courses/", response_model=List[CourseListResponse])
async def get_admin_courses_list(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Obtener todos los cursos para administración"""
    courses = db.query(Course).all()
    
    response = []
    for course in courses:
        # Cargar instructor
        instructor = db.query(User).filter(User.id == course.instructor_id).first()
        
        # Contar lecciones
        lesson_count = db.query(Lesson).filter(Lesson.course_id == course.id).count()
        
        response.append(CourseListResponse(
            id=course.id,
            title=course.title,
            description=course.description,
            short_description=course.short_description,
            cover_image_url=get_safe_cover_url(course.cover_image_url),
            level=course.level or "Beginner",
            language=course.language or "Español",
            category=course.category,
            price=course.price,
            is_premium=course.is_premium,
            is_published=course.is_published,
            instructor_name=instructor.name if instructor else "Desconocido",
            lesson_count=lesson_count,
            estimated_duration_hours=course.estimated_duration_hours,
            created_at=course.created_at
        ))
    
    return response

@router.delete("/admin/courses/{course_id}")
async def delete_course_admin(
    course_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Eliminar (soft-delete) un curso: lo despublica para que no aparezca en la parte pública.
    Nota: La lista de admin actualmente muestra todos los cursos; si se desea ocultar los despublicados,
    podemos ajustar el listado o agregar un filtro.
    """
    try:
        ok = course_service.delete_course(db, course_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Course not found")
        return {"message": "Course deleted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===== RUTAS PARA GESTIÓN DE CAPÍTULOS Y LECCIONES =====

@router.get("/admin/{course_id}/structure")
async def get_course_structure_admin(
    course_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Obtener estructura completa del curso (capítulos y lecciones) para administradores"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    chapters = db.query(Chapter).filter(
        Chapter.course_id == course_id
    ).order_by(Chapter.order_index).all()
    
    result = []
    for chapter in chapters:
        lessons = db.query(Lesson).filter(
            Lesson.chapter_id == chapter.id
        ).order_by(Lesson.order_index).all()
        
        chapter_data = {
            "id": chapter.id,
            "title": chapter.title,
            "description": chapter.description,
            "order_index": chapter.order_index,
            "is_published": chapter.is_published,
            "course_id": chapter.course_id,
            "lessons": [
                {
                    "id": lesson.id,
                    "title": lesson.title,
                    "description": lesson.description,
                    "content_type": lesson.content_type,
                    "video_url": lesson.video_url,
                    "video_duration_seconds": lesson.video_duration_seconds,
                    "file_url": lesson.file_url,
                    "file_type": lesson.file_type,
                    "file_size_bytes": lesson.file_size_bytes,
                    "text_content": lesson.text_content,
                    "order_index": lesson.order_index,
                    "estimated_duration_minutes": lesson.estimated_duration_minutes,
                    "is_published": lesson.is_published,
                    "is_free": lesson.is_free,
                    "can_download": lesson.can_download,
                    "chapter_id": lesson.chapter_id,
                    "course_id": lesson.course_id
                } for lesson in lessons
            ]
        }
        result.append(chapter_data)
    
    return result

@router.post("/admin/chapters/")
async def create_chapter_admin(
    chapter_data: ChapterCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Crear nuevo capítulo"""
    try:
        chapter = course_service.create_chapter(db, chapter_data)
        return {
            "id": chapter.id,
            "title": chapter.title,
            "description": chapter.description,
            "order_index": chapter.order_index,
            "is_published": chapter.is_published,
            "course_id": chapter.course_id,
            "lessons": []
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/admin/chapters/{chapter_id}/")
async def update_chapter_admin(
    chapter_id: int,
    chapter_data: ChapterUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Actualizar un capítulo existente"""
    try:
        chapter = course_service.update_chapter(db, chapter_id, chapter_data)
        if not chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")

        lessons = db.query(Lesson).filter(
            Lesson.chapter_id == chapter.id
        ).order_by(Lesson.order_index).all()

        return {
            "id": chapter.id,
            "title": chapter.title,
            "description": chapter.description,
            "order_index": chapter.order_index,
            "is_published": chapter.is_published,
            "course_id": chapter.course_id,
            "lessons": [
                {
                    "id": lesson.id,
                    "title": lesson.title,
                    "description": lesson.description,
                    "content_type": lesson.content_type,
                    "video_url": lesson.video_url,
                    "video_duration_seconds": lesson.video_duration_seconds,
                    "file_url": lesson.file_url,
                    "file_type": lesson.file_type,
                    "file_size_bytes": lesson.file_size_bytes,
                    "text_content": lesson.text_content,
                    "order_index": lesson.order_index,
                    "estimated_duration_minutes": lesson.estimated_duration_minutes,
                    "is_published": lesson.is_published,
                    "is_free": lesson.is_free,
                    "can_download": lesson.can_download,
                    "chapter_id": lesson.chapter_id,
                    "course_id": lesson.course_id
                } for lesson in lessons
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/admin/chapters/{chapter_id}/")
async def delete_chapter_admin(
    chapter_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Eliminar un capítulo y sus lecciones asociadas"""
    try:
        ok = course_service.delete_chapter(db, chapter_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Chapter not found")
        return {"message": "Chapter deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/admin/courses/{course_id}/chapters/reorder/")
async def reorder_chapters_admin(
    course_id: int,
    payload: ChapterReorderRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Actualizar el orden de los capítulos de un curso"""
    try:
        updated_chapters = course_service.reorder_chapters(db, course_id, payload.chapter_ids)
        return {
            "message": "Chapters reordered",
            "chapters": [
                {
                    "id": chapter.id,
                    "order_index": chapter.order_index
                } for chapter in sorted(updated_chapters, key=lambda ch: ch.order_index)
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/admin/chapters/{chapter_id}/lessons/reorder/")
async def reorder_lessons_admin(
    chapter_id: int,
    payload: LessonReorderRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Actualizar el orden de las lecciones de un capítulo"""
    try:
        updated_lessons = course_service.reorder_lessons(db, chapter_id, payload.lesson_ids)
        return {
            "message": "Lessons reordered",
            "lessons": [
                {
                    "id": lesson.id,
                    "order_index": lesson.order_index
                } for lesson in sorted(updated_lessons, key=lambda l: l.order_index)
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/admin/lessons/{lesson_id}")
async def delete_lesson_admin(
    lesson_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Eliminar lección (y su archivo en R2 si existe)"""
    try:
        ok = course_service.delete_lesson(db, lesson_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Lesson not found")
        return {"message": "Lesson deleted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/admin/lessons/")
async def create_lesson_admin(
    lesson_data: LessonCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Crear nueva lección"""
    try:
        lesson = course_service.create_lesson(db, lesson_data)
        return {
            "id": lesson.id,
            "title": lesson.title,
            "description": lesson.description,
            "content_type": lesson.content_type,
            "video_url": lesson.video_url,
            "video_duration_seconds": lesson.video_duration_seconds,
            "file_url": lesson.file_url,
            "file_type": lesson.file_type,
            "file_size_bytes": lesson.file_size_bytes,
            "text_content": lesson.text_content,
            "order_index": lesson.order_index,
            "estimated_duration_minutes": lesson.estimated_duration_minutes,
            "is_published": lesson.is_published,
            "is_free": lesson.is_free,
            "can_download": lesson.can_download,
            "chapter_id": lesson.chapter_id,
            "course_id": lesson.course_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/admin/lessons/{lesson_id}")
async def update_lesson_admin(
    lesson_id: int,
    lesson_data: LessonUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Actualizar lección (usado para agregar archivos subidos)"""
    try:
        lesson = course_service.update_lesson(db, lesson_id, lesson_data)
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")
        
        return {
            "id": lesson.id,
            "title": lesson.title,
            "description": lesson.description,
            "content_type": lesson.content_type,
            "video_url": lesson.video_url,
            "video_duration_seconds": lesson.video_duration_seconds,
            "file_url": lesson.file_url,
            "file_type": lesson.file_type,
            "file_size_bytes": lesson.file_size_bytes,
            "text_content": lesson.text_content,
            "order_index": lesson.order_index,
            "estimated_duration_minutes": lesson.estimated_duration_minutes,
            "is_published": lesson.is_published,
            "is_free": lesson.is_free,
            "can_download": lesson.can_download,
            "chapter_id": lesson.chapter_id,
            "course_id": lesson.course_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
