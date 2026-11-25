from datetime import datetime

from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, UniqueConstraint, Index

from app.models.base import BaseModelTenant, BaseModelTenantMixin


class Substitution(BaseModelTenant, BaseModelTenantMixin):
    """
    Cover for one timetable period on one date. substitute_teacher_id is empty for a period marked as needing
    cover by hand (reason MANUAL, e.g. exam duty) that has no substitute yet.
    Existing institution databases get this table at start-up.
    """
    __tablename__ = 'substitutions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    timetable_entry_id = Column(Integer, ForeignKey('timetable_entries.id', ondelete='CASCADE'), nullable=False)
    absent_teacher_id = Column(Integer, nullable=False)        # institution_users.id of the period's own teacher
    substitute_teacher_id = Column(Integer, nullable=True)     # institution_users.id of the cover
    reason = Column(String(20), nullable=False, default='LEAVE')   # LEAVE | ABSENT | HALF_DAY | MANUAL
    note = Column(String(255), nullable=True)
    assigned_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('date', 'timetable_entry_id', name='uq_substitution_date_entry'),
        Index('ix_substitutions_date', 'date'),
    )
