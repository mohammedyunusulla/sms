from app.models.base import BaseModel
from sqlalchemy import Column, String, Text, Integer, JSON
from sqlalchemy.orm import relationship

class Institution(BaseModel):
    __tablename__ = 'institutions'
    
    name = Column(String(200), nullable=False)
    code = Column(String(20), unique=True, nullable=False)  # Unique identifier for database naming
    address = Column(Text)
    phone = Column(String(20))
    email = Column(String(120))
    city = Column(String(120))
    state = Column(String(120))
    country = Column(String(120))   
    website = Column(String(200))
    # What the Super Admin switched on for this institution (see app/utils/features.py)
    features = Column(JSON, nullable=True)      # feature keys
    login_roles = Column(JSON, nullable=True)   # role codes that may sign in
    skid = Column(String(50))
    institution_admin_id = Column(Integer, nullable=True) # Institution admin user ID
    
    # Relationships
    users = relationship("User", back_populates="institution", cascade="all, delete-orphan")
    institution_admin = relationship("User", foreign_keys=[institution_admin_id],primaryjoin="Institution.institution_admin_id == User.id", post_update=True) # Institution admin user relationship
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def __repr__(self):
        return f'<Institution {self.name} ({self.code})>'
    
    @classmethod
    def get_by_code(cls, code):
        """Get institution by code"""
        return cls.query.filter_by(code=code, is_active=True).first()
    
    def to_dict(self, exclude_fields=None):
        """Convert institution to dictionary"""
        if exclude_fields is None:
            exclude_fields = []
        
        data = super().to_dict(exclude_fields)
        from app.utils.features import settings_of
        data.update(settings_of(self))  # features with what they need, valid sign-in roles
        return data
