from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, BigInteger, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()

# Tabla de asociación para la relación many-to-many entre posts y tags
post_tags = Table(
    'post_tags',
    Base.metadata,
    Column('post_id', Integer, ForeignKey('posts.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)

class Role(Base):
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255))
    
    # Relaciones
    users = relationship("User", back_populates="role")

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    google_id = Column(String(100), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    avatar_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    has_premium_access = Column(Boolean, default=False)  # Nuevo: Acceso premium
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    role = relationship("Role", back_populates="users")
    posts = relationship("Post", back_populates="author")
    # enrollments = relationship("CourseEnrollment", back_populates="user")  # Temporalmente comentado

class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(120), unique=True, nullable=False, index=True)
    description = Column(Text)
    color = Column(String(7), default="#3B82F6")  # Color hex para UI
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    posts = relationship("Post", back_populates="category")

class Tag(Base):
    __tablename__ = "tags"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    slug = Column(String(60), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    posts = relationship("Post", secondary=post_tags, back_populates="tags")

class Post(Base):
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(280), unique=True, nullable=False, index=True)
    excerpt = Column(Text)  # Resumen/descripción corta
    content = Column(Text, nullable=False)
    featured_image_url = Column(String(500))
    featured_image_object_key = Column(String(500))  # Para manejo de R2
    meta_title = Column(String(60))  # SEO
    meta_description = Column(String(160))  # SEO
    is_published = Column(Boolean, default=False)
    is_featured = Column(Boolean, default=False)  # Post destacado
    published_at = Column(DateTime(timezone=True))
    reading_time_minutes = Column(Integer)  # Tiempo estimado de lectura
    views_count = Column(Integer, default=0)
    
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    author = relationship("User", back_populates="posts")
    category = relationship("Category", back_populates="posts")
    tags = relationship("Tag", secondary=post_tags, back_populates="posts")

class Course(Base):
    __tablename__ = "courses"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    short_description = Column(String(500))  # Descripción corta para preview
    cover_image_url = Column(String(500))
    trailer_video_url = Column(String(500))  # Video trailer del curso
    level = Column(String(50), default="Beginner")  # Beginner, Intermediate, Advanced
    language = Column(String(50), default="Español")
    category = Column(String(100))  # Categoría del curso
    tags = Column(Text)  # Tags separados por comas
    estimated_duration_hours = Column(Integer)  # Duración estimada total
    is_published = Column(Boolean, default=False)
    is_premium = Column(Boolean, default=True)
    price = Column(String(50))
    instructor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    instructor = relationship("User")
    chapters = relationship("Chapter", back_populates="course", cascade="all, delete-orphan", order_by="Chapter.order_index")
    enrollments = relationship("CourseEnrollment", back_populates="course")

class Chapter(Base):
    __tablename__ = "chapters"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    order_index = Column(Integer, nullable=False)  # Orden dentro del curso
    is_published = Column(Boolean, default=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    course = relationship("Course", back_populates="chapters")
    lessons = relationship("Lesson", back_populates="chapter", cascade="all, delete-orphan", order_by="Lesson.order_index")

class Lesson(Base):
    __tablename__ = "lessons"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    content_type = Column(String(50), nullable=False)  # video, pdf, image, text, quiz
    
    # Contenido de video
    video_url = Column(String(500))  # URL pública para preview
    video_object_key = Column(String(500))  # Key privada en R2
    video_duration_seconds = Column(Integer)
    
    # Contenido de archivo (PDF, imágenes)
    file_url = Column(String(500))  # URL pública del archivo
    file_object_key = Column(String(500))  # Key en R2
    file_type = Column(String(50))  # pdf, jpg, png, etc.
    file_size_bytes = Column(BigInteger)
    
    # Contenido de texto
    text_content = Column(Text)  # Contenido HTML/Markdown
    
    # Metadatos
    order_index = Column(Integer, nullable=False)  # Orden dentro del capítulo
    estimated_duration_minutes = Column(Integer)  # Duración estimada
    is_published = Column(Boolean, default=False)
    is_free = Column(Boolean, default=False)  # Preview gratuito
    can_download = Column(Boolean, default=False)  # Permitir descarga de archivos
    
    # Relaciones
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)  # Redundante pero útil para consultas
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    chapter = relationship("Chapter", back_populates="lessons")
    course = relationship("Course")
    progress = relationship("LessonProgress", back_populates="lesson")

class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    is_completed = Column(Boolean, default=False)
    progress_percentage = Column(Integer, default=0)  # 0-100
    time_spent_seconds = Column(Integer, default=0)  # Tiempo total visto
    last_position_seconds = Column(Integer, default=0)  # Última posición en videos
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    lesson = relationship("Lesson", back_populates="progress")
    
    # Constraint para evitar duplicados
    __table_args__ = (
        {'extend_existing': True},
    )

class CourseEnrollment(Base):
    __tablename__ = "course_enrollments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    has_access = Column(Boolean, default=False)  # Control manual de acceso
    enrollment_date = Column(DateTime(timezone=True), server_default=func.now())
    access_granted_date = Column(DateTime(timezone=True))
    access_granted_by = Column(Integer, ForeignKey("users.id"))  # Admin que otorgó acceso
    
    # Progreso del curso
    progress_percentage = Column(Integer, default=0)  # 0-100
    completed_lessons = Column(Integer, default=0)
    total_time_spent_seconds = Column(Integer, default=0)
    last_accessed_at = Column(DateTime(timezone=True))
    
    # Relaciones con foreign_keys explícitos para evitar ambigüedad
    # user = relationship("User", foreign_keys=[user_id])  # Temporalmente comentado
    course = relationship("Course", back_populates="enrollments")
    # granted_by = relationship("User", foreign_keys=[access_granted_by])  # Temporalmente comentado
    
    # Constraint para evitar enrollments duplicados
    __table_args__ = (
        {'extend_existing': True},
    )

class HomepageContent(Base):
    __tablename__ = "homepage_content"
    
    id = Column(Integer, primary_key=True, index=True)
    section = Column(String(100), nullable=False, index=True)  # 'hero', 'about', 'stats', 'testimonials'
    title = Column(String(255))
    subtitle = Column(String(500))
    description = Column(Text)
    image_url = Column(String(500))
    button_text = Column(String(100))
    button_url = Column(String(255))
    order_index = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    extra_data = Column(Text)  # JSON para datos adicionales específicos de cada sección
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class HomepageGallery(Base):
    __tablename__ = "homepage_gallery"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    image_url = Column(String(500), nullable=False)
    category = Column(String(100))  # 'project', 'certificate', 'achievement', etc.
    order_index = Column(Integer, default=0)
    is_featured = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

