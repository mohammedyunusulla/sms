from sqlalchemy import Date, Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import relationship

from app.models.base import BaseModelTenant, BaseModelTenantMixin


class StudentQRSticker(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = "student_qr_stickers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("institution_users.id"), nullable=False, unique=True, index=True)
    qr_code_value = Column(String(120), nullable=False, unique=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())

    student = relationship("InstitutionUsers")


class Homework(BaseModelTenant, BaseModelTenantMixin):
    """One homework of the Homework AI module (not the Assignments feature)."""
    __tablename__ = "homeworks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False, index=True)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=False, index=True)
    subject = Column(String(120), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    reference_answer_key = Column(Text, nullable=True)
    # Photos of the homework (e.g. a photo of the board) - stored under HOMEWORK_UPLOAD_DIR
    instruction_image_paths = Column(JSON, default=list, nullable=True)
    expected_time_minutes = Column(Integer, default=15, nullable=False)
    due_date = Column(DateTime, nullable=True)
    # the day the homework is for (students see it that day; afterwards it's in Past Homeworks, view only)
    homework_date = Column(Date, nullable=True, index=True)
    created_by = Column(Integer, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())

    class_obj = relationship("Class")
    section_obj = relationship("Section")


class StudentHomeworkSession(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = "student_homework_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("institution_users.id"), nullable=False, index=True)
    homework_id = Column(Integer, ForeignKey("homeworks.id"), nullable=False, index=True)
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
    # The notebook page: the QR sticker read from the start photo, and that photo (page blank + QR).
    # At submit the same QR must be on the uploaded pages. The same QR can be reused after the
    # previous session is completed; only active sessions lock the QR.
    page_qr_code = Column(String(255), nullable=True, index=True)
    start_image_path = Column(String(500), nullable=True)
    # Page checks: qr_matched, page_blank_at_start, same_page_as_start, notes, flagged
    integrity_json = Column(JSON, default=dict, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

    student = relationship("InstitutionUsers")
    homework = relationship("Homework")
