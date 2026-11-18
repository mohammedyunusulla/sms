from app.models.main.School import School, SchoolPlan
from app.models.main.User import User, UserRole
from app import db
from app.services.user_service import UserService
from app.utils.db_manager import DatabaseManager
from app.utils.db_name_generator import DatabaseNameGenerator
import re
import logging
from sqlalchemy import and_, or_
import psycopg2
from psycopg2 import sql

logger = logging.getLogger(__name__)

class SchoolService:
    
    @staticmethod
    def create_school(data):
        """Create a new school"""
        try:
             # Generate unique database name
            db_name = DatabaseNameGenerator.generate_db_name(data)
            print("db_name----------", db_name)
            # Validate plan if provided
            plan = data.get('plan', 'BASIC').upper()
            if plan not in [p.value for p in SchoolPlan]:
                return {
                    'success': False,
                    'message': f'Invalid plan. Must be one of: {", ".join([p.value for p in SchoolPlan])}'
                }
            
            
            # Step 1: Create database for school
            try:
                created_db_name  = DatabaseManager.create_school_database(db_name)
                print("created_db_name----------", created_db_name)
            except Exception as db_error:
                logger.error(f"Error creating school database: {str(db_error)}")
                return {
                    'success': False,
                    'message': 'Failed to create dedicated database for school'
                }
            
            # Step 2: Initialize database schema
            try:
                DatabaseManager.initialize_school_schema(created_db_name)
            except Exception as schema_error:
                logger.error(f"Error initializing school schema: {str(schema_error)}")
                # Cleanup: Drop the created database
                DatabaseManager.drop_school_database(created_db_name)
                return {
                    'success': False,
                    'message': 'Failed to initialize database schema'
                }

            # Step 3: Create school entry in the main DB
            school = School(
                name=data['name'].strip(),
                code=data['code'].strip(),
                address=data.get('address', '').strip(),
                phone=data.get('phone', '').strip(),
                email=data.get('email', '').strip(),
                city=data.get('city', '').strip(),
                state=data.get('state', '').strip(),
                country=data.get('country', '').strip(),
                website=data.get('website', '').strip(),
                plan=SchoolPlan(plan),
                skid=created_db_name.replace("skool_", "").strip()
            )
            
            school.save()
            logger.info(f"School created successfully: {school.name} ({school.code})")
            
            return {
                'success': True,
                'message': 'School created successfully',
                'data': school.to_dict()
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating school: {str(e)}")
            DatabaseManager.drop_school_database(created_db_name)
            return {
                'success': False,
                'message': 'Failed to create school'
            }
    
    @staticmethod
    def get_schools():
        """Get list of schools"""
        try:
            schools = School.query.order_by(School.name).all()
            # Convert schools to dict
            schools_data = [school.to_dict() for school in schools]
            
            return {
                'success': True,
                'data': schools_data
            }
            
        except Exception as e:
            logger.error(f"Error getting schools: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to retrieve schools'
            }
    
    @staticmethod
    def get_school_by_id(school_id):
        """Get school by ID"""
        try:
            school = School.query.filter(
                and_(School.id == school_id, School.is_active == True)
            ).first()
            
            if not school:
                return {
                    'success': False,
                    'message': 'School not found'
                }
            
            # Include user count in the response
            school_data = school.to_dict()
            school_data['user_count'] = User.query.filter(
                and_(User.school_id == school_id, User.is_active == True)
            ).count()
            
            return {
                'success': True,
                'data': school_data
            }
            
        except Exception as e:
            logger.error(f"Error getting school {school_id}: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to retrieve school'
            }
    
    @staticmethod
    def update_school(school_id, data):
        """Update school information"""
        try:
            school = School.query.filter(
                and_(School.id == school_id, School.is_active == True)
            ).first()
            
            if not school:
                return {
                    'success': False,
                    'message': 'School not found'
                }
            
            # Update fields if provided
            if 'name' in data:
                school.name = data['name'].strip()
            
            if 'code' in data:
                school.code = data['code'].strip()
            
            if 'address' in data:
                school.address = data['address'].strip()
            
            if 'city' in data:
                school.city = data['city'].strip()
            
            if 'state' in data:
                school.state = data['state'].strip()
            
            if 'country' in data:
                school.country = data['country'].strip()
            
            if 'phone' in data:
                school.phone = data['phone'].strip()
            
            if 'email' in data:
                school.email = data['email'].strip()
            
            if 'website' in data:
                school.website = data['website'].strip()
            
            if 'plan' in data:
                plan = data['plan']
                if plan in [p.value for p in SchoolPlan]:
                    school.plan = SchoolPlan(plan)
                else:
                    return {
                        'success': False,
                        'message': f'Invalid plan. Must be one of: {", ".join([p.value for p in SchoolPlan])}'
                    }
            
            db.session.commit()
            
            logger.info(f"School updated successfully: {school.name} ({school.code})")
            
            return {
                'success': True,
                'message': 'School updated successfully',
                'data': school.to_dict()
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating school {school_id}: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to update school'
            }
    
    @staticmethod
    def delete_school(school_id):
        """Soft delete school"""
        try:
            school = School.query.filter(
                and_(School.id == school_id, School.is_active == True)
            ).first()
            
            if not school:
                return {
                    'success': False,
                    'message': 'School not found'
                }
            
            # Check if school has active users
            active_users_count = User.query.filter(
                and_(User.school_id == school_id, User.is_active == True)
            ).count()
            
            if active_users_count > 0:
                return {
                    'success': False,
                    'message': f'Cannot delete school with {active_users_count} active users. Please deactivate users first.'
                }
            
            # Soft delete
            school.is_active = False
            db.session.commit()
            
            logger.info(f"School soft deleted: {school.name} ({school.code})")
            
            return {
                'success': True,
                'message': 'School deleted successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting school {school_id}: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to delete school'
            }
    
    @staticmethod
    def assign_school_admin(school_id, user_data):
        """Assign or create school admin for a school"""
        try:
            # Check if school exists and is active
            school = School.query.filter(
                and_(School.id == school_id, School.is_active == True)
            ).first()
            
            if not school:
                return {
                    'success': False,
                    'message': 'School not found'
                }
            
            # Check if user already exists
            existing_user = User.query.filter(
                and_(User.email == user_data['email'], User.is_active == True)
            ).first()
            
            if existing_user:
                # If user exists but is not assigned to this school
                if existing_user.school_id != school_id:
                    return {
                        'success': False,
                        'message': 'User with this email already exists in another school'
                    }
                
                # If user exists in this school, update role to school admin
                if existing_user.role != UserRole.SCHOOL_ADMIN:
                    existing_user.role = UserRole.SCHOOL_ADMIN
                    db.session.commit()
                    
                    logger.info(f"User role updated to school admin: {existing_user.email}")
                    
                    return {
                        'success': True,
                        'message': 'User role updated to school admin',
                        'data': existing_user.to_dict()
                    }
                else:
                    return {
                        'success': False,
                        'message': 'User is already a school admin for this school'
                    }
            
            # Create new school admin user
            # Add required fields that might be missing
            if 'username' not in user_data:
                # Generate username from email if not provided
                user_data['username'] = user_data['email'].split('@')[0]
            
            if 'password' not in user_data:
                # Generate a default password (should be changed on first login)
                user_data['password'] = 'TempPass@123'
            
            user_data['role'] = 'school_admin'  # Use string value as per your UserService
            user_data['school_id'] = school_id
            
            # Use your existing UserService.create_user method
            try:
                user = UserService.create_user(user_data)
                
                logger.info(f"School admin created and assigned to school {school.name}: {user_data['email']}")
                return {
                    'success': True,
                    'message': 'School admin created and assigned successfully',
                    'data': user.to_dict()
                }
                
            except ValueError as e:
                return {
                    'success': False,
                    'message': str(e)
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Failed to create school admin: {str(e)}'
                }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error assigning school admin to school {school_id}: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to assign school admin'
            }
    
    @staticmethod
    def get_school_users(school_id, page=1, per_page=10, role=''):
        """Get users for a specific school"""
        try:
            # Check if school exists
            school = School.query.filter(
                and_(School.id == school_id, School.is_active == True)
            ).first()
            
            if not school:
                return {
                    'success': False,
                    'message': 'School not found'
                }
            
            query = User.query.filter(
                and_(User.school_id == school_id, User.is_active == True)
            )
            
            # Apply role filter
            if role and role in [r.value for r in UserRole]:
                query = query.filter(User.role == UserRole(role))
            
            # Get paginated results
            pagination = query.order_by(User.created_at.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
            
            users = [user.to_dict() for user in pagination.items]
            
            return {
                'success': True,
                'data': {
                    'school': school.to_dict(),
                    'users': users,
                    'pagination': {
                        'page': pagination.page,
                        'pages': pagination.pages,
                        'per_page': pagination.per_page,
                        'total': pagination.total,
                        'has_next': pagination.has_next,
                        'has_prev': pagination.has_prev
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting users for school {school_id}: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to retrieve school users'
            }
            
    
    @staticmethod
    def get_super_admin_dashboard_stats():
        """Get system-wide dashboard stats for super admin"""
        try:
            from sqlalchemy import func as sa_func

            # School counts
            total_schools = School.query.count()
            active_schools = School.query.filter(School.is_active == True).count()
            inactive_schools = total_schools - active_schools

            # User counts (from main DB)
            total_users = User.query.count()
            total_super_admins = User.query.filter(User.role == UserRole.SUPER_ADMIN).count()
            total_school_admins = User.query.filter(User.role == UserRole.SCHOOL_ADMIN).count()
            active_users = User.query.filter(User.is_active == True).count()

            # Plan distribution
            plan_distribution = db.session.query(
                School.plan, sa_func.count(School.id)
            ).filter(School.is_active == True).group_by(School.plan).all()
            plan_counts = {plan.value: count for plan, count in plan_distribution}

            # Recent schools (last 5 created)
            recent_schools = School.query.order_by(
                School.created_at.desc()
            ).limit(5).all()
            recent_schools_data = []
            for s in recent_schools:
                sd = s.to_dict()
                sd['user_count'] = User.query.filter(
                    and_(User.school_id == s.id, User.is_active == True)
                ).count()
                recent_schools_data.append(sd)

            # Recent admins (last 5 created)
            recent_admins = User.query.filter(
                User.role == UserRole.SCHOOL_ADMIN
            ).order_by(User.created_at.desc()).limit(5).all()
            recent_admins_data = []
            for admin in recent_admins:
                ad = admin.to_dict()
                recent_admins_data.append(ad)

            return {
                'success': True,
                'data': {
                    'total_schools': total_schools,
                    'active_schools': active_schools,
                    'inactive_schools': inactive_schools,
                    'total_users': total_users,
                    'active_users': active_users,
                    'total_super_admins': total_super_admins,
                    'total_school_admins': total_school_admins,
                    'plan_distribution': {
                        'BASIC': plan_counts.get('BASIC', 0),
                        'STANDARD': plan_counts.get('STANDARD', 0),
                        'PREMIUM': plan_counts.get('PREMIUM', 0),
                    },
                    'recent_schools': recent_schools_data,
                    'recent_admins': recent_admins_data,
                }
            }

        except Exception as e:
            logger.error(f"Error getting super admin dashboard stats: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to retrieve dashboard stats'
            }

    @staticmethod
    def get_school_admins():
        """Get list of all school admins"""
        try:
            # Query users with SCHOOL_ADMIN role
            admins = User.query.filter(
                User.role == UserRole.SCHOOL_ADMIN,
                User.is_active == True
            ).order_by(User.first_name).all()
            
            admins_data = []
            for admin in admins:
                admin_dict = admin.to_dict()
                # Add school details if available
                if admin.school:
                    admin_dict['school_name'] = admin.school.name
                    admin_dict['school_code'] = admin.school.code
                else:
                    admin_dict['school_name'] = 'Not Assigned'
                    admin_dict['school_code'] = '-'
                
                admins_data.append(admin_dict)
            
            return {
                'success': True,
                'data': admins_data
            }
            
        except Exception as e:
            logger.error(f"Error getting school admins: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to retrieve school admins'
            }
    
    
    @staticmethod
    def change_admin_password(admin_id, new_password):
        """Change password for a school admin"""
        try:
            admin = User.query.filter(
                User.id == admin_id,
                User.role == UserRole.SCHOOL_ADMIN
            ).first()
            
            if not admin:
                return {
                    'success': False,
                    'message': 'School admin not found'
                }
            
            # Validate password strength (optional)
            if len(new_password) < 8:
                return {
                    'success': False,
                    'message': 'Password must be at least 8 characters long'
                }
            
            # Update password
            admin.set_password(new_password)
            db.session.commit()
            
            logger.info(f"Password changed for admin: {admin.username} ({admin.email})")
            
            return {
                'success': True,
                'message': 'Password changed successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error changing password for admin {admin_id}: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to change password'
            }


    @staticmethod
    def toggle_school_status(school_id, activate=True):
        """Activate or deactivate school"""
        try:
            school = School.query.filter(School.id == school_id).first()
            
            if not school:
                return {
                    'success': False,
                    'message': 'School not found'
                }
            
            # Update status
            school.is_active = activate
            db.session.commit()
            
            action = "activated" if activate else "deactivated"
            logger.info(f"School {action}: {school.name} ({school.code})")
            
            return {
                'success': True,
                'message': f'School {action} successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error toggling school status {school_id}: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to update school status'
            }
            
   
    @staticmethod
    def hard_delete_school(school_id):
        """Hard delete school - removes users and drops database"""
        try:
            school = School.query.filter(School.id == school_id).first()
            
            if not school:
                return {
                    'success': False,
                    'message': 'School not found'
                }
            
            skid = school.skid
            school_name = school.name
            school_code = school.code
            
            # Step 1: Delete all users associated with this school from main DB
            users_to_delete = User.query.filter(User.school_id == school_id).all()
            user_count = len(users_to_delete)
            
            for user in users_to_delete:
                db.session.delete(user)
            
            # Step 2: Delete the school record
            db.session.delete(school)
            db.session.commit()
            
            logger.info(f"Deleted {user_count} users for school: {school_name} ({school_code})")
            
            # Step 3: Drop the dedicated school database using utility function
            try:
                database_name = f"skool_{skid}"
                DatabaseManager.drop_school_database(database_name)
                logger.info(f"Dropped database: {database_name}")
            except Exception as db_error:
                logger.error(f"Error dropping database {database_name}: {str(db_error)}")
                return {
                    'success': True,
                    'message': f'School deleted but failed to drop database {database_name}. Manual cleanup required.',
                    'warning': str(db_error)
                }
            
            logger.info(f"School hard deleted: {school_name} ({school_code})")
            
            return {
                'success': True,
                'message': f'School deleted successfully. {user_count} users removed and database dropped.'
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error hard deleting school {school_id}: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to delete school'
            }