from app.models.base import BaseModelTenant, BaseModelTenantMixin
from sqlalchemy import Column, String, Integer, Date, Numeric, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

class StaffSalarySetup(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = 'staff_salary_setup'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    staff_id = Column(Integer, ForeignKey('institution_users.id'), nullable=False)
    academic_year_id = Column(Integer, ForeignKey('academic_years.id'), nullable=False)
    
    # Salary Components
    basic_salary = Column(Numeric(10, 2), nullable=False)
    allowances = Column(JSON, default={})  # {"hra": 5000, "da": 3000, "transport": 2000}
    deductions = Column(JSON, default={})  # {"pf": 1800, "tax": 500}
    gross_salary = Column(Numeric(10, 2), nullable=False)
    net_salary = Column(Numeric(10, 2), nullable=False)
    
    # Validity
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    staff = relationship("InstitutionUsers", backref="salary_setups")
    academic_year = relationship("AcademicYear", backref="staff_salaries")
    salary_payments = relationship("SalaryPayment", back_populates="salary_setup")


class SalaryPayment(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = 'salary_payments'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    staff_id = Column(Integer, ForeignKey('institution_users.id'), nullable=False)
    salary_setup_id = Column(Integer, ForeignKey('staff_salary_setup.id'), nullable=False)
    academic_year_id = Column(Integer, ForeignKey('academic_years.id'), nullable=False)
    
    # Payment Details
    payment_month = Column(Integer, nullable=False)  # 1-12
    payment_year = Column(Integer, nullable=False)
    payment_date = Column(Date, nullable=True)
    
    # Amounts
    basic_salary = Column(Numeric(10, 2), nullable=False)
    allowances_paid = Column(JSON, default={})
    deductions_applied = Column(JSON, default={})
    gross_amount = Column(Numeric(10, 2), nullable=False)
    net_amount_paid = Column(Numeric(10, 2), nullable=False)
    
    # Payment Info
    payment_method = Column(String(50))  # cash, bank_transfer, cheque
    transaction_reference = Column(String(100))
    status = Column(String(20), default='pending')  # pending, paid, cancelled
    notes = Column(String(500))
    
    # Metadata
    paid_by = Column(Integer, ForeignKey('institution_users.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    staff = relationship("InstitutionUsers", foreign_keys=[staff_id], backref="salary_payments")
    salary_setup = relationship("StaffSalarySetup", back_populates="salary_payments")
    academic_year = relationship("AcademicYear", backref="salary_payments")


class Expense(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = 'expenses'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    academic_year_id = Column(Integer, ForeignKey('academic_years.id'), nullable=False)
    
    # Expense Details
    expense_category = Column(String(50), nullable=False)  # Direct string from UI
    expense_date = Column(Date, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    vendor_name = Column(String(200))
    description = Column(String(500))
    
    # Reference for salary payments
    reference_type = Column(String(50))  # 'salary_payment', 'bill', 'service', 'other'
    reference_id = Column(Integer, nullable=True)  # Links to salary_payment.id if applicable
    
    # Payment
    payment_method = Column(String(50))  # cash, bank_transfer, cheque, online
    receipt_attachment_url = Column(String(500))
    
    # Approval workflow
    approval_status = Column(String(20), default='approved')  # pending, approved, rejected
    approved_by = Column(Integer, nullable=True)
    
    # Metadata
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    academic_year = relationship("AcademicYear", backref="expenses")
