from app.models.base import BaseModelTenant, BaseModelTenantMixin
from sqlalchemy import Column, Integer, String, Text, Date, Numeric, Boolean, ForeignKey, CheckConstraint, UniqueConstraint, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

class Lesson(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = 'lessons'

    id = Column(Integer, primary_key=True, autoincrement=True)
    syllabus_id = Column(Integer, ForeignKey('syllabi.id', ondelete='CASCADE'), nullable=False)

    title = Column(String(255), nullable=False)
    description = Column(Text)
    sequence_order = Column(Integer, nullable=False)

    estimated_duration_hours = Column(Numeric(6, 2))
    lesson_notes = Column(Text)
    teaching_method = Column(String(100))
    resources_url = Column(Text)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    syllabus = relationship('Syllabus', back_populates='lessons')
    topics = relationship('Topic', back_populates='lesson', cascade='all, delete-orphan', order_by='Topic.sequence_order')

    # Constraints
    __table_args__ = (
        UniqueConstraint('syllabus_id', 'sequence_order', name='unique_syllabus_sequence'),
    )

    def to_dict(self, include_topics=False):
        """Convert lesson to dictionary"""
        data = {
            'id': self.id,
            'syllabus_id': self.syllabus_id,
            'title': self.title,
            'description': self.description,
            'sequence_order': self.sequence_order,
            'estimated_duration_hours': float(self.estimated_duration_hours) if self.estimated_duration_hours else 0,
            'lesson_notes': self.lesson_notes,
            'teaching_method': self.teaching_method,
            'resources_url': self.resources_url,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_topics and self.topics:
            data['topics'] = [topic.to_dict(include_subtopics=True) for topic in self.topics]
            data['total_topics'] = len(self.topics)

        return data

    def __repr__(self):
        return f"<Lesson {self.sequence_order}. {self.title}>"
