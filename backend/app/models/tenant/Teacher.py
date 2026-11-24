from app.models.base import BaseModelTenant, BaseModelTenantMixin
from sqlalchemy import Column, String, Text, DECIMAL, DateTime, Integer, Date, func, ForeignKey
from sqlalchemy.orm import relationship

class Teacher(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = 'teachers'
    
    user_id = Column(Integer, ForeignKey('institution_users.id'), primary_key=True)
    employee_id = Column(String(50), unique=True, nullable=False) # Unique within the institution
    designation = Column(String(100))
    date_of_joining = Column(Date)
    qualifications = Column(Text)
    salary = Column(DECIMAL(10, 2))
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

    user = relationship("InstitutionUsers", back_populates="teacher")
    teacher_subjects = relationship("TeacherSubject", back_populates="teacher", cascade="all, delete-orphan")   
    timetable_entries = relationship("TimetableEntry", back_populates="teacher", cascade="all, delete-orphan")