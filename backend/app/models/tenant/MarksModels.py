from app.models.base import BaseModelTenant, BaseModelTenantMixin
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, Float, Text, UniqueConstraint
from sqlalchemy.orm import relationship

class MarksEntry(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = 'marks_entries'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    exam_config_id = Column(Integer, ForeignKey('exam_subject_configs.id'), nullable=False)
    student_id = Column(Integer, ForeignKey('students.user_id'), nullable=False)
    academic_year_id = Column(Integer, ForeignKey('academic_years.id'))
    
    # Marks fields
    internal_marks = Column(Float, default=0)
    external_marks = Column(Float, default=0)
    total_marks = Column(Float, nullable=False)
    
    # Additional fields
    is_absent = Column(Boolean, default=False)
    remarks = Column(Text)
    entered_by = Column(Integer, ForeignKey('institution_users.id'), nullable=True)
    
    exam_config = relationship("ExamSubjectConfig", back_populates="marks_entries")
    academic_year = relationship("AcademicYear", back_populates="marks_entries")
    student = relationship("Student")
    entered_by_user = relationship("InstitutionUsers", foreign_keys=[entered_by])
    
    # Add constraint to prevent duplicate entries
    __table_args__ = (
        UniqueConstraint('exam_config_id', 'student_id', 'academic_year_id', name='uq_exam_student_marks'),
    )