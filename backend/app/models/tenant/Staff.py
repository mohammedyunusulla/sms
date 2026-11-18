from app.models.base import BaseModelTenant, BaseModelTenantMixin
from sqlalchemy import Column, String, Integer, Date, func, ForeignKey, DECIMAL, Text
from sqlalchemy.orm import relationship

class Staff(BaseModelTenant, BaseModelTenantMixin):
    __tablename__ = 'staff'
    
    user_id = Column(Integer, ForeignKey('school_users.id'), primary_key=True)
    employee_id = Column(String(50), unique=True, nullable=False) # Unique within the school
    designation = Column(String(100)) # This is where 'Clerk', 'Librarian', 'Accountant', 'Janitor' etc. would go
    salary = Column(DECIMAL(10, 2))
    qualifications = Column(Text)
    date_of_joining = Column(Date)
    user = relationship("SchoolUsers", back_populates="staff")

    def __repr__(self):
        return f"<StaffProfile EmployeeID:{self.employee_id}>"