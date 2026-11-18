from app.models.base import BaseModelTenant, BaseModelTenantMixin
from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship


class TeacherSyllabusAssignment(BaseModelTenant, BaseModelTenantMixin):
    """Tracks which teacher teaches which syllabus for which section.
    History is preserved when teachers change (is_active=False, unassigned_at set).
    """
    __tablename__ = 'teacher_syllabus_assignments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    syllabus_id = Column(Integer, ForeignKey('syllabi.id', ondelete='CASCADE'), nullable=False)
    teacher_id = Column(Integer, ForeignKey('teachers.user_id', ondelete='CASCADE'), nullable=False)
    section_id = Column(Integer, ForeignKey('sections.id', ondelete='CASCADE'), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    assigned_at = Column(DateTime, default=func.current_timestamp(), nullable=False)
    unassigned_at = Column(DateTime, nullable=True)

    syllabus = relationship("Syllabus", backref="teacher_assignments")
    teacher = relationship("Teacher", backref="syllabus_assignments")
    section = relationship("Section", backref="teacher_syllabus_assignments")

    def to_dict(self):
        return {
            'id': self.id,
            'syllabus_id': self.syllabus_id,
            'teacher_id': self.teacher_id,
            'section_id': self.section_id,
            'is_active': self.is_active,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'unassigned_at': self.unassigned_at.isoformat() if self.unassigned_at else None,
        }
