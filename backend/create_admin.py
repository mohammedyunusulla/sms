#!/usr/bin/env python3
"""
Script to create initial super admin user
"""

import sys
import getpass
from app import create_app, db
from app.models import User, UserRole
from app.utils import validate_email, validate_password

def create_super_admin():
    """Create initial super admin user"""
    
    app = create_app()
    
    with app.app_context():
        print("=" * 50)
        print("  Create Super Admin User")
        print("=" * 50)
        
        # Check if super admin already exists
        existing_admin = User.query.filter_by(role=UserRole.SUPER_ADMIN).first()
        if existing_admin:
            print(f"Super admin already exists: {existing_admin.username}")
            response = input("Do you want to create another super admin? (y/N): ")
            if response.lower() != 'y':
                print("Aborted.")
                return
        
        print("\nEnter super admin details:")
        
        # Get username
        while True:
            username = input("Username: ").strip()
            if not username:
                print("Username is required.")
                continue
            
            if User.get_by_username(username):
                print("Username already exists. Please choose another.")
                continue
            
            break
        
        # Get email
        while True:
            email = input("Email: ").strip()
            if not email:
                print("Email is required.")
                continue
            
            if not validate_email(email):
                print("Invalid email format.")
                continue
            
            if User.get_by_email(email):
                print("Email already exists. Please choose another.")
                continue
            
            break
        
        # Get first name
        while True:
            first_name = input("First Name: ").strip()
            if first_name:
                break
            print("First name is required.")
        
        # Get last name
        while True:
            last_name = input("Last Name: ").strip()
            if last_name:
                break
            print("Last name is required.")
        
        # Get phone (optional)
        phone = input("Phone (optional): ").strip()
        
        # Get password
        while True:
            password = getpass.getpass("Password: ")
            if not password:
                print("Password is required.")
                continue
            
            is_valid, message = validate_password(password)
            if not is_valid:
                print(f"Password validation failed: {message}")
                continue
            
            confirm_password = getpass.getpass("Confirm Password: ")
            if password != confirm_password:
                print("Passwords do not match.")
                continue
            
            break
        
        # Create super admin
        try:
            admin = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone=phone if phone else None,
                role=UserRole.SUPER_ADMIN,
                institution_id=None,  # Super admin doesn't belong to any institution
                institution_user_id=None
            )
            
            admin.set_password(password)
            admin.save()
            
            print("\n" + "=" * 50)
            print("  Super Admin Created Successfully!")
            print("=" * 50)
            print(f"Username: {admin.username}")
            print(f"Email: {admin.email}")
            print(f"Name: {admin.full_name}")
            print(f"Role: {admin.role.value}")
            print(f"ID: {admin.id}")
            print("\nYou can now use these credentials to log in.")
            
        except Exception as e:
            print(f"\nError creating super admin: {str(e)}")
            sys.exit(1)

if __name__ == '__main__':
    create_super_admin()