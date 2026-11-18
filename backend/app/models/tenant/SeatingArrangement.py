from app.models.base import BaseModelTenant, BaseModelTenantMixin
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, Text, DateTime, Date, Time, JSON, func, UniqueConstraint
from sqlalchemy.orm import relationship


class ExamSeatingConfig(BaseModelTenant, BaseModelTenantMixin):
    """Maps rooms to classes/sections for a specific exam timetable entry."""
    __tablename__ = 'exam_seating_configs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    academic_year_id = Column(Integer, ForeignKey('academic_years.id'), nullable=False)
    exam_type_id = Column(Integer, ForeignKey('exam_types.id'), nullable=False)
    room_id = Column(Integer, ForeignKey('rooms.id'), nullable=False)

    # Which classes/sections sit in this room (stored as JSON array)
    # e.g. [{"class_id": 1, "section_id": 2}, {"class_id": 1, "section_id": 3}]
    class_assignments = Column(JSON, nullable=False)

    exam_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    invigilator_id = Column(Integer, ForeignKey('teachers.user_id'), nullable=True)

    is_generated = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

    # Relationships
    academic_year = relationship("AcademicYear")
    exam_type = relationship("ExamType")
    room = relationship("Room")
    invigilator = relationship("Teacher")
    seating_plans = relationship("SeatingPlan", back_populates="config", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('academic_year_id', 'exam_type_id', 'room_id', 'exam_date', 'start_time',
                         name='uq_seating_config_room_slot'),
    )


class SeatingPlan(BaseModelTenant, BaseModelTenantMixin):
    """Individual seat assignments generated from a seating config."""
    __tablename__ = 'seating_plans'

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_id = Column(Integer, ForeignKey('exam_seating_configs.id', ondelete='CASCADE'), nullable=False)
    student_id = Column(Integer, ForeignKey('students.user_id'), nullable=False)

    seat_row = Column(Integer, nullable=False)
    seat_column = Column(Integer, nullable=False)
    seat_label = Column(String(20), nullable=True)  # e.g. "R1-C3"

    created_at = Column(DateTime, default=func.current_timestamp())

    # Relationships
    config = relationship("ExamSeatingConfig", back_populates="seating_plans")
    student = relationship("Student")

    __table_args__ = (
        UniqueConstraint('config_id', 'seat_row', 'seat_column', name='uq_seating_plan_seat'),
        UniqueConstraint('config_id', 'student_id', name='uq_seating_plan_student'),
    )
