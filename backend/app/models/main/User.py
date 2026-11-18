from app.models.base import BaseModel
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import enum

class UserRole(enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    SCHOOL_ADMIN = "SCHOOL_ADMIN"
    PRINCIPAL = "PRINCIPAL"
    TEACHER = "TEACHER"
    STUDENT = "STUDENT"
    PARENT = "PARENT"
    BUS_STAFF = "BUS_STAFF"

class User(BaseModel):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(20))
    role = Column(Enum(UserRole), nullable=False)
    last_login = Column(DateTime)
    skid = Column(String(50))
    plan = Column(String(10), default='BASIC')
    school_id = Column(Integer, ForeignKey('schools.id'), nullable=True)  # Null for super admin
    school_user_id = Column(Integer, nullable=True)  # Links to student/teacher ID in school DB and Null for super admin
    # Account lockout fields
    failed_login_attempts = Column(Integer, default=0, nullable=True)
    locked_until = Column(DateTime, nullable=True)

    # Relationships
    school = relationship("School", back_populates="users")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password):
        """Set password hash using pbkdf2:sha256 with high iterations"""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256:600000')

    def check_password(self, password):
        """Check if password matches hash"""
        return check_password_hash(self.password_hash, password)

    def is_locked_out(self):
        """Check if account is currently locked"""
        if self.locked_until is not None and self.locked_until > datetime.utcnow():
            return True
        # Auto-unlock if lockout period has passed
        if self.locked_until is not None and self.locked_until <= datetime.utcnow():
            self.failed_login_attempts = 0
            self.locked_until = None
            self.save()
        return False

    def record_failed_login(self):
        """Record a failed login attempt and lock if threshold reached"""
        from app.services.auth_service import AuthService
        self.failed_login_attempts = (self.failed_login_attempts or 0) + 1
        if self.failed_login_attempts >= AuthService.MAX_FAILED_ATTEMPTS:
            self.locked_until = datetime.utcnow() + timedelta(minutes=AuthService.LOCKOUT_DURATION_MINUTES)
        self.save()

    def reset_failed_login(self):
        """Reset failed login counter on successful login"""
        if (self.failed_login_attempts or 0) > 0 or self.locked_until is not None:
            self.failed_login_attempts = 0
            self.locked_until = None
            self.save()
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
        return self.save()
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @classmethod
    def get_by_username(cls, username):
        """Get user by username"""
        return cls.query.filter_by(username=username, is_active=True).first()
    
    @classmethod
    def get_by_email(cls, email):
        """Get user by email"""
        return cls.query.filter_by(email=email, is_active=True).first()
    
    @classmethod
    def get_by_school(cls, school_id):
        """Get all users by school"""
        return cls.query.filter_by(school_id=school_id, is_active=True).all()
    
    # Fields that should never be sent to the client
    SENSITIVE_FIELDS = ['password_hash', 'failed_login_attempts', 'locked_until']

    def to_dict(self, exclude_fields=None):
        """Convert user to dictionary, excluding sensitive fields"""
        if exclude_fields is None:
            exclude_fields = list(self.SENSITIVE_FIELDS)
        else:
            exclude_fields.extend(self.SENSITIVE_FIELDS)

        data = super().to_dict(exclude_fields)
        data['full_name'] = self.full_name

        if self.school:
            data['school_name'] = self.school.name
            data['school_code'] = self.school.code
            data['skid'] = self.school.skid
        return data