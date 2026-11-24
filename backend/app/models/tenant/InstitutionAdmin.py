from app.models.base import BaseModelTenant, BaseModelTenantMixin
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

class InstitutionAdmin(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = 'institution_admins'
    user_id = Column(Integer, ForeignKey('institution_users.id'), primary_key=True)
    designation = Column(String(100))
    user = relationship("InstitutionUsers", back_populates="institution_admin")

    def __repr__(self):
        return f"<InstitutionAdminProfile UserID:{self.user_id}>"