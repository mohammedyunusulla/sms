from app.models.base import BaseModelTenant, BaseModelTenantMixin
from sqlalchemy import Column, String, Integer, func, ForeignKey, Boolean, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship


class SectionSubject(BaseModelTenant, BaseModelTenantMixin):
    """
    Association table linking subjects to sections
    Allows same subject to be taught in multiple sections with different teachers
    """
    __tablename__ = 'section_subjects'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=False)
    subject_id = Column(Integer, ForeignKey('subjects.id'), nullable=False)
    # academic_year_id = Column(Integer, ForeignKey('academic_years.id'))  # Optional: track by year
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Prevent duplicate subject-section assignments
    __table_args__ = (
        UniqueConstraint('section_id', 'subject_id', name='uq_section_subject_year'),
    )
    
    # Relationships
    section = relationship("Section", back_populates="section_subjects")
    subject = relationship("Subject", back_populates="section_subjects")
    
    def to_dict(self):
        return {
            'id': self.id,
            'section_id': self.section_id,
            'subject_id': self.subject_id,
            # 'academic_year_id': self.academic_year_id,
            'is_active': self.is_active
        }

    def __repr__(self):
        return f"<SectionSubject section_id={self.section_id} subject_id={self.subject_id}>"
