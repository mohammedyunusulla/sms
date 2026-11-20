from app.models.base import BaseModelTenant, BaseModelTenantMixin
from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint


class ExamResultPublication(BaseModelTenant, BaseModelTenantMixin):
    """
    An exam's results released to students and parents for one academic year.
    Exam types are reused every year, so publishing is per (exam, year). No row = not published.
    """
    __tablename__ = 'exam_result_publications'

    id = Column(Integer, primary_key=True, autoincrement=True)
    exam_type_id = Column(Integer, ForeignKey('exam_types.id', ondelete='CASCADE'), nullable=False)
    academic_year_id = Column(Integer, ForeignKey('academic_years.id', ondelete='CASCADE'), nullable=False)
    published_at = Column(DateTime, nullable=False)
    published_by = Column(Integer, nullable=True)  # school_users.id

    __table_args__ = (
        UniqueConstraint('exam_type_id', 'academic_year_id', name='uq_exam_result_publication'),
    )

    def to_dict(self):
        return {
            'exam_type_id': self.exam_type_id,
            'academic_year_id': self.academic_year_id,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'published_by': self.published_by,
        }
