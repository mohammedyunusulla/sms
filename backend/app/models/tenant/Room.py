from app.models.base import BaseModelTenant, BaseModelTenantMixin
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, JSON
from datetime import datetime


class Room(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = 'rooms'

    id = Column(Integer, primary_key=True, autoincrement=True)
    room_name = Column(String(100), nullable=False)
    room_type = Column(String(50), nullable=False)
    building = Column(String(100), nullable=True)
    floor = Column(Integer, nullable=True)
    # seating_layout: JSON array of sides
    # e.g. [{"name": "Side-A", "rows": 10, "columns": 3}, {"name": "Side-B", "rows": 10, "columns": 3}]
    seating_layout = Column(JSON, nullable=True)
    capacity = Column(Integer, nullable=False)
    has_projector = Column(Boolean, default=False)
    has_ac = Column(Boolean, default=False)
    has_computers = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Room {self.room_name}>"
