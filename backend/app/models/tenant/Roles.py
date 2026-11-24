from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, DateTime, func
from sqlalchemy.dialects.postgresql import ARRAY
from app.models.base import BaseModelTenant, BaseModelTenantMixin
from sqlalchemy.orm import relationship

class Role(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role_name = Column(String(80), nullable=False)
    role_code = Column(String(100), unique=True, nullable=False)
    description = Column(String(255))
    permissions = Column(ARRAY(String), default=[])  # Stores list like ['create_user', 'view_reports']
    is_system_role = Column(Boolean, default=False)
    # The built-in role a custom role is "based on" (PRINCIPAL / CLERK / BUS_STAFF): it is stored on the user's
    # login account, so it decides the dashboard and the server's access checks. Built-in roles: their own code.
    base_role = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    institution_id = Column(Integer, nullable=True)  # Null for system roles
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

    # Relationship back to User table (one-to-many from Role to User)
    users = relationship("InstitutionUsers", back_populates="role_obj")
    user_roles = relationship("UserRoles", back_populates="role", cascade="all, delete-orphan")
