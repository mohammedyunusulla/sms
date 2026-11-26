from app.utils import features
from app.models.main.Institution import Institution
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

class InstitutionService:
    
    @staticmethod
    def create_institution(data):
        """Create a new institution"""
        created_db_name = None
        try:
            required_fields = ['name', 'code']
            missing = [field for field in required_fields if not (data.get(field) and str(data.get(field)).strip())]
            if missing:
                return {
                    'success': False,
                    'message': f"Missing required fields: {', '.join(missing)}"
                }

            # Generate unique database name
            db_name = DatabaseNameGenerator.generate_db_name(data)
            
            
            # Step 1: Create database for institution
            try:
                created_db_name  = DatabaseManager.create_institution_database(db_name)
            except Exception as db_error:
                logger.error(f"Error creating institution database: {str(db_error)}")
                return {
                    'success': False,
                    'message': 'Failed to create dedicated database for institution'
                }
            
            # Step 2: Initialize database schema
            try:
                DatabaseManager.initialize_institution_schema(created_db_name)
            except Exception as schema_error:
                logger.error(f"Error initializing institution schema: {str(schema_error)}")
                # Cleanup: Drop the created database
                DatabaseManager.drop_institution_database(created_db_name)
                return {
                    'success': False,
                    'message': 'Failed to initialize database schema'
                }

            # Step 3: Create institution entry in the main DB
            institution = Institution(
                name=data['name'].strip(),
                code=data['code'].strip(),
                address=data.get('address', '').strip(),
                phone=data.get('phone', '').strip(),
                email=data.get('email', '').strip(),
                city=data.get('city', '').strip(),
                state=data.get('state', '').strip(),
                country=data.get('country', '').strip(),
                website=data.get('website', '').strip(),
                # nothing optional to start with: the Super Admin switches features on (Features & Logins)
                features=list(features.DEFAULT_FEATURES),
                login_roles=list(features.DEFAULT_LOGIN_ROLES),
                skid=created_db_name.replace("eduspyre_", "").strip()
            )
            
            institution.save()
            logger.info(f"Institution created successfully: {institution.name} ({institution.code})")
            
            return {
                'success': True,
                'message': 'Institution created successfully',
                'data': institution.to_dict()
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating institution: {str(e)}")
            if created_db_name:
                DatabaseManager.drop_institution_database(created_db_name)
            return {
                'success': False,
                'message': 'Failed to create institution'
            }
    
    @staticmethod
    def get_feature_settings(institution_id):
        """The institution's switches plus the catalogue the Super Admin page draws."""
        institution = Institution.query.get(institution_id)
        if not institution:
            return {'success': False, 'message': 'Institution not found'}
        return {'success': True, 'data': {
            'institution': {'id': institution.id, 'name': institution.name, 'code': institution.code, 'skid': institution.skid},
            **features.settings_of(institution),
            'catalogue': features.catalogue(),
        }}

    @staticmethod
    def update_feature_settings(institution_id, data):
        """
        Save the switches. Features are stored with everything they need (Timetable brings Subjects);
        the page asks before turning off something another feature needs, so what arrives is what is wanted.
        """
        institution = Institution.query.get(institution_id)
        if not institution:
            return {'success': False, 'message': 'Institution not found'}
        if 'features' in data:
            if not isinstance(data['features'], list):
                return {'success': False, 'message': 'features must be a list'}
            unknown = [k for k in data['features'] if k not in features.FEATURES]
            if unknown:
                return {'success': False, 'message': f"Unknown feature: {', '.join(map(str, unknown))}"}
            institution.features = features.with_requirements(data['features'])
        if 'login_roles' in data:
            if not isinstance(data['login_roles'], list):
                return {'success': False, 'message': 'login_roles must be a list'}
            unknown = [r for r in data['login_roles'] if str(r).upper() not in features.LOGIN_ROLES]
            if unknown:
                return {'success': False, 'message': f"Unknown role: {', '.join(map(str, unknown))}"}
            institution.login_roles = features.clean_login_roles(data['login_roles'])
        db.session.commit()
        features.forget(institution.skid)
        logger.info(f"Feature switches updated for {institution.name}: {institution.features} / {institution.login_roles}")
        return {'success': True, 'message': 'Saved', 'data': features.settings_of(institution)}

    @staticmethod
    def get_institutions():
        """Get list of institutions"""
        try:
            institutions = Institution.query.order_by(Institution.name).all()
            # Convert institutions to dict
            institutions_data = [institution.to_dict() for institution in institutions]
            
            return {
                'success': True,
                'data': institutions_data
            }
            
        except Exception as e:
            logger.error(f"Error getting institutions: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to retrieve institutions'
            }
    
    @staticmethod
    def get_institution_by_id(institution_id):
        """Get institution by ID"""
        try:
            institution = Institution.query.filter(
                and_(Institution.id == institution_id, Institution.is_active == True)
            ).first()
            
            if not institution:
                return {
                    'success': False,
                    'message': 'Institution not found'
                }
            
            # Include user count in the response
            institution_data = institution.to_dict()
            institution_data['user_count'] = User.query.filter(
                and_(User.institution_id == institution_id, User.is_active == True)
            ).count()
            
            return {
                'success': True,
                'data': institution_data
            }
            
        except Exception as e:
            logger.error(f"Error getting institution {institution_id}: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to retrieve institution'
            }
    
    @staticmethod
    def update_institution(institution_id, data):
        """Update institution information"""
        try:
            institution = Institution.query.filter(
                and_(Institution.id == institution_id, Institution.is_active == True)
            ).first()
            
            if not institution:
                return {
                    'success': False,
                    'message': 'Institution not found'
                }
            
            # Update fields if provided
            if 'name' in data:
                institution.name = data['name'].strip()
            
            if 'code' in data:
                institution.code = data['code'].strip()
            
            if 'address' in data:
                institution.address = data['address'].strip()
            
            if 'city' in data:
                institution.city = data['city'].strip()
            
            if 'state' in data:
                institution.state = data['state'].strip()
            
            if 'country' in data:
                institution.country = data['country'].strip()
            
            if 'phone' in data:
                institution.phone = data['phone'].strip()
            
            if 'email' in data:
                institution.email = data['email'].strip()
            
            if 'website' in data:
                institution.website = data['website'].strip()
            
            db.session.commit()
            
            logger.info(f"Institution updated successfully: {institution.name} ({institution.code})")
            
            return {
                'success': True,
                'message': 'Institution updated successfully',
                'data': institution.to_dict()
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating institution {institution_id}: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to update institution'
            }
    
    @staticmethod
    def delete_institution(institution_id):
        """Soft delete institution"""
        try:
            institution = Institution.query.filter(
                and_(Institution.id == institution_id, Institution.is_active == True)
            ).first()
            
            if not institution:
                return {
                    'success': False,
                    'message': 'Institution not found'
                }
            
            # Check if institution has active users
            active_users_count = User.query.filter(
                and_(User.institution_id == institution_id, User.is_active == True)
            ).count()
            
            if active_users_count > 0:
                return {
                    'success': False,
                    'message': f'Cannot delete institution with {active_users_count} active users. Please deactivate users first.'
                }
            
            # Soft delete
            institution.is_active = False
            db.session.commit()
            
            logger.info(f"Institution soft deleted: {institution.name} ({institution.code})")
            
            return {
                'success': True,
                'message': 'Institution deleted successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting institution {institution_id}: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to delete institution'
            }
    
    @staticmethod
    def assign_institution_admin(institution_id, user_data):
        """Assign or create institution admin for an institution"""
        try:
            # Check if institution exists and is active
            institution = Institution.query.filter(
                and_(Institution.id == institution_id, Institution.is_active == True)
            ).first()
            
            if not institution:
                return {
                    'success': False,
                    'message': 'Institution not found'
                }
            
            # Check if user already exists
            existing_user = User.query.filter(
                and_(User.email == user_data['email'], User.is_active == True)
            ).first()
            
            if existing_user:
                # If user exists but is not assigned to this institution
                if existing_user.institution_id != institution_id:
                    return {
                        'success': False,
                        'message': 'User with this email already exists in another institution'
                    }
                
                # If user exists in this institution, update role to institution admin
                if existing_user.role != UserRole.INSTITUTION_ADMIN:
                    existing_user.role = UserRole.INSTITUTION_ADMIN
                    db.session.commit()
                    
                    logger.info(f"User role updated to institution admin: {existing_user.email}")
                    
                    return {
                        'success': True,
                        'message': 'User role updated to institution admin',
                        'data': existing_user.to_dict()
                    }
                else:
                    return {
                        'success': False,
                        'message': 'User is already an institution admin for this institution'
                    }
            
            # Create new institution admin user
            # Add required fields that might be missing
            if 'username' not in user_data:
                # Generate username from email if not provided
                user_data['username'] = user_data['email'].split('@')[0]
            
            if 'password' not in user_data:
                # Generate a default password (should be changed on first login)
                user_data['password'] = 'TempPass@123'
            
            user_data['role'] = 'institution_admin'  # Use string value as per your UserService
            user_data['institution_id'] = institution_id
            
            # Use your existing UserService.create_user method
            try:
                user = UserService.create_user(user_data)
                
                logger.info(f"Institution admin created and assigned to institution {institution.name}: {user_data['email']}")
                return {
                    'success': True,
                    'message': 'Institution admin created and assigned successfully',
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
                    'message': f'Failed to create institution admin: {str(e)}'
                }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error assigning institution admin to institution {institution_id}: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to assign institution admin'
            }
    
    @staticmethod
    def get_institution_users(institution_id, page=1, per_page=10, role=''):
        """Get users for a specific institution"""
        try:
            # Check if institution exists
            institution = Institution.query.filter(
                and_(Institution.id == institution_id, Institution.is_active == True)
            ).first()
            
            if not institution:
                return {
                    'success': False,
                    'message': 'Institution not found'
                }
            
            query = User.query.filter(
                and_(User.institution_id == institution_id, User.is_active == True)
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
                    'institution': institution.to_dict(),
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
            logger.error(f"Error getting users for institution {institution_id}: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to retrieve institution users'
            }
            
    
    @staticmethod
    def get_super_admin_dashboard_stats():
        """Get system-wide dashboard stats for super admin"""
        try:
            from sqlalchemy import func as sa_func

            # Institution counts
            total_institutions = Institution.query.count()
            active_institutions = Institution.query.filter(Institution.is_active == True).count()
            inactive_institutions = total_institutions - active_institutions

            # User counts (from main DB)
            total_users = User.query.count()
            total_super_admins = User.query.filter(User.role == UserRole.SUPER_ADMIN).count()
            total_institution_admins = User.query.filter(User.role == UserRole.INSTITUTION_ADMIN).count()
            active_users = User.query.filter(User.is_active == True).count()

            # How many active institutions use each feature
            feature_counts = {key: 0 for key in features.ALL_FEATURES}
            for row in Institution.query.filter(Institution.is_active == True).all():
                for key in features.settings_of(row)['features']:
                    feature_counts[key] += 1

            # Recent institutions (last 5 created)
            recent_institutions = Institution.query.order_by(
                Institution.created_at.desc()
            ).limit(5).all()
            recent_institutions_data = []
            for s in recent_institutions:
                sd = s.to_dict()
                sd['user_count'] = User.query.filter(
                    and_(User.institution_id == s.id, User.is_active == True)
                ).count()
                recent_institutions_data.append(sd)

            # Recent admins (last 5 created)
            recent_admins = User.query.filter(
                User.role == UserRole.INSTITUTION_ADMIN
            ).order_by(User.created_at.desc()).limit(5).all()
            recent_admins_data = []
            for admin in recent_admins:
                ad = admin.to_dict()
                recent_admins_data.append(ad)

            return {
                'success': True,
                'data': {
                    'total_institutions': total_institutions,
                    'active_institutions': active_institutions,
                    'inactive_institutions': inactive_institutions,
                    'total_users': total_users,
                    'active_users': active_users,
                    'total_super_admins': total_super_admins,
                    'total_institution_admins': total_institution_admins,
                    'feature_usage': [
                        {'key': key, 'label': features.feature_label(key), 'institutions': feature_counts[key]}
                        for key in features.ALL_FEATURES
                    ],
                    'recent_institutions': recent_institutions_data,
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
    def get_institution_admins():
        """Get list of all institution admins"""
        try:
            # Query users with INSTITUTION_ADMIN role
            # Active and inactive (deleted) admins, so a deleted admin can be reactivated here
            admins = User.query.filter(
                User.role == UserRole.INSTITUTION_ADMIN,
            ).order_by(User.is_active.desc(), User.first_name).all()
            
            admins_data = []
            for admin in admins:
                admin_dict = admin.to_dict()
                # Add institution details if available
                if admin.institution:
                    admin_dict['institution_name'] = admin.institution.name
                    admin_dict['institution_code'] = admin.institution.code
                else:
                    admin_dict['institution_name'] = 'Not Assigned'
                    admin_dict['institution_code'] = '-'
                
                admins_data.append(admin_dict)
            
            return {
                'success': True,
                'data': admins_data
            }
            
        except Exception as e:
            logger.error(f"Error getting institution admins: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to retrieve institution admins'
            }
    
    
    @staticmethod
    def change_admin_password(admin_id, new_password):
        """Change password for an institution admin"""
        try:
            admin = User.query.filter(
                User.id == admin_id,
                User.role == UserRole.INSTITUTION_ADMIN
            ).first()
            
            if not admin:
                return {
                    'success': False,
                    'message': 'Institution admin not found'
                }
            
            # Same password rule as every other account
            from app.utils.helpers import validate_password
            ok, problem = validate_password(new_password or '')
            if not ok:
                return {
                    'success': False,
                    'message': problem
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
    def toggle_institution_status(institution_id, activate=True):
        """Activate or deactivate institution"""
        try:
            institution = Institution.query.filter(Institution.id == institution_id).first()
            
            if not institution:
                return {
                    'success': False,
                    'message': 'Institution not found'
                }
            
            # Update status
            institution.is_active = activate
            db.session.commit()
            
            action = "activated" if activate else "deactivated"
            logger.info(f"Institution {action}: {institution.name} ({institution.code})")
            
            return {
                'success': True,
                'message': f'Institution {action} successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error toggling institution status {institution_id}: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to update institution status'
            }
            
   
    @staticmethod
    def hard_delete_institution(institution_id):
        """Hard delete institution - removes users and drops database"""
        try:
            institution = Institution.query.filter(Institution.id == institution_id).first()
            
            if not institution:
                return {
                    'success': False,
                    'message': 'Institution not found'
                }
            
            skid = institution.skid
            institution_name = institution.name
            institution_code = institution.code
            
            # Step 1: Delete all users associated with this institution from main DB
            users_to_delete = User.query.filter(User.institution_id == institution_id).all()
            user_count = len(users_to_delete)
            
            for user in users_to_delete:
                db.session.delete(user)
            
            # Step 2: Delete the institution record
            db.session.delete(institution)
            db.session.commit()
            
            logger.info(f"Deleted {user_count} users for institution: {institution_name} ({institution_code})")
            
            # Step 3: Drop the dedicated institution database using utility function
            try:
                database_name = f"eduspyre_{skid}"
                DatabaseManager.drop_institution_database(database_name)
                logger.info(f"Dropped database: {database_name}")
            except Exception as db_error:
                logger.error(f"Error dropping database {database_name}: {str(db_error)}")
                return {
                    'success': True,
                    'message': f'Institution deleted but failed to drop database {database_name}. Manual cleanup required.',
                    'warning': str(db_error)
                }
            
            logger.info(f"Institution hard deleted: {institution_name} ({institution_code})")
            
            return {
                'success': True,
                'message': f'Institution deleted successfully. {user_count} users removed and database dropped.'
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error hard deleting institution {institution_id}: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to delete institution'
            }