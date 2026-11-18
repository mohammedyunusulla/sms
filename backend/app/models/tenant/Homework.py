from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import relationship

from app.models.base import BaseModelTenant, BaseModelTenantMixin


class StudentQRSticker(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = "student_qr_stickers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("school_users.id"), nullable=False, unique=True, index=True)
    qr_code_value = Column(String(120), nullable=False, unique=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())

    student = relationship("SchoolUsers")


class HomeworkAssignment(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = "homework_assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False, index=True)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=False, index=True)
    subject = Column(String(120), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    reference_answer_key = Column(Text, nullable=True)
    expected_time_minutes = Column(Integer, default=15, nullable=False)
    due_date = Column(DateTime, nullable=True)
    created_by = Column(Integer, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())

    class_obj = relationship("Class")
    section_obj = relationship("Section")


class StudentHomeworkSession(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = "student_homework_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("school_users.id"), nullable=False, index=True)
    assignment_id = Column(Integer, ForeignKey("homework_assignments.id"), nullable=False, index=True)
    status = Column(String(20), default="in_progress", nullable=False, index=True)
    started_at = Column(DateTime, default=func.current_timestamp(), nullable=False)
    last_resumed_at = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    active_duration_seconds = Column(Integer, default=0, nullable=False)
    hints_used_count = Column(Integer, default=0, nullable=False)
    submission_image_paths = Column(JSON, default=list, nullable=False)
    accuracy_score = Column(Float, nullable=True)
    efficiency_score = Column(Float, nullable=True)
    ai_feedback_json = Column(JSON, default=dict, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

    student = relationship("SchoolUsers")
    assignment = relationship("HomeworkAssignment")
