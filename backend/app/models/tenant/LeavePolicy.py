from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint

from app.models.base import BaseModelTenant, BaseModelTenantMixin


class LeavePolicy(BaseModelTenant, BaseModelTenantMixin):
    """
    Paid staff leave per leave type for an academic year (e.g. Casual 12, Sick 10, Other 0).
    paid_days NULL (or no row) means no limit: every approved day is paid. A year without rows uses the latest
    earlier year's policy. Existing institution databases get this table at start-up.
    """
    __tablename__ = 'leave_policies'

    id = Column(Integer, primary_key=True, autoincrement=True)
    academic_year_id = Column(Integer, ForeignKey('academic_years.id'), nullable=False)
    leave_type = Column(String(30), nullable=False)   # CASUAL | SICK | OTHER (staff leave types)
    paid_days = Column(Integer, nullable=True)        # NULL = no limit for this type
    updated_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (UniqueConstraint('academic_year_id', 'leave_type', name='uq_leave_policy_year_type'),)
