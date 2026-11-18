from app.models.base import BaseModelTenant, BaseModelTenantMixin
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, Float, Date, Time, Text, DateTime, func, UniqueConstraint
from sqlalchemy.orm import relationship

class ExamType(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = 'exam_types'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    exam_name = Column(String(100), nullable=False)  # FA1, FA2, Midterm, Final, etc.
    exam_code = Column(String(20), unique=True)
    exam_category = Column(String(50))  # 'Formative', 'Summative', 'Annual'
    sequence_order = Column(Integer)  # For ordering exams (1st, 2nd, etc.)
    
    exam_subjects = relationship("ExamSubjectConfig", back_populates="exam_type", cascade="all, delete-orphan")
    

class ExamSubjectConfig(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = 'exam_subject_configs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    exam_type_id = Column(Integer, ForeignKey('exam_types.id'), nullable=False)
    class_id = Column(Integer, ForeignKey('classes.id'), nullable=False)
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=True)  # Null means all sections
    subject_id = Column(Integer, ForeignKey('subjects.id'), nullable=False)
    
    # Marking scheme
    has_internal_external = Column(Boolean, default=False)
    internal_max_marks = Column(Integer, default=0)
    external_max_marks = Column(Integer, default=0)
    total_max_marks = Column(Integer, nullable=False)
    min_passing_marks = Column(Integer, nullable=False)
    
    # Weightage (useful for final grade calculation)
    weightage_percentage = Column(Float, default=100.0)
    
    exam_type = relationship("ExamType", back_populates="exam_subjects")
    class_ = relationship("Class")
    section = relationship("Section")
    subject = relationship("Subject")
    marks_entries = relationship("MarksEntry", back_populates="exam_config", cascade="all, delete-orphan")


class ExamTimetable(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = 'exam_timetables'

    id = Column(Integer, primary_key=True, autoincrement=True)
    academic_year_id = Column(Integer, ForeignKey('academic_years.id'), nullable=False)
    exam_type_id = Column(Integer, ForeignKey('exam_types.id'), nullable=False)
    class_id = Column(Integer, ForeignKey('classes.id'), nullable=False)
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=True)
    subject_id = Column(Integer, ForeignKey('subjects.id'), nullable=False)

    exam_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    duration_minutes = Column(Integer, nullable=True)

    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

    # Relationships
    academic_year = relationship("AcademicYear")
    exam_type = relationship("ExamType")
    class_ = relationship("Class")
    section = relationship("Section")
    subject = relationship("Subject")

    __table_args__ = (
        UniqueConstraint('academic_year_id', 'exam_type_id', 'class_id', 'section_id', 'subject_id',
                         name='uq_exam_timetable_entry'),
    )