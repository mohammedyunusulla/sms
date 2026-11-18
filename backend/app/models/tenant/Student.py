from app.models.base import BaseModelTenant, BaseModelTenantMixin
from sqlalchemy import Column, String, DateTime, Integer, Date, Text, func, ForeignKey
from sqlalchemy.orm import relationship

class Student(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = 'students'

    user_id = Column(Integer, ForeignKey('school_users.id'), primary_key=True)
    roll_no = Column(String(50), nullable=True) # Unique within the school, e.g., roll number
    admission_date = Column(Date)
    class_id = Column(Integer, ForeignKey('classes.id'), nullable=True)
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=True) # Assuming a `sections` table will be created

    # Essential fields for ID Cards & Certificates
    student_photo = Column(Text, nullable=True)  # Base64 encoded image or URL
    blood_group = Column(String(10), nullable=True)  # A+, B+, O+, AB+, etc.
    emergency_contact = Column(String(20), nullable=True)

    # Identification Details
    admission_number = Column(String(50), nullable=True, unique=True)  # Unique permanent ID
    aadhar_number = Column(String(12), nullable=True)  # 12-digit Aadhar number
    birth_certificate_number = Column(String(100), nullable=True)
    nationality = Column(String(50), nullable=True, default='Indian')
    religion = Column(String(50), nullable=True)
    category = Column(String(50), nullable=True)  # General, OBC, SC, ST, EWS
    mother_tongue = Column(String(50), nullable=True)

    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    user = relationship("SchoolUsers", back_populates="student")
    section_obj = relationship("Section", back_populates="students_in_section") # Example, needs to be defined in Section
    attendance_records = relationship("Attendance", back_populates="student_profile")
    enrollments = relationship("StudentEnrollment", back_populates="student")
    parent_links = relationship(
        "StudentParent", 
        foreign_keys="[StudentParent.student_user_id]", 
        back_populates="student"
    )