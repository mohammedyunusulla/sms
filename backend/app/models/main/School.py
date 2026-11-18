from app.models.base import BaseModel
from sqlalchemy import Column, String, Text, Enum, Integer, ForeignKey, func
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

class SchoolPlan(enum.Enum):
    BASIC = "BASIC"
    STANDARD = "STANDARD"
    PREMIUM = "PREMIUM"

class School(BaseModel):
    __tablename__ = 'schools'
    
    name = Column(String(200), nullable=False)
    code = Column(String(20), unique=True, nullable=False)  # Unique identifier for database naming
    address = Column(Text)
    phone = Column(String(20))
    email = Column(String(120))
    city = Column(String(120))
    state = Column(String(120))
    country = Column(String(120))   
    website = Column(String(200))
    plan = Column(Enum(SchoolPlan), default=SchoolPlan.BASIC, nullable=False)
    skid = Column(String(50))
    school_admin_id = Column(Integer, nullable=True) # School admin user ID
    
    # Relationships
    users = relationship("User", back_populates="school", cascade="all, delete-orphan")
    school_admin = relationship("User", foreign_keys=[school_admin_id],primaryjoin="School.school_admin_id == User.id", post_update=True) # School admin user relationship
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def __repr__(self):
        return f'<School {self.name} ({self.code})>'
    
    @classmethod
    def get_by_code(cls, code):
        """Get school by code"""
        return cls.query.filter_by(code=code, is_active=True).first()
    
    def to_dict(self, exclude_fields=None):
        """Convert school to dictionary"""
        if exclude_fields is None:
            exclude_fields = []
        
        data = super().to_dict(exclude_fields)
        return data
