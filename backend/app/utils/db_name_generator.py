import re
import uuid
import secrets
from datetime import datetime
from app.models.main.Institution import Institution

class DatabaseNameGenerator:
    @staticmethod
    def generate_db_name(institution_data):
        """
        Generate a unique database name for an institution
        """
        # Add random suffix to ensure uniqueness
        random_suffix = secrets.token_hex(8)

        # Database name format: eduspyre_{random_suffix}
        db_name = f"eduspyre_{random_suffix}"
        
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
        """Ensure database name is unique by checking existing institutions"""
        # Check if name already exists
        existing_institution = Institution.query.filter_by(skid=base_name).first()
        
        if not existing_institution:
            return base_name
        
        # If exists, append counter
        counter = 1
        while True:
            new_name = f"{base_name}_{counter}"
            existing = Institution.query.filter_by(skid=new_name).first()
            if not existing:
                return new_name
            counter += 1
