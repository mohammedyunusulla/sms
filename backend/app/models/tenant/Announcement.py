from app.models.base import BaseModelTenant, BaseModelTenantMixin
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

class Announcement(BaseModelTenant, BaseModelTenantMixin):
    """Main Announcement/Announcement table"""
    __tablename__ = 'announcements'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    academic_year_id = Column(Integer, ForeignKey('academic_years.id'), nullable=False)
    
    # Content
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    announcement_type = Column(String(50), nullable=False)
    priority = Column(String(50), default='NORMAL')
    
    # Targeting
    target_audience = Column(String(50), nullable=False)
    target_classes = Column(JSON)
    target_sections = Column(JSON)
    target_users = Column(JSON)
    
    # Attachments
    attachments = Column(JSON)
    
    # Publishing
    is_published = Column(Boolean, default=False)
    publish_date = Column(DateTime)
    expiry_date = Column(DateTime)
    
    # Metadata
    created_by = Column(Integer, ForeignKey('institution_users.id'), nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    academic_year = relationship("AcademicYear")
    
    def to_dict(self):
        return {
            'id': self.id,
            'academic_year_id': self.academic_year_id,
            'title': self.title,
            'description': self.description,
            'announcement_type': self.announcement_type,
            'priority': self.priority,
            'target_audience': self.target_audience,
            'target_classes': self.target_classes,
            'target_sections': self.target_sections,
            'target_users': self.target_users,
            'attachments': self.attachments,
            'is_published': self.is_published,
            'publish_date': self.publish_date.isoformat() if self.publish_date else None,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'created_by': self.created_by,
            'is_active': self.is_active,
            # stored in UTC: marked as such so browsers show local time ("Posted on" showed UTC - QA C18)
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None
        }
