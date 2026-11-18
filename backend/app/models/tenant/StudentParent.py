from app.models.base import BaseModelTenant, BaseModelTenantMixin
from sqlalchemy import Column, String, Integer, func, ForeignKey
from sqlalchemy.orm import relationship

class StudentParent(BaseModelTenant, BaseModelTenantMixin): 
    __tablename__ = 'student_parents'
    student_user_id = Column(Integer, ForeignKey('students.user_id'), primary_key=True)
    parent_user_id = Column(Integer, ForeignKey('parent.user_id'), primary_key=True)
    relation_type = Column(String(10))

    # Relationships to access the profile objects
    student = relationship("Student", foreign_keys=[student_user_id], back_populates="parent_links")
    parent = relationship("Parent", foreign_keys=[parent_user_id], back_populates="children_links")

    def __repr__(self):
        return f"<StudentParent Student:{self.student_user_id} Parent:{self.parent_user_id} ({self.relation_type.value})>"

