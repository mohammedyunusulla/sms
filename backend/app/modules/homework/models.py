from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy import JSON as SQLJSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class HomeworkBase(DeclarativeBase):
    pass


class StudentQRSticker(HomeworkBase):
    __tablename__ = "student_qr_stickers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(Integer, index=True, unique=True)
    qr_code_value: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class HomeworkAssignment(HomeworkBase):
    __tablename__ = "homework_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    skid: Mapped[str] = mapped_column(String(100), index=True)
    class_id: Mapped[int] = mapped_column(Integer, index=True)
    section_id: Mapped[int] = mapped_column(Integer, index=True)
    subject: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    reference_answer_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_time_minutes: Mapped[int] = mapped_column(Integer, default=15)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class StudentHomeworkSession(HomeworkBase):
    __tablename__ = "student_homework_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(Integer, index=True)
    assignment_id: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(20), default="in_progress", index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    last_resumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active_duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    hints_used_count: Mapped[int] = mapped_column(Integer, default=0)
    submission_image_paths: Mapped[list[str]] = mapped_column(SQLJSON, default=list)
    accuracy_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    efficiency_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_feedback_json: Mapped[dict] = mapped_column(SQLJSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


def create_homework_tables(engine) -> None:
    HomeworkBase.metadata.create_all(bind=engine)
