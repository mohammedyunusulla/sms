from sqlalchemy import Column, Integer, String, Text, Time, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import BaseModelTenant, BaseModelTenantMixin
from datetime import datetime


class TimetableEntry(BaseModelTenant, BaseModelTenantMixin):
    """Individual timetable entries (periods)"""
    __tablename__ = 'timetable_entries'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timetable_id = Column(Integer, ForeignKey('timetables.id'), nullable=False)
    
    # Schedule details
    day_of_week = Column(String(20), nullable=False)    # Monday, Tuesday, etc.
    period_number = Column(Integer, nullable=False)      # 1, 2, 3, etc.
    start_time = Column(Time, nullable=False)            # e.g., 09:00
    end_time = Column(Time, nullable=False)              # e.g., 09:45
    
    # Class details
    subject_id = Column(Integer, ForeignKey('subjects.id'), nullable=False)
    teacher_id = Column(Integer, ForeignKey('teachers.user_id'), nullable=False)
    room_number = Column(String(50), nullable=True)      # Room/Classroom number
    class_type = Column(String(20), default='Regular')   # Regular, Lab, Tutorial, etc.
    
    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    timetable = relationship("Timetable", back_populates="entries")
    subject = relationship("Subject", back_populates="timetable_entries")
    teacher = relationship("Teacher", back_populates="timetable_entries")
    
    # Unique constraint to prevent double booking
    __table_args__ = (
        UniqueConstraint(
            'timetable_id', 'day_of_week', 'period_number',
            name='unique_period_per_day_per_timetable'
        ),
        UniqueConstraint(
            'teacher_id', 'day_of_week', 'start_time', 'end_time',
            name='unique_teacher_schedule_per_time_slot'
        ),
    )
    
    def __repr__(self):
        return f"<TimetableEntry(id={self.id}, day={self.day_of_week}, period={self.period_number}, subject_id={self.subject_id})>"
        
        