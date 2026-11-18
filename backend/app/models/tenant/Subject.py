from app.models.base import BaseModelTenant, BaseModelTenantMixin
from sqlalchemy import Column, String, Text, Integer, func, ForeignKey
from sqlalchemy.orm import relationship

class Subject(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = 'subjects'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_name = Column(String(100), nullable=False)
    subject_code = Column(String(20), unique=True)
    credits = Column(Integer, default=1)
    description = Column(Text)
    class_id = Column(Integer, ForeignKey('classes.id'), nullable=False)
    
    class_ = relationship("Class", back_populates="subjects")
    teacher_subjects = relationship("TeacherSubject", back_populates="subject", cascade="all, delete-orphan")
    timetable_entries = relationship("TimetableEntry", back_populates="subject", cascade="all, delete-orphan")
    section_subjects = relationship("SectionSubject", back_populates="subject", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Subject {self.subject_name} ({self.subject_code})>"