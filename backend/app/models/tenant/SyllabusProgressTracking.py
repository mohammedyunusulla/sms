from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, Numeric, ForeignKey, Text
from app.models.base import BaseModelTenant, BaseModelTenantMixin
from datetime import datetime


class SyllabusProgressTracking(BaseModelTenant, BaseModelTenantMixin):
    """
    Progress on syllabus components, kept per SECTION (QA B33): a teacher with sections A and B ticks them
    separately, and a replacement teacher carries on where the section was. teacher_id is who last recorded it.
    section_id NULL = a teacher with no section assignment for that syllabus (their own progress, as before).
    """
    __tablename__ = 'syllabus_progress_tracking'

    id = Column(Integer, primary_key=True, autoincrement=True)
    teacher_id = Column(Integer, ForeignKey('teachers.user_id', ondelete='CASCADE'), nullable=False)
    section_id = Column(Integer, ForeignKey('sections.id', ondelete='CASCADE'), nullable=True, index=True)

    # Links to the hierarchical levels
    item_type = Column(String(50), nullable=False)  # 'syllabus', 'lesson', 'topic', 'subtopic'
    item_id = Column(Integer, nullable=False)

    # Teacher specifics (Timeline)
    planned_start_date = Column(Date)
    planned_end_date = Column(Date)
    actual_start_date = Column(Date)
    actual_end_date = Column(Date)
    planned_completion_date = Column(Date)  # Specific for subtopics
    actual_completion_date = Column(Date)

    # Progress
    status = Column(String(20), default='planned')  # 'planned', 'in_progress', 'completed'
    completion_percentage = Column(Numeric(5, 2), default=0.00)
    is_completed = Column(Boolean, default=False)

    # Notes
    teacher_notes = Column(Text)

    # Metadata
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_active = Column(Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'teacher_id': self.teacher_id,
            'section_id': self.section_id,
            'item_type': self.item_type,
            'item_id': self.item_id,
            'planned_start_date': self.planned_start_date.isoformat() if self.planned_start_date else None,
            'planned_end_date': self.planned_end_date.isoformat() if self.planned_end_date else None,
            'actual_start_date': self.actual_start_date.isoformat() if self.actual_start_date else None,
            'actual_end_date': self.actual_end_date.isoformat() if self.actual_end_date else None,
            'planned_completion_date': self.planned_completion_date.isoformat() if self.planned_completion_date else None,
            'actual_completion_date': self.actual_completion_date.isoformat() if self.actual_completion_date else None,
            'status': self.status,
            'completion_percentage': float(self.completion_percentage),
            'is_completed': self.is_completed,
            'teacher_notes': self.teacher_notes
        }
