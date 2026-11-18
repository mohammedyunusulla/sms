
from app.models.base import BaseModelTenant, BaseModelTenantMixin
from sqlalchemy import Column, String, Integer, ForeignKey, func
from sqlalchemy.orm import relationship

class Class(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = 'classes'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    class_name = Column(String(100), nullable=False)
    
     # Relationships
    sections = relationship("Section", back_populates="class_obj", cascade="all, delete-orphan")
    enrollments = relationship("StudentEnrollment", back_populates="class_obj")
    subjects = relationship("Subject", back_populates="class_", cascade="all, delete-orphan")
    timetables = relationship("Timetable", back_populates="class_ref", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'class_name': self.class_name,
            'student_count': getattr(self, 'student_count', 0)
        }

    def __repr__(self):
        return f"<Class {self.class_name}>"