# app/models/institution_users.py
from app.models.base import BaseModelTenant, BaseModelTenantMixin
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, Date
from sqlalchemy.orm import relationship
from .UserRoles import UserRoles

# --- User Table (Tenant DB - consolidated users for a specific institution) ---
class InstitutionUsers(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = 'institution_users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date)
    gender = Column(String(20))
    address = Column(Text)
    phone = Column(String(20))
    role_id = Column(Integer, ForeignKey('roles.id'))
    skid = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)

    # Relationships to profile tables (one-to-one with cascade for deletion)
    institution_admin = relationship("InstitutionAdmin", uselist=False, back_populates="user", cascade="all, delete-orphan")
    teacher = relationship("Teacher", uselist=False, back_populates="user", cascade="all, delete-orphan")
    student = relationship("Student", uselist=False, back_populates="user", cascade="all, delete-orphan")
    staff = relationship("Staff", uselist=False, back_populates="user", cascade="all, delete-orphan")
    parent = relationship("Parent", uselist=False, back_populates="user", cascade="all, delete-orphan")
    role_obj = relationship("Role", back_populates="users")
    roles = relationship("UserRoles", back_populates="user", foreign_keys=[UserRoles.user_id])

    def __repr__(self):
        role_name = self.role_obj.role_name if self.role_obj else "No Role"
        return f"<InstitutionUser {self.username} Role: {role_name}>"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def to_dict(self, exclude_fields=None):
        if exclude_fields is None:
            exclude_fields = []
        data = super().to_dict(exclude_fields)
        data['full_name'] = self.full_name
        data['role'] = self.roles[0].role.to_dict() if self.roles else None

        # Add profile data if exists
        if self.institution_admin:
            data['profile'] = self.institution_admin.to_dict()
        elif self.teacher:
            data['profile'] = self.teacher.to_dict()
        elif self.student:
            data['profile'] = self.student.to_dict()
        elif self.staff:
            data['profile'] = self.staff.to_dict()
        elif self.parent:
            data['profile'] = self.parent.to_dict()

        return data
