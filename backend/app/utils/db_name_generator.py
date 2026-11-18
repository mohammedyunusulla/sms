import re
import uuid
import secrets
from datetime import datetime
from app.models.main.School import School

class DatabaseNameGenerator:
    @staticmethod
    def generate_db_name(school_data):
        """
        Generate a unique database name for a school
        """
        # Add random suffix to ensure uniqueness
        random_suffix = secrets.token_hex(8)

        # Database name format: skool_{random_suffix}
        db_name = f"skool_{random_suffix}"
        
        return db_name
    
    @staticmethod
    def _clean_string(text):
        """Clean string for database naming"""
        # Remove special characters, keep only alphanumeric
        cleaned = re.sub(r'[^a-zA-Z0-9]', '', text.lower())
        # Limit length to 20 characters
        return cleaned[:20] if cleaned else ''
    
    @staticmethod
    def _ensure_unique_name(base_name):
        """Ensure database name is unique by checking existing schools"""
        # Check if name already exists
        existing_school = School.query.filter_by(skid=base_name).first()
        
        if not existing_school:
            return base_name
        
        # If exists, append counter
        counter = 1
        while True:
            new_name = f"{base_name}_{counter}"
            existing = School.query.filter_by(skid=new_name).first()
            if not existing:
                return new_name
            counter += 1
