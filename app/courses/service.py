from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status
from datetime import datetime

from app.db.models import User, Course, Chapter, Lesson, CourseEnrollment, LessonProgress
from app.courses.schemas import (
    CourseCreate, CourseUpdate, ChapterCreate, ChapterUpdate, 
    LessonCreate, LessonUpdate, LessonProgressUpdate
)
from app.storage.r2 import r2_service

class CourseService:
    @staticmethod
    def check_user_access(db: Session, user_id: int, course_id: int) -> bool:
        """Verificar si un usuario tiene acceso a un curso
        
        Niveles de acceso:
        1. Admin → Acceso total
        2. Curso gratuito → Todos pueden ver
        3. Premium global → Ve todos los cursos premium
        4. Enrollment específico → Solo cursos comprados individualmente
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        # 1. Los admins tienen acceso a todo
        if user.role.name == "admin":
            return True
        
        # 2. Para cursos gratuitos, todos pueden acceder
        course = db.query(Course).filter(Course.id == course_id).first()
        if course and not course.is_premium:
            return True
        
        # 3. ACCESO PREMIUM GLOBAL: Si el usuario tiene acceso premium global, puede ver todo
        if user.has_premium_access:
            return True
        
        # 4. ACCESO POR CURSO: Verificar si tiene enrollment específico para este curso
        enrollment = db.query(CourseEnrollment).filter(
            CourseEnrollment.user_id == user_id,
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.has_access == True
        ).first()
        
        return enrollment is not None
    
    @staticmethod
    def check_lesson_access(db: Session, user_id: int, lesson_id: int) -> bool:
        """Verificar si un usuario tiene acceso a una lección específica"""
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            return False
        
        # Si la lección es gratuita, todos pueden acceder
        if lesson.is_free:
            return True
        
        # Verificar acceso al curso
        return CourseService.check_user_access(db, user_id, lesson.course_id)
    
    @staticmethod
    def grant_lifetime_access(
        db: Session, 
        user_id: int, 
        granted_by_user_id: int,
        notes: str = "Pago verificado - Acceso premium global"
    ) -> User:
        """Otorgar acceso premium GLOBAL de por vida a un usuario (puede ver TODOS los cursos)"""
        # Verificar que el usuario que otorga sea admin
        granted_by = db.query(User).filter(User.id == granted_by_user_id).first()
        if not granted_by or granted_by.role.name != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo los administradores pueden otorgar acceso"
            )
        
        # Otorgar acceso premium global
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        user.has_premium_access = True
        user.updated_at = datetime.utcnow()
        
        # Registrar el evento en enrollments para tracking
        enrollment = CourseEnrollment(
            user_id=user_id,
            course_id=0,  # 0 indica acceso general premium global
            has_access=True,
            access_granted_date=datetime.utcnow(),
            access_granted_by=granted_by_user_id
        )
        db.add(enrollment)
        
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def grant_course_access(
        db: Session,
        user_id: int,
        course_id: int,
        granted_by_user_id: int,
        notes: str = "Acceso individual al curso"
    ) -> CourseEnrollment:
        """Otorgar acceso a UN CURSO ESPECÍFICO"""
        # Verificar que el usuario que otorga sea admin
        granted_by = db.query(User).filter(User.id == granted_by_user_id).first()
        if not granted_by or granted_by.role.name != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo los administradores pueden otorgar acceso"
            )
        
        # Verificar que el curso existe
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Curso no encontrado"
            )
        
        # Verificar que el usuario existe
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        # Verificar si ya tiene enrollment para este curso
        existing_enrollment = db.query(CourseEnrollment).filter(
            CourseEnrollment.user_id == user_id,
            CourseEnrollment.course_id == course_id
        ).first()
        
        if existing_enrollment:
            # Actualizar enrollment existente
            existing_enrollment.has_access = True
            existing_enrollment.access_granted_date = datetime.utcnow()
            existing_enrollment.access_granted_by = granted_by_user_id
            db.commit()
            db.refresh(existing_enrollment)
            return existing_enrollment
        else:
            # Crear nuevo enrollment
            enrollment = CourseEnrollment(
                user_id=user_id,
                course_id=course_id,
                has_access=True,
                access_granted_date=datetime.utcnow(),
                access_granted_by=granted_by_user_id
            )
            db.add(enrollment)
            db.commit()
            db.refresh(enrollment)
            return enrollment
    
    @staticmethod
    def revoke_course_access(db: Session, user_id: int, course_id: int) -> bool:
        """Revocar acceso a un curso"""
        enrollment = db.query(CourseEnrollment).filter(
            CourseEnrollment.user_id == user_id,
            CourseEnrollment.course_id == course_id
        ).first()
        
        if enrollment:
            enrollment.has_access = False
            db.commit()
            return True
        
        return False
    
    @staticmethod
    def grant_premium_access(db: Session, user_id: int) -> bool:
        """Otorgar acceso premium general a un usuario"""
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.has_premium_access = True
            db.commit()
            return True
        return False
    
    @staticmethod
    def revoke_premium_access(db: Session, user_id: int) -> bool:
        """Revocar acceso premium general de un usuario"""
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.has_premium_access = False
            db.commit()
            return True
        return False
    
    @staticmethod
    def get_secure_video_url(
        db: Session, 
        user_id: int, 
        lesson_id: int,
        expiration: int = 3600  # 1 hora por defecto
    ) -> Optional[str]:
        """Obtener URL firmada temporal para un video"""
        # Verificar acceso
        if not CourseService.check_lesson_access(db, user_id, lesson_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes acceso a esta lección"
            )
        
        # Obtener la lección
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson or not lesson.video_object_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video no encontrado"
            )
        
        # Generar URL firmada temporal
        try:
            url = r2_service.client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': r2_service.bucket_name,
                    'Key': lesson.video_object_key
                },
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generando URL del video: {str(e)}"
            )
    
    @staticmethod
    def get_user_courses(db: Session, user_id: int) -> List[Course]:
        """Obtener cursos a los que el usuario tiene acceso"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return []
        
        # Si es admin, obtener todos los cursos
        if user.role.name == "admin":
            return db.query(Course).filter(Course.is_published == True).all()
        
        # Si tiene acceso premium, obtener todos los cursos premium
        if user.has_premium_access:
            return db.query(Course).filter(
                Course.is_published == True,
                Course.is_premium == True
            ).all()
        
        # Obtener cursos específicos con enrollment
        enrollments = db.query(CourseEnrollment).filter(
            CourseEnrollment.user_id == user_id,
            CourseEnrollment.has_access == True
        ).all()
        
        course_ids = [e.course_id for e in enrollments]
        courses = db.query(Course).filter(
            Course.id.in_(course_ids),
            Course.is_published == True
        ).all()
        
        # Agregar cursos gratuitos
        free_courses = db.query(Course).filter(
            Course.is_published == True,
            Course.is_premium == False
        ).all()
        
        return courses + free_courses

    # ===== NUEVOS MÉTODOS PARA GESTIÓN COMPLETA DE CURSOS =====
    
    @staticmethod
    def create_course(db: Session, course_data: CourseCreate) -> Course:
        """Crear un nuevo curso"""
        course = Course(**course_data.dict())
        db.add(course)
        db.commit()
        db.refresh(course)
        return course

    @staticmethod
    def update_course(db: Session, course_id: int, course_data: CourseUpdate) -> Optional[Course]:
        """Actualizar un curso existente"""
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            return None
        
        for field, value in course_data.dict(exclude_unset=True).items():
            setattr(course, field, value)
        
        course.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(course)
        return course

    @staticmethod
    def get_course_with_structure(db: Session, course_id: int, user_id: Optional[int] = None) -> Optional[Course]:
        """Obtener curso completo con capítulos y lecciones"""
        course = db.query(Course).options(
            joinedload(Course.chapters).joinedload(Chapter.lessons),
            joinedload(Course.instructor)
        ).filter(Course.id == course_id).first()
        
        if not course:
            return None
        
        # Si hay un usuario, agregar información de progreso
        if user_id:
            # Verificar acceso
            has_access = CourseService.check_user_access(db, user_id, course_id)
            course.has_access = has_access
            
            # Obtener progreso si tiene acceso
            if has_access:
                enrollment = db.query(CourseEnrollment).filter(
                    CourseEnrollment.user_id == user_id,
                    CourseEnrollment.course_id == course_id
                ).first()
                
                if enrollment:
                    course.progress_percentage = enrollment.progress_percentage or 0
        
        return course

    @staticmethod
    def create_chapter(db: Session, chapter_data: ChapterCreate) -> Chapter:
        """Crear un nuevo capítulo"""
        chapter = Chapter(**chapter_data.dict())
        db.add(chapter)
        db.commit()
        db.refresh(chapter)
        return chapter

    @staticmethod
    def update_chapter(db: Session, chapter_id: int, chapter_data: ChapterUpdate) -> Optional[Chapter]:
        """Actualizar un capítulo"""
        chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
        if not chapter:
            return None
        
        for field, value in chapter_data.dict(exclude_unset=True).items():
            setattr(chapter, field, value)
        
        chapter.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(chapter)
        return chapter

    @staticmethod
    def create_lesson(db: Session, lesson_data: LessonCreate) -> Lesson:
        """Crear una nueva lección"""
        lesson = Lesson(**lesson_data.dict())
        db.add(lesson)
        db.commit()
        db.refresh(lesson)
        return lesson

    @staticmethod
    def update_lesson(db: Session, lesson_id: int, lesson_data: LessonUpdate) -> Optional[Lesson]:
        """Actualizar una lección"""
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            return None
        
        data = lesson_data.dict(exclude_unset=True)
        # Si recibimos file_url/video_url, quitamos los *_object_key para no sobreescribirlos accidentalmente
        if 'file_url' in data:
            data.pop('file_object_key', None)
        if 'video_url' in data:
            data.pop('video_object_key', None)
        for field, value in data.items():
            setattr(lesson, field, value)
        
        lesson.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(lesson)
        return lesson

    @staticmethod
    def update_lesson_progress(
        db: Session, 
        user_id: int, 
        lesson_id: int, 
        progress_data: LessonProgressUpdate
    ) -> LessonProgress:
        """Actualizar el progreso de una lección"""
        # Verificar que el usuario tenga acceso a la lección
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")
        
        if not CourseService.check_user_access(db, user_id, lesson.course_id):
            raise HTTPException(status_code=403, detail="Access denied to this lesson")
        
        # Buscar progreso existente o crear uno nuevo
        progress = db.query(LessonProgress).filter(
            LessonProgress.user_id == user_id,
            LessonProgress.lesson_id == lesson_id
        ).first()
        
        if not progress:
            progress = LessonProgress(
                user_id=user_id,
                lesson_id=lesson_id,
                **progress_data.dict()
            )
            db.add(progress)
        else:
            for field, value in progress_data.dict().items():
                setattr(progress, field, value)
        
        # Marcar como completado si el progreso es 100%
        if progress_data.progress_percentage >= 100 and not progress.is_completed:
            progress.is_completed = True
            progress.completed_at = datetime.utcnow()
        
        progress.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(progress)
        
        # Actualizar progreso del curso
        CourseService._update_course_progress(db, user_id, lesson.course_id)
        
        return progress

    @staticmethod
    def _update_course_progress(db: Session, user_id: int, course_id: int):
        """Actualizar el progreso general del curso basado en las lecciones completadas"""
        # Obtener total de lecciones del curso
        total_lessons = db.query(Lesson).filter(
            Lesson.course_id == course_id,
            Lesson.is_published == True
        ).count()
        
        if total_lessons == 0:
            return
        
        # Obtener lecciones completadas por el usuario
        completed_lessons = db.query(LessonProgress).join(Lesson).filter(
            LessonProgress.user_id == user_id,
            Lesson.course_id == course_id,
            LessonProgress.is_completed == True
        ).count()
        
        # Calcular porcentaje de progreso
        progress_percentage = int((completed_lessons / total_lessons) * 100)
        
        # Actualizar enrollment
        enrollment = db.query(CourseEnrollment).filter(
            CourseEnrollment.user_id == user_id,
            CourseEnrollment.course_id == course_id
        ).first()
        
        if enrollment:
            enrollment.progress_percentage = progress_percentage
            enrollment.completed_lessons = completed_lessons
            enrollment.last_accessed_at = datetime.utcnow()
            db.commit()

    @staticmethod
    def delete_course(db: Session, course_id: int) -> bool:
        """
        Eliminar un curso:
        - Si está publicado (is_published=True): soft delete (lo despublica)
        - Si NO está publicado (borrador): hard delete (lo elimina completamente)
        """
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            return False
        
        # Si el curso nunca fue publicado, eliminarlo completamente (hard delete)
        if not course.is_published:
            # Primero eliminar todas las lecciones de todos los capítulos
            chapters = db.query(Chapter).filter(Chapter.course_id == course_id).all()
            for chapter in chapters:
                # Eliminar lesson_progress asociados a las lecciones del capítulo
                lessons = db.query(Lesson).filter(Lesson.chapter_id == chapter.id).all()
                for lesson in lessons:
                    db.query(LessonProgress).filter(LessonProgress.lesson_id == lesson.id).delete()
                    db.delete(lesson)
                # Eliminar el capítulo
                db.delete(chapter)
            
            # Eliminar enrollments al curso
            db.query(CourseEnrollment).filter(CourseEnrollment.course_id == course_id).delete()
            
            # Finalmente eliminar el curso
            db.delete(course)
            db.commit()
            return True
        
        # Si el curso está o estuvo publicado, hacer soft delete
        course.is_published = False
        course.updated_at = datetime.utcnow()
        db.commit()
        return True

    @staticmethod
    def delete_chapter(db: Session, chapter_id: int) -> bool:
        """Eliminar un capítulo"""
        chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
        if not chapter:
            return False
        
        db.delete(chapter)
        db.commit()
        return True

    @staticmethod
    def reorder_chapters(db: Session, course_id: int, chapter_ids: List[int]) -> List[Chapter]:
        """Actualizar el orden de los capítulos de un curso"""
        chapters = db.query(Chapter).filter(Chapter.course_id == course_id).order_by(Chapter.order_index).all()
        if not chapters:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found or has no chapters")

        existing_ids = [chapter.id for chapter in chapters]
        if sorted(existing_ids) != sorted(chapter_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chapter IDs do not match course chapters")

        chapter_map = {chapter.id: chapter for chapter in chapters}
        for position, chapter_id in enumerate(chapter_ids, start=1):
            chapter = chapter_map.get(chapter_id)
            if chapter is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Chapter {chapter_id} does not belong to course")
            chapter.order_index = position
            chapter.updated_at = datetime.utcnow()

        db.commit()

        return db.query(Chapter).filter(Chapter.course_id == course_id).order_by(Chapter.order_index).all()

    @staticmethod
    def reorder_lessons(db: Session, chapter_id: int, lesson_ids: List[int]) -> List[Lesson]:
        """Actualizar el orden de las lecciones de un capítulo"""
        lessons = db.query(Lesson).filter(Lesson.chapter_id == chapter_id).order_by(Lesson.order_index).all()
        if not lessons:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found or has no lessons")

        existing_ids = [lesson.id for lesson in lessons]
        if sorted(existing_ids) != sorted(lesson_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lesson IDs do not match chapter lessons")

        lesson_map = {lesson.id: lesson for lesson in lessons}
        for position, lesson_id in enumerate(lesson_ids, start=1):
            lesson = lesson_map.get(lesson_id)
            if lesson is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Lesson {lesson_id} does not belong to chapter")
            lesson.order_index = position
            lesson.updated_at = datetime.utcnow()

        db.commit()

        return db.query(Lesson).filter(Lesson.chapter_id == chapter_id).order_by(Lesson.order_index).all()

    @staticmethod
    def delete_lesson(db: Session, lesson_id: int) -> bool:
        """Eliminar una lección y todos sus registros de progreso asociados"""
        from app.db.models import LessonProgress
        
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            return False
        
        # PRIMERO: Eliminar todos los registros de progreso de esta lección
        try:
            db.query(LessonProgress).filter(LessonProgress.lesson_id == lesson_id).delete(synchronize_session=False)
            db.flush()  # Asegurar que se ejecute antes de eliminar la lección
        except Exception as e:
            print(f"Error eliminando registros de progreso: {e}")
            db.rollback()
            raise
        
        # SEGUNDO: Intentar eliminar archivos asociados en R2 si existen
        try:
            from urllib.parse import urlparse
            def _extract_key(url: str) -> str:
                if not url:
                    return ''
                path = urlparse(url).path.lstrip('/') if (url.startswith('http://') or url.startswith('https://')) else url
                # Quitar prefijo de bucket si está presente
                from app.core.config import settings as _settings
                bucket_prefix = f"{_settings.R2_BUCKET_NAME}/"
                if path.startswith(bucket_prefix):
                    path = path[len(bucket_prefix):]
                # Fallback: mantener desde 'courses/...'
                idx = path.rfind('/courses/')
                if idx != -1:
                    path = path[idx+1:]
                return path

            if lesson.file_url:
                key = _extract_key(lesson.file_url)
                if key:
                    r2_service.delete_object(key)
            if lesson.video_url:
                keyv = _extract_key(lesson.video_url)
                if keyv:
                    r2_service.delete_object(keyv)
        except Exception as e:
            print(f"Error eliminando archivos de R2: {e}")
            # No fallar si no se pueden eliminar los archivos

        # TERCERO: Eliminar la lección
        db.delete(lesson)
        db.commit()
        return True

course_service = CourseService()
