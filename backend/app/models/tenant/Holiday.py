from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Boolean, ForeignKey, JSON, Index

from app.models.base import BaseModelTenant, BaseModelTenantMixin


class Holiday(BaseModelTenant, BaseModelTenantMixin):
    """
    A holiday (one day or a range) for everyone, students only or staff only. Tentative holidays (e.g. Eid,
    subject to moon sighting) count as holidays on their current date until confirmed or moved.
    Existing institution databases get this table at start-up.
    """
    __tablename__ = 'holidays'

    id = Column(Integer, primary_key=True, autoincrement=True)
    academic_year_id = Column(Integer, ForeignKey('academic_years.id'), nullable=True)
    name = Column(String(120), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    applies_to = Column(String(20), nullable=False, default='ALL')   # ALL | STUDENTS | STAFF
    is_tentative = Column(Boolean, nullable=False, default=False)
    note = Column(String(255), nullable=True)                        # e.g. "subject to moon sighting"
    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (Index('ix_holidays_dates', 'start_date', 'end_date'),)


class CalendarSetting(BaseModelTenant, BaseModelTenantMixin):
    """
    Weekly off days for an academic year: whole weekdays (0 = Monday ... 6 = Sunday) and optionally
    alternate Saturdays ('2_4' = 2nd and 4th Saturday, '1_3' = 1st and 3rd). A year without a row uses the
    latest earlier year's; with none at all, Sunday is the weekly off.
    """
    __tablename__ = 'calendar_settings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    academic_year_id = Column(Integer, ForeignKey('academic_years.id'), nullable=False, unique=True)
    weekly_off_days = Column(JSON, nullable=False, default=[6])
    alternate_saturdays = Column(String(10), nullable=False, default='NONE')   # NONE | 2_4 | 1_3
    updated_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
