from app.models.base import BaseModelTenant, BaseModelTenantMixin
from sqlalchemy import Column, String, Text, DateTime, Integer, Date, ForeignKey, func
from sqlalchemy.orm import relationship

class Attendance(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = 'attendance'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_user_id = Column(Integer, ForeignKey('students.user_id'))
    class_id = Column(Integer, ForeignKey('classes.id'))
    section_id = Column(Integer, ForeignKey('sections.id'))
    date = Column(Date, nullable=False)
    status = Column(String(20), default='PRESENT')
    remarks = Column(Text)
    academic_year_id = Column(Integer, ForeignKey('academic_years.id'))
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    student_profile = relationship("Student", back_populates="attendance_records")
    section_obj = relationship("Section", back_populates="attendance_records")
    academic_year = relationship("AcademicYear", back_populates="attendance_records")

    def __repr__(self):
        return f"<Attendance StudentUserID:{self.student_user_id} Date:{self.date} Status:{self.status}>"
