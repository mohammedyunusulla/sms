from sqlalchemy import Column, Integer, String, Text, Time, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import BaseModelTenant, BaseModelTenantMixin
from datetime import datetime


class Timetable(BaseModelTenant, BaseModelTenantMixin):
    """Main timetable configuration table"""
    __tablename__ = 'timetables'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    class_id = Column(Integer, ForeignKey('classes.id'), nullable=False)
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=False)
    academic_year_id = Column(Integer, ForeignKey('academic_years.id'))
    semester = Column(String(10), nullable=False)     # e.g., "1" or "2"
    
    # Time configuration
    period_duration = Column(Integer, default=45)       # Duration in minutes
    school_start_time = Column(Time, nullable=True)    # e.g., 09:00
    lunch_start_time = Column(Time, nullable=True)     # e.g., 12:30
    lunch_duration = Column(Integer, default=30)        # Duration in minutes
    total_periods = Column(Integer, default=7)          # Total periods per day
    
    # Metadata
    is_draft = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    class_ref = relationship("Class", back_populates="timetables")
    section_obj = relationship("Section", back_populates="timetables")
    academic_year = relationship("AcademicYear", back_populates="timetables")
    entries = relationship("TimetableEntry", back_populates="timetable", cascade="all, delete-orphan")
    
    # Unique constraint to prevent duplicate timetables
    __table_args__ = (
        UniqueConstraint(
             'class_id', 'section_id', 'academic_year_id', 'semester',
            name='unique_timetable_per_class_section_year_semester'
        ),
    )
    
    def __repr__(self):
        return f"<Timetable(id={self.id}, class_id={self.class_id}, section_id={self.section_id}, year={self.academic_year_id})>"


# Database indexes for better performance
"""
CREATE INDEX idx_timetable_school_class_section ON timetables( class_id, section_id);
CREATE INDEX idx_timetable_academic_year_semester ON timetables(academic_year_id, semester);
CREATE INDEX idx_timetable_entries_day_period ON timetable_entries(day_of_week, period_number);
CREATE INDEX idx_timetable_entries_teacher_time ON timetable_entries(teacher_id, day_of_week, start_time);
CREATE INDEX idx_timetable_entries_subject ON timetable_entries(subject_id);
CREATE INDEX idx_timetable_conflicts_unresolved ON timetable_conflicts(is_resolved, created_at);
"""