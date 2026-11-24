from app.models.base import BaseModelTenant, BaseModelTenantMixin
from sqlalchemy import Column, String, Integer, func, ForeignKey, Text
from sqlalchemy.orm import relationship

class Parent(BaseModelTenant, BaseModelTenantMixin): # Inherit from BaseModelTenant
    __tablename__ = 'parent'
    
    user_id = Column(Integer, ForeignKey('institution_users.id'), primary_key=True)
    user = relationship("InstitutionUsers", back_populates="parent")
    relation_type = Column(String(50), nullable=True)  # e.g., 'Father', 'Mother', 'Guardian'
    
    # Father's details - making these nullable might be useful if the data is optional
    father_full_name = Column(String(100), nullable=True)
    father_phone = Column(String(20), nullable=True)
    father_occupation = Column(String(100), nullable=True)
    father_qualification = Column(String(100), nullable=True)

    # Mother's details - also potentially nullable
    mother_full_name = Column(String(100), nullable=True)
    mother_phone = Column(String(20), nullable=True)
    mother_occupation = Column(String(100), nullable=True)
    mother_qualification = Column(String(100), nullable=True)

    # Address details
    # Corrected the typo 'text' to 'Text' for a larger string field
    address = Column(Text)
    city = Column(String(255))
    state = Column(String(100))
    postal_code = Column(String(100))
    
    # Relationship to StudentParent (for linking to children)
    children_links = relationship("StudentParent", foreign_keys="[StudentParent.parent_user_id]", back_populates="parent")

    def __repr__(self):
        return f"<ParentProfile UserID:{self.user_id}>"

