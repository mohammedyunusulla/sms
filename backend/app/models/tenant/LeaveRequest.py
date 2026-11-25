from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, Index

from app.models.base import BaseModelTenant, BaseModelTenantMixin


class LeaveRequest(BaseModelTenant, BaseModelTenantMixin):
    """
    A leave application: a student's (applied by the student or a parent) or a staff member's.
    Existing institution databases get this table at start-up (see _bootstrap_tenant_schemas).
    """
    __tablename__ = 'leave_requests'

    id = Column(Integer, primary_key=True, autoincrement=True)
    applicant_type = Column(String(20), nullable=False)          # STUDENT | STAFF
    user_id = Column(Integer, ForeignKey('institution_users.id'), nullable=False)      # who is on leave
    applied_by = Column(Integer, ForeignKey('institution_users.id'), nullable=False)   # student, parent or staff
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=True)  # student's section when applied
    academic_year_id = Column(Integer, ForeignKey('academic_years.id'), nullable=True)
    from_date = Column(Date, nullable=False)
    to_date = Column(Date, nullable=False)
    leave_type = Column(String(30), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default='PENDING')  # PENDING | APPROVED | REJECTED | CANCELLED
    decided_by = Column(Integer, ForeignKey('institution_users.id'), nullable=True)
    decided_at = Column(DateTime, nullable=True)
    decision_note = Column(Text, nullable=True)
    # staff leave, set when approved: days counted (no Sundays) split into paid (within the yearly balance)
    # and unpaid (beyond it - the last days of the leave). See services/leave_balance.py
    paid_days = Column(Integer, nullable=True)
    unpaid_days = Column(Integer, nullable=True)
    # set when a holiday / weekly-off change recounted this approved leave
    recount_note = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('ix_leave_requests_user_dates', 'user_id', 'from_date', 'to_date'),
        Index('ix_leave_requests_status', 'status'),
    )

    def __repr__(self):
        return f"<LeaveRequest {self.id} {self.applicant_type} user={self.user_id} {self.from_date}..{self.to_date} {self.status}>"
