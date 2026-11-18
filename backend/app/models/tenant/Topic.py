from app.models.base import BaseModelTenant, BaseModelTenantMixin
from sqlalchemy import Column, Integer, String, Text, Date, Numeric, Boolean, ForeignKey, CheckConstraint, UniqueConstraint, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

class Topic(BaseModelTenantMixin, BaseModelTenant):
    __tablename__ = 'topics'

    id = Column(Integer, primary_key=True, autoincrement=True)
    lesson_id = Column(Integer, ForeignKey('lessons.id', ondelete='CASCADE'), nullable=False)

    title = Column(String(255), nullable=False)
    description = Column(Text)
    sequence_order = Column(Integer, nullable=False)

    estimated_duration_hours = Column(Numeric(6, 2))

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    lesson = relationship('Lesson', back_populates='topics')
    subtopics = relationship('Subtopic', back_populates='topic', cascade='all, delete-orphan', order_by='Subtopic.sequence_order')

    # Constraints
    __table_args__ = (
        UniqueConstraint('lesson_id', 'sequence_order', name='unique_lesson_sequence'),
    )

    def to_dict(self, include_subtopics=False):
        """Convert topic to dictionary"""
        data = {
            'id': self.id,
            'lesson_id': self.lesson_id,
            'title': self.title,
            'description': self.description,
            'sequence_order': self.sequence_order,
            'estimated_duration_hours': float(self.estimated_duration_hours) if self.estimated_duration_hours else 0,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_subtopics and self.subtopics:
            data['subtopics'] = [subtopic.to_dict() for subtopic in self.subtopics]
            data['total_subtopics'] = len(self.subtopics)

        return data

    def __repr__(self):
        return f"<Topic {self.sequence_order}. {self.title}>"
