"""Add chapters and lesson content system

Revision ID: chapters_content_001
Revises: 
Create Date: 2025-09-15 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'chapters_content_001'
down_revision = 'e04014b06b42'
branch_labels = None
depends_on = None


def upgrade():
    # Crear tabla chapters
    op.create_table('chapters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.Column('is_published', sa.Boolean(), nullable=True),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chapters_id'), 'chapters', ['id'], unique=False)

    # Crear tabla lesson_progress
    op.create_table('lesson_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('lesson_id', sa.Integer(), nullable=False),
        sa.Column('is_completed', sa.Boolean(), nullable=True),
        sa.Column('progress_percentage', sa.Integer(), nullable=True),
        sa.Column('time_spent_seconds', sa.Integer(), nullable=True),
        sa.Column('last_position_seconds', sa.Integer(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['lesson_id'], ['lessons.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lesson_progress_id'), 'lesson_progress', ['id'], unique=False)

    # Agregar nuevas columnas a courses
    op.add_column('courses', sa.Column('short_description', sa.String(length=500), nullable=True))
    op.add_column('courses', sa.Column('trailer_video_url', sa.String(length=500), nullable=True))
    op.add_column('courses', sa.Column('level', sa.String(length=50), nullable=True))
    op.add_column('courses', sa.Column('language', sa.String(length=50), nullable=True))
    op.add_column('courses', sa.Column('category', sa.String(length=100), nullable=True))
    op.add_column('courses', sa.Column('tags', sa.Text(), nullable=True))
    op.add_column('courses', sa.Column('estimated_duration_hours', sa.Integer(), nullable=True))

    # Agregar nuevas columnas a course_enrollments
    op.add_column('course_enrollments', sa.Column('progress_percentage', sa.Integer(), nullable=True))
    op.add_column('course_enrollments', sa.Column('completed_lessons', sa.Integer(), nullable=True))
    op.add_column('course_enrollments', sa.Column('total_time_spent_seconds', sa.Integer(), nullable=True))
    op.add_column('course_enrollments', sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=True))

    # Modificar tabla lessons - agregar nuevas columnas
    op.add_column('lessons', sa.Column('content_type', sa.String(length=50), nullable=False, server_default='video'))
    op.add_column('lessons', sa.Column('video_duration_seconds', sa.Integer(), nullable=True))
    op.add_column('lessons', sa.Column('file_url', sa.String(length=500), nullable=True))
    op.add_column('lessons', sa.Column('file_object_key', sa.String(length=500), nullable=True))
    op.add_column('lessons', sa.Column('file_type', sa.String(length=50), nullable=True))
    op.add_column('lessons', sa.Column('file_size_bytes', sa.BigInteger(), nullable=True))
    op.add_column('lessons', sa.Column('text_content', sa.Text(), nullable=True))
    op.add_column('lessons', sa.Column('estimated_duration_minutes', sa.Integer(), nullable=True))
    op.add_column('lessons', sa.Column('can_download', sa.Boolean(), nullable=True))
    op.add_column('lessons', sa.Column('chapter_id', sa.Integer(), nullable=True))

    # Actualizar foreign key de lessons para referenciar chapters
    op.create_foreign_key(None, 'lessons', 'chapters', ['chapter_id'], ['id'])

    # Actualizar valores por defecto
    op.execute("UPDATE courses SET level = 'Beginner' WHERE level IS NULL")
    op.execute("UPDATE courses SET language = 'Español' WHERE language IS NULL")
    op.execute("UPDATE course_enrollments SET progress_percentage = 0 WHERE progress_percentage IS NULL")
    op.execute("UPDATE course_enrollments SET completed_lessons = 0 WHERE completed_lessons IS NULL")
    op.execute("UPDATE course_enrollments SET total_time_spent_seconds = 0 WHERE total_time_spent_seconds IS NULL")
    op.execute("UPDATE lessons SET can_download = false WHERE can_download IS NULL")

def downgrade():
    # Eliminar columnas de lessons
    op.drop_constraint(None, 'lessons', type_='foreignkey')
    op.drop_column('lessons', 'chapter_id')
    op.drop_column('lessons', 'can_download')
    op.drop_column('lessons', 'estimated_duration_minutes')
    op.drop_column('lessons', 'text_content')
    op.drop_column('lessons', 'file_size_bytes')
    op.drop_column('lessons', 'file_type')
    op.drop_column('lessons', 'file_object_key')
    op.drop_column('lessons', 'file_url')
    op.drop_column('lessons', 'video_duration_seconds')
    op.drop_column('lessons', 'content_type')

    # Eliminar columnas de course_enrollments
    op.drop_column('course_enrollments', 'last_accessed_at')
    op.drop_column('course_enrollments', 'total_time_spent_seconds')
    op.drop_column('course_enrollments', 'completed_lessons')
    op.drop_column('course_enrollments', 'progress_percentage')

    # Eliminar columnas de courses
    op.drop_column('courses', 'estimated_duration_hours')
    op.drop_column('courses', 'tags')
    op.drop_column('courses', 'category')
    op.drop_column('courses', 'language')
    op.drop_column('courses', 'level')
    op.drop_column('courses', 'trailer_video_url')
    op.drop_column('courses', 'short_description')

    # Eliminar tablas
    op.drop_index(op.f('ix_lesson_progress_id'), table_name='lesson_progress')
    op.drop_table('lesson_progress')
    op.drop_index(op.f('ix_chapters_id'), table_name='chapters')
    op.drop_table('chapters')
