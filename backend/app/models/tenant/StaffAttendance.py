from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, UniqueConstraint, Index

from app.models.base import BaseModelTenant, BaseModelTenantMixin


class StaffAttendance(BaseModelTenant, BaseModelTenantMixin):
    """
    One staff member's attendance for one day (teachers, Principal, clerks, bus staff, custom staff roles).
    Existing institution databases get this table at start-up (see _bootstrap_tenant_schemas).
    """
    __tablename__ = 'staff_attendance'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('institution_users.id'), nullable=False)
    date = Column(Date, nullable=False)
    status = Column(String(20), nullable=False)   # PRESENT | ABSENT | LATE | HALF_DAY | LEAVE
    remarks = Column(Text)
    marked_by = Column(Integer, nullable=True)     # institution_users.id who first saved it
    updated_by = Column(Integer, nullable=True)    # ... and who last changed it
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('user_id', 'date', name='uq_staff_attendance_user_date'),
        Index('ix_staff_attendance_date', 'date'),
    )

    def __repr__(self):
        return f"<StaffAttendance user={self.user_id} {self.date} {self.status}>"
