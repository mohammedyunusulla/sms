from app.models.base import BaseModelTenant, BaseModelTenantMixin
from sqlalchemy import Column, String, Integer, func, ForeignKey
from sqlalchemy.orm import relationship


class Section(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = 'sections'

    id = Column(Integer, primary_key=True)
    section_name = Column(String(100), nullable=False)
    class_id = Column(Integer, ForeignKey('classes.id'))
    teacher_id = Column(Integer, ForeignKey('teachers.user_id'))

    # Backref example
    class_obj = relationship("Class", back_populates="sections")
    teacher = relationship("Teacher", backref="sections_handled")
    students_in_section = relationship("Student", back_populates="section_obj")
    enrollments = relationship("StudentEnrollment", back_populates="section_obj")
    attendance_records = relationship("Attendance", back_populates="section_obj", cascade="all, delete-orphan")
    timetables = relationship("Timetable", back_populates="section_obj", cascade="all, delete-orphan")
    section_subjects = relationship("SectionSubject", back_populates="section", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            'id': self.id,
            'section_name': self.section_name,
            'class_id': self.class_id,
            'teacher_id': self.teacher_id,
            'teacher_name': getattr(self, 'teacher_name', None),
            'student_count': getattr(self, 'student_count', 0) 
        }    
