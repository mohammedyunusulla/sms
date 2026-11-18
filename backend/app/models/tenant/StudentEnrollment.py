from app.models.base import BaseModelTenant, BaseModelTenantMixin
from sqlalchemy import Column, String, Integer, Date, ForeignKey, func, Text
from sqlalchemy.orm import relationship

class StudentEnrollment(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = 'student_enrollments'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey('students.user_id'))
    class_id = Column(Integer, ForeignKey('classes.id'))
    section_id = Column(Integer, ForeignKey('sections.id'))
    academic_year_id = Column(Integer, ForeignKey('academic_years.id'), nullable=True)
    enrollment_date = Column(Date, default=func.current_date())
    promotion_date = Column(Date)
    status = Column(String(20), default='active')
    remarks = Column(Text)
    
    # Relationships
    student = relationship("Student", back_populates="enrollments")
    class_obj = relationship("Class", back_populates="enrollments")
    section_obj = relationship("Section", back_populates="enrollments")
    academic_year = relationship("AcademicYear", back_populates="student_enrollments")
    
    def __repr__(self):
        return f"<StudentEnrollment {self.student_id} - {self.academic_year_id}>"
