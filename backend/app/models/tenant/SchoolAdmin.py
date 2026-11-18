from app.models.base import BaseModelTenant, BaseModelTenantMixin
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

class SchoolAdmin(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = 'school_admins'
    user_id = Column(Integer, ForeignKey('school_users.id'), primary_key=True)
    designation = Column(String(100))
    user = relationship("SchoolUsers", back_populates="school_admin")

    def __repr__(self):
        return f"<SchoolAdminProfile UserID:{self.user_id}>"