from app.models.base import BaseModel
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

class UserSession(BaseModel):
    __tablename__ = 'user_sessions'
    
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    session_token = Column(String(255), unique=True, nullable=False)
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(Text)
    login_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    logout_time = Column(DateTime, nullable=True)
    is_logged_out = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    def logout(self):
        """Mark session as logged out"""
        self.logout_time = datetime.utcnow()
        self.is_logged_out = True
        return self.save()
    
    @property
    def session_duration(self):
        """Calculate session duration"""
        end_time = self.logout_time if self.logout_time else datetime.utcnow()
        return end_time - self.login_time
    
    @classmethod
    def get_active_session(cls, session_token):
        """Get active session by token"""
        return cls.query.filter_by(
            session_token=session_token, 
            is_logged_out=False, 
            is_active=True
        ).first()
    
    @classmethod
    def get_user_sessions(cls, user_id, active_only=False):
        """Get all sessions for a user"""
        query = cls.query.filter_by(user_id=user_id, is_active=True)
        if active_only:
            query = query.filter_by(is_logged_out=False)
        return query.all()
    
    def to_dict(self, exclude_fields=None):
        """Convert session to dictionary"""
        if exclude_fields is None:
            exclude_fields = ['session_token']  # Don't expose session tokens
        else:
            exclude_fields.append('session_token')
        
        data = super().to_dict(exclude_fields)
        data['session_duration_seconds'] = self.session_duration.total_seconds()
        
        return data