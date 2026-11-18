from app.models.base import BaseModelTenant, BaseModelTenantMixin
from sqlalchemy import Column, Text, DateTime, Integer, ForeignKey, Boolean, func
from sqlalchemy.orm import relationship


class AssignmentSubmission(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = 'assignment_submissions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    assignment_id = Column(Integer, ForeignKey('assignments.id'), nullable=False)
    student_id = Column(Integer, ForeignKey('students.user_id'), nullable=False)
    is_completed = Column(Boolean, default=False)
    remarks = Column(Text, nullable=True)
    reviewed_by = Column(Integer, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

    # Relationships
    assignment = relationship("Assignment", back_populates="submissions")
    student = relationship("Student", backref="assignment_submissions")

    def to_dict(self):
        return {
            'id': self.id,
            'assignment_id': self.assignment_id,
            'student_id': self.student_id,
            'is_completed': self.is_completed,
            'remarks': self.remarks,
            'reviewed_by': self.reviewed_by,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<AssignmentSubmission assignment={self.assignment_id} student={self.student_id}>"
