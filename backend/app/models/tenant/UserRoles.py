from sqlalchemy import Column, Integer, Boolean, ForeignKey, func
from sqlalchemy.dialects.postgresql import ARRAY
from app.models.base import BaseModelTenant, BaseModelTenantMixin
from sqlalchemy.orm import relationship

class UserRoles(BaseModelTenant, BaseModelTenantMixin):
    """User-Role assignment"""
    __tablename__ = 'user_roles'
    
    user_id = Column(Integer, ForeignKey('school_users.id'), primary_key=True)
    role_id = Column(Integer, ForeignKey('roles.id'), primary_key=True)
    assigned_by = Column(Integer, ForeignKey('school_users.id'), nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("SchoolUsers", back_populates="roles", foreign_keys=[user_id])
    role = relationship("Role", back_populates="user_roles")
    
    
    def __repr__(self):
        return f'<UserRole {self.user.user_code} - {self.role.role_code}>'