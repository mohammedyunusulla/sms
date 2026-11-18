# app/models/tenant/fee_models.py

from sqlalchemy import Column, Integer, String, Numeric, Date, Boolean, ForeignKey, Enum, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM  # ✅ Import PostgreSQL-specific ENUM
from app.models.tenant import BaseModelTenant, BaseModelTenantMixin
from datetime import datetime
import enum


class FeeType(enum.Enum):
    TUITION = "Tuition Fee"
    ADMISSION = "Admission Fee"
    EXAM = "Exam Fee"
    LIBRARY = "Library Fee"
    SPORTS = "Sports Fee"
    TRANSPORT = "Transport Fee"
    HOSTEL = "Hostel Fee"
    LAB = "Lab Fee"
    ACTIVITY = "Activity Fee"
    LATE_FEE = "Late Fee"
    OTHER = "Other"


class PaymentMode(enum.Enum):
    CASH = "Cash"
    CHEQUE = "Cheque"
    ONLINE = "Online Transfer"
    UPI = "UPI"
    CARD = "Debit/Credit Card"
    DEMAND_DRAFT = "Demand Draft"


class PaymentStatus():
    PENDING = "PENDING"
    PARTIAL = "PARTIAL"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"

class RecurrenceType(enum.Enum):
    ONE_TIME = "ONE_TIME"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    YEARLY = "YEARLY"


fee_type_enum = PG_ENUM(
    FeeType,
    name='feetype',
    create_type=True,
    checkfirst=True
)

payment_mode_enum = PG_ENUM(
    PaymentMode,
    name='paymentmode',
    create_type=True,
    checkfirst=True
)


