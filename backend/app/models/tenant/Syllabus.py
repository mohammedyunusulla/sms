from app.models.base import BaseModelTenant, BaseModelTenantMixin
from sqlalchemy import Column, Integer, String, Text, Date, Numeric, Boolean, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

class Syllabus(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = 'syllabi'

    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, ForeignKey('subjects.id', ondelete='CASCADE'), nullable=False)
    academic_year_id = Column(Integer, ForeignKey('academic_years.id', ondelete='CASCADE'), nullable=False)
    created_by = Column(Integer, ForeignKey('school_users.id', ondelete='SET NULL'), nullable=True)

    title = Column(String(255), nullable=False)
    description = Column(Text)

    estimated_duration_hours = Column(Numeric(6, 2))

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    subject = relationship('Subject', backref='syllabi')
    academic_year = relationship('AcademicYear', backref='syllabi')
    creator = relationship('SchoolUsers', backref='syllabi_created', foreign_keys=[created_by])
    # every lesson (deleted ones too) - owns the rows
    all_lessons = relationship('Lesson', back_populates='syllabus', cascade='all, delete-orphan', order_by='Lesson.sequence_order')
    # what pages and reports show: active lessons only (deleted ones used to appear everywhere)
    lessons = relationship('Lesson', primaryjoin="and_(Lesson.syllabus_id == Syllabus.id, Lesson.is_active == True)",
                           order_by='Lesson.sequence_order', viewonly=True)

    # Constraints
    __table_args__ = (
        UniqueConstraint('subject_id', 'academic_year_id', name='unique_subject_academic_year'),
    )

    def to_dict(self, include_lessons=False):
        """Convert syllabus to dictionary"""
        # Get creator name - handle both direct teacher and school_user scenarios
        creator_name = None
        if self.creator:
            if hasattr(self.creator, 'teacher') and self.creator.teacher:
                # If creator is a SchoolUser with a teacher profile
                creator_name = f"{self.creator.first_name} {self.creator.last_name}"
            else:
                # Direct SchoolUser
                creator_name = f"{self.creator.first_name} {self.creator.last_name}"
        
        data = {
            'id': self.id,
            'subject_id': self.subject_id,
            'subject_name': self.subject.subject_name if self.subject else None,
            'academic_year_id': self.academic_year_id,
            'academic_year_name': self.academic_year.year_name if self.academic_year else None,
            'created_by': self.created_by,
            'creator_name': creator_name,
            'title': self.title,
            'description': self.description,
            'estimated_duration_hours': float(self.estimated_duration_hours) if self.estimated_duration_hours else 0,
            'status': 'planned',
            'completion_percentage': 0,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_lessons:
            data['lessons'] = [lesson.to_dict(include_topics=True) for lesson in self.lessons]
            data['total_lessons'] = len(self.lessons)

        return data

    def __repr__(self):
        return f"<Syllabus {self.title} - {self.subject.subject_name if self.subject else 'No Subject'}>"