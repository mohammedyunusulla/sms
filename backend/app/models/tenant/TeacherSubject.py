from app.models.base import BaseModelTenant, BaseModelTenantMixin
from sqlalchemy import Column,  DateTime, Integer, func, ForeignKey
from sqlalchemy.orm import relationship

class TeacherSubject(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = 'teacher_subjects'
    
    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey('teachers.user_id'), nullable=False)
    subject_id = Column(Integer, ForeignKey('subjects.id'), nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    teacher = relationship("Teacher", back_populates="teacher_subjects")
    subject = relationship("Subject", back_populates="teacher_subjects")
    