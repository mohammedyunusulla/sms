from app.models.base import BaseModelTenant, BaseModelTenantMixin
from sqlalchemy import Column, Text, DateTime, Integer, Date, ForeignKey, Boolean, func
from sqlalchemy.orm import relationship


class Assignment(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = 'assignments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    teacher_id = Column(Integer, ForeignKey('teachers.user_id'), nullable=False)
    class_id = Column(Integer, ForeignKey('classes.id'), nullable=False)
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=False)
    subject_id = Column(Integer, ForeignKey('subjects.id'), nullable=False)
    academic_year_id = Column(Integer, ForeignKey('academic_years.id'), nullable=False)
    assignment_text = Column(Text, nullable=True)
    assignment_drawing = Column(Text, nullable=True)
    assignment_date = Column(Date, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

    # Relationships
    teacher = relationship("Teacher", backref="assignments")
    class_obj = relationship("Class", backref="assignments")
    section_obj = relationship("Section", backref="assignments")
    subject = relationship("Subject", backref="assignments")
    academic_year = relationship("AcademicYear", backref="assignments")
    submissions = relationship("AssignmentSubmission", back_populates="assignment", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'teacher_id': self.teacher_id,
            'class_id': self.class_id,
            'section_id': self.section_id,
            'subject_id': self.subject_id,
            'academic_year_id': self.academic_year_id,
            'assignment_text': self.assignment_text,
            'assignment_drawing': self.assignment_drawing,
            'assignment_date': self.assignment_date.isoformat() if self.assignment_date else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Assignment id={self.id} teacher={self.teacher_id} date={self.assignment_date}>"
