from app.models.base import BaseModelTenant, BaseModelTenantMixin
from sqlalchemy import Column, String, Integer, Date, func, Boolean
from sqlalchemy.orm import relationship

class AcademicYear(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = 'academic_years'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    year_name = Column(String(50), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_current = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    student_enrollments = relationship("StudentEnrollment", back_populates="academic_year")
    attendance_records = relationship("Attendance", back_populates="academic_year")
    marks_entries = relationship("MarksEntry", back_populates="academic_year")
    timetables = relationship("Timetable", back_populates="academic_year")
    fee_structures = relationship("FeeStructure", back_populates="academic_year")
    student_fees = relationship("StudentFee", back_populates="academic_year")
    fee_discounts = relationship("FeeDiscount", back_populates="academic_year")
    promotions_from = relationship("PromotionHistory", foreign_keys="[PromotionHistory.from_academic_year_id]", back_populates="from_academic_year")
    promotions_to = relationship("PromotionHistory", foreign_keys="[PromotionHistory.to_academic_year_id]", back_populates="to_academic_year")