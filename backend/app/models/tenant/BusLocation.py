from sqlalchemy import Column, Integer, Float, Boolean, DateTime, ForeignKey, func
from app.models.base import BaseModelTenant, BaseModelTenantMixin


class BusLocation(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = "bus_location"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bus_staff_user_id = Column(Integer, ForeignKey('school_users.id'), nullable=False, unique=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    heading = Column(Float, nullable=True)
    speed = Column(Float, nullable=True)      # km/h
    is_active = Column(Boolean, default=False, nullable=False)
    updated_at = Column(DateTime, default=func.current_timestamp(), nullable=False)
