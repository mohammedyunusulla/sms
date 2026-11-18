# app/models/base.py
from sqlalchemy import Column, Integer, DateTime, Boolean
from datetime import datetime, date, time
from app import db
from sqlalchemy.ext.declarative import declarative_base

# Base class for main database models
class BaseModel(db.Model):
    __abstract__ = True
    
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    def save(self):
        """Save the current instance to database"""
        db.session.add(self)    
        db.session.commit()
        return self
    
    def delete(self):
        """Soft delete by setting is_active to False"""
        self.is_active = False
        db.session.commit()
        return self
    
    def activate(self):
        """Activate the record by setting is_active to True"""
        self.is_active = True
        db.session.commit()
        return self
    
    def to_dict(self, exclude_fields=None):
        """Convert model instance to dictionary"""
        if exclude_fields is None:
            exclude_fields = []

        result = {}
        for column in self.__table__.columns:
            if column.name not in exclude_fields:
                value = getattr(self, column.name)
                if isinstance(value, datetime):
                    result[column.name] = value.isoformat()
                elif isinstance(value, date):
                    result[column.name] = value.isoformat()
                elif isinstance(value, time):
                    result[column.name] = value.strftime('%H:%M')
                elif hasattr(value, 'value'):  # For Enum types
                    result[column.name] = value.value
                else:
                    result[column.name] = value
        return result

    @classmethod
    def get_by_id(cls, id):
        """Get record by id"""
        return cls.query.filter_by(id=id, is_active=True).first()
    
    @classmethod
    def get_all_active(cls):
        """Get all active records"""
        return cls.query.filter_by(is_active=True).all()

# Base class for tenant database models
BaseModelTenant = declarative_base()

class BaseModelTenantMixin:
    """Mixin for tenant models to inherit common methods"""
    def save(self):
        """Save the current instance to database"""
        db.session.add(self)
        db.session.commit()
        return self
    
    def delete(self):
        """Soft delete by setting is_active to False"""
        self.is_active = False
        db.session.commit()
        return self
    
    def to_dict(self, exclude_fields=None):
        """Convert model instance to dictionary"""
        if exclude_fields is None:
            exclude_fields = []

        result = {}
        for column in self.__table__.columns:
            if column.name not in exclude_fields:
                value = getattr(self, column.name)
                if isinstance(value, datetime):
                    result[column.name] = value.isoformat()
                elif isinstance(value, date):
                    result[column.name] = value.isoformat()
                elif isinstance(value, time):
                    result[column.name] = value.strftime('%H:%M')
                elif hasattr(value, 'value'):  # For Enum types
                    result[column.name] = value.value
                else:
                    result[column.name] = value
        return result