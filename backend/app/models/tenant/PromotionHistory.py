from app.models.base import BaseModelTenant, BaseModelTenantMixin
from sqlalchemy import Column, String, Integer, Date, ForeignKey, func, Text 
from sqlalchemy.orm import relationship

class PromotionHistory(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = 'promotion_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_user_id = Column(Integer, ForeignKey('school_users.id'), nullable=False)
    from_academic_year_id = Column(Integer, ForeignKey('academic_years.id'), nullable=False)
    to_academic_year_id = Column(Integer, ForeignKey('academic_years.id'), nullable=False)
    from_class_id = Column(Integer, ForeignKey('classes.id'), nullable=False)
    to_class_id = Column(Integer, ForeignKey('classes.id'), nullable=False)
    from_section_id = Column(Integer, ForeignKey('sections.id'))
    to_section_id = Column(Integer, ForeignKey('sections.id'))
    promotion_date = Column(Date, nullable=False)
    promotion_type = Column(String(20), default='REGULAR')  # REGULAR, DETAINED, SPECIAL
    promoted_by = Column(Integer)
    remarks = Column(Text)
    
    # Relationships
    # Change the student relationship to:
    student = relationship("SchoolUsers", backref="promotion_history")
    from_academic_year = relationship("AcademicYear", foreign_keys=[from_academic_year_id], back_populates="promotions_from")
    to_academic_year = relationship("AcademicYear", foreign_keys=[to_academic_year_id], back_populates="promotions_to")
    from_class = relationship("Class", foreign_keys=[from_class_id])
    to_class = relationship("Class", foreign_keys=[to_class_id])