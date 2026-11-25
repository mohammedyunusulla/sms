from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, Date, Time, DateTime, ForeignKey, JSON, Index

from app.models.base import BaseModelTenant, BaseModelTenantMixin


class Event(BaseModelTenant, BaseModelTenantMixin):
    """
    An institution event (Annual Day, a parent-teacher meeting, a sports meet...), all-day or with times,
    for everyone, all staff, students & parents, or specific sections. Cancelled events stay visible.
    Unlike a holiday it doesn't change attendance or leave. Existing institution databases get this table
    at start-up.
    """
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True, autoincrement=True)
    academic_year_id = Column(Integer, ForeignKey('academic_years.id'), nullable=True)
    title = Column(String(150), nullable=False)
    event_type = Column(String(20), nullable=False, default='GENERAL')   # GENERAL | PTM | SPORTS | CULTURAL | MEETING | OTHER
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=True)       # no time = all day
    end_time = Column(Time, nullable=True)
    location = Column(String(150), nullable=True)
    description = Column(Text, nullable=True)
    audience = Column(String(20), nullable=False, default='ALL')         # ALL | STAFF | STUDENTS | SECTIONS
    section_ids = Column(JSON, nullable=True)                            # for SECTIONS
    status = Column(String(20), nullable=False, default='ACTIVE')        # ACTIVE | CANCELLED
    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (Index('ix_events_dates', 'start_date', 'end_date'),)
