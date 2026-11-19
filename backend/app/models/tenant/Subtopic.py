from app.models.base import BaseModelTenant, BaseModelTenantMixin
from sqlalchemy import Column, Integer, String, Text, Date, Numeric, Boolean, ForeignKey, CheckConstraint, UniqueConstraint, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

class Subtopic(BaseModelTenantMixin, BaseModelTenant):
    __tablename__ = 'subtopics'

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic_id = Column(Integer, ForeignKey('topics.id', ondelete='CASCADE'), nullable=False)

    title = Column(String(255), nullable=False)
    description = Column(Text)
    sequence_order = Column(Integer, nullable=False)

    estimated_duration_hours = Column(Numeric(6, 2))
    learning_objectives = Column(Text)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    topic = relationship('Topic', back_populates='all_subtopics')

    # Constraints
    __table_args__ = (
        UniqueConstraint('topic_id', 'sequence_order', name='unique_topic_sequence'),
    )

    def to_dict(self):
        """Convert subtopic to dictionary"""
        return {
            'id': self.id,
            'topic_id': self.topic_id,
            'title': self.title,
            'description': self.description,
            'sequence_order': self.sequence_order,
            'estimated_duration_hours': float(self.estimated_duration_hours) if self.estimated_duration_hours else 0,
            'learning_objectives': self.learning_objectives,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Subtopic {self.sequence_order}. {self.title} ({'✓' if self.is_completed else '○'})>"