# 1. Fee Structure Template (Class/Grade wise)
class FeeStructure(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = 'fee_structures'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    academic_year_id = Column(Integer, ForeignKey('academic_years.id'))
    class_id = Column(Integer, ForeignKey('classes.id'), nullable=False)
    fee_name = Column(String(100), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    is_mandatory = Column(Boolean, default=True)
    is_recurring = Column(Boolean, default=False)
    recurrence_type = Column(String(50), nullable=True)
    recurrence_amount = Column(Numeric(10, 2), nullable=True)  # Amount per recurrence
    recurrence_months = Column(Integer, nullable=True)  # Number of months/occurrences
    allows_installments = Column(Boolean, default=True)  # Can be paid in installments
    is_active = Column(Boolean, default=True)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    class_info = relationship("Class", foreign_keys=[class_id])
    academic_year = relationship("AcademicYear", foreign_keys=[academic_year_id])
    
    def to_dict(self):
        return {
            'id': self.id,
            'academic_year_id': self.academic_year_id,
            'class_id': self.class_id,
            'fee_name': self.fee_name,
            'amount': float(self.amount) if self.amount else 0,
            'is_mandatory': self.is_mandatory,
            'is_recurring': self.is_recurring,
            'recurrence_type': self.recurrence_type,
            'recurrence_amount': float(self.recurrence_amount) if self.recurrence_amount else None,
            'recurrence_months': self.recurrence_months,
            'allows_installments': self.allows_installments,
            'is_active': self.is_active,
            'description': self.description,
            'created_at': self.created_at.isoformat() if hasattr(self, 'created_at') and self.created_at else None,
            'updated_at': self.updated_at.isoformat() if hasattr(self, 'updated_at') and self.updated_at else None
        }


# 2. Student Fee Assignment
class StudentFee(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = 'student_fees'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey('students.user_id'), nullable=False)
    fee_structure_id = Column(Integer, ForeignKey('fee_structures.id'), nullable=False)
    academic_year_id = Column(Integer, ForeignKey('academic_years.id'))
    due_date = Column(Date, nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    paid_amount = Column(Numeric(10, 2), default=0)
    discount_amount = Column(Numeric(10, 2), default=0)
    late_fee = Column(Numeric(10, 2), default=0)
    status = Column(String(50), default="PENDING")  # Use the reusable enum
    remarks = Column(Text)
    has_installments = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    student = relationship("Student", foreign_keys=[student_id])
    fee_structure = relationship("FeeStructure", foreign_keys=[fee_structure_id])
    academic_year = relationship("AcademicYear", foreign_keys=[academic_year_id])
    payments = relationship("FeePayment", back_populates="student_fee")
    installments = relationship("FeeInstallment", back_populates="student_fee")
    
    @property
    def balance_amount(self):
        return float(self.total_amount) - float(self.paid_amount)
    
    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'fee_structure_id': self.fee_structure_id,
            'academic_year_id': self.academic_year_id,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'total_amount': float(self.total_amount),
            'paid_amount': float(self.paid_amount),
            'discount_amount': float(self.discount_amount),
            'late_fee': float(self.late_fee),
            'balance_amount': self.balance_amount,
            'status': self.status,
            'remarks': self.remarks,
            'has_installments': self.has_installments,
            'created_at': self.created_at.isoformat() if hasattr(self, 'created_at') and self.created_at else None,
            'updated_at': self.updated_at.isoformat() if hasattr(self, 'updated_at') and self.updated_at else None
        }


# 3. Fee Payment Records
class FeePayment(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = 'fee_payments'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_fee_id = Column(Integer, ForeignKey('student_fees.id'), nullable=False)
    installment_id = Column(Integer, ForeignKey('fee_installments.id'))
    receipt_number = Column(String(50), unique=True, nullable=False)
    payment_date = Column(Date, nullable=False, default=datetime.now().date)
    amount_paid = Column(Numeric(10, 2), nullable=False)
    payment_mode = Column(payment_mode_enum, nullable=False)  # ✅ Use the reusable enum
    transaction_id = Column(String(100))
    cheque_number = Column(String(50))
    bank_name = Column(String(100))
    collected_by = Column(Integer, ForeignKey('school_users.id'))
    remarks = Column(Text)
    is_cancelled = Column(Boolean, default=False)
    cancelled_by = Column(Integer, ForeignKey('school_users.id'))
    cancelled_at = Column(DateTime)
    cancellation_reason = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    student_fee = relationship("StudentFee", back_populates="payments")
    collector = relationship("SchoolUsers", foreign_keys=[collected_by])
    installment = relationship("FeeInstallment", back_populates="payments")
    
    def to_dict(self):
        return {
            'id': self.id,
            'student_fee_id': self.student_fee_id,
            'installment_id': self.installment_id,
            'receipt_number': self.receipt_number,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'amount_paid': float(self.amount_paid),
            'payment_mode': self.payment_mode.name if self.payment_mode else None,
            'transaction_id': self.transaction_id,
            'cheque_number': self.cheque_number,
            'bank_name': self.bank_name,
            'collected_by': self.collected_by,
            'remarks': self.remarks,
            'is_cancelled': self.is_cancelled,
            'created_at': self.created_at.isoformat() if hasattr(self, 'created_at') and self.created_at else None,
            'updated_at': self.updated_at.isoformat() if hasattr(self, 'updated_at') and self.updated_at else None
        }


# 4. Fee Discount/Concession
class FeeDiscount(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = 'fee_discounts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey('students.user_id'), nullable=False)
    academic_year_id = Column(Integer, ForeignKey('academic_years.id'))
    discount_name = Column(String(100), nullable=False)
    discount_type = Column(String(20), nullable=False)  # PERCENTAGE or FIXED
    discount_value = Column(Numeric(10, 2), nullable=False)
    applicable_fees = Column(String(200))  # JSON array of fee_type
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date)
    is_active = Column(Boolean, default=True)
    approved_by = Column(Integer, ForeignKey('school_users.id'))
    reason = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    student = relationship("Student", foreign_keys=[student_id])
    academic_year = relationship("AcademicYear", foreign_keys=[academic_year_id])
    
    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'academic_year_id': self.academic_year_id,
            'discount_name': self.discount_name,
            'discount_type': self.discount_type,
            'discount_value': float(self.discount_value),
            'applicable_fees': self.applicable_fees,
            'valid_from': self.valid_from.isoformat() if self.valid_from else None,
            'valid_to': self.valid_to.isoformat() if self.valid_to else None,
            'is_active': self.is_active,
            'approved_by': self.approved_by,
            'reason': self.reason,
            'created_at': self.created_at.isoformat() if hasattr(self, 'created_at') and self.created_at else None,
            'updated_at': self.updated_at.isoformat() if hasattr(self, 'updated_at') and self.updated_at else None
        }


# 5. Fee Installments
class FeeInstallment(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = 'fee_installments'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_fee_id = Column(Integer, ForeignKey('student_fees.id'), nullable=False)
    installment_number = Column(Integer, nullable=False)
    installment_name = Column(String(100), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    due_date = Column(Date, nullable=False)
    paid_amount = Column(Numeric(10, 2), default=0)
    status = Column(String(50), default="PENDING")  #  Use the reusable enum
    remarks = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    student_fee = relationship("StudentFee", back_populates="installments")
    payments = relationship("FeePayment", back_populates="installment")
    
    @property
    def balance_amount(self):
        return float(self.amount) - float(self.paid_amount)
    
    def to_dict(self):
        return {
            'id': self.id,
            'student_fee_id': self.student_fee_id,
            'installment_number': self.installment_number,
            'installment_name': self.installment_name,
            'amount': float(self.amount),
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'paid_amount': float(self.paid_amount),
            'balance_amount': self.balance_amount,
            'status': self.status,
            'remarks': self.remarks,
            'created_at': self.created_at.isoformat() if hasattr(self, 'created_at') and self.created_at else None,
            'updated_at': self.updated_at.isoformat() if hasattr(self, 'updated_at') and self.updated_at else None
        }
