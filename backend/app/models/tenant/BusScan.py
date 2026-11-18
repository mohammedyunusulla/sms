import enum
from sqlalchemy import Column, Integer, String, DateTime, Text, Enum, ForeignKey, func
from app.models.base import BaseModelTenant, BaseModelTenantMixin


class BusScanType(enum.Enum):
    CHECK_IN = "CHECK_IN"
    CHECK_OUT = "CHECK_OUT"


class BusScan(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = "bus_scan"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_user_id = Column(Integer, ForeignKey('school_users.id'), nullable=False)
    scan_type = Column(Enum(BusScanType), nullable=False)
    scanned_at = Column(DateTime, default=func.current_timestamp(), nullable=False)
    scanned_by_user_id = Column(Integer, nullable=True)  # Bus staff school_users.id
    academic_year_id = Column(Integer, nullable=True)
    location = Column(String(255), nullable=True)   # Optional bus stop / route label
