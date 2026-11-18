from app.models.main.User import User, UserRole
from app.models.main.School import School
from app.models.tenant import Student, Teacher, SchoolUsers, SchoolAdmin
from app.models.tenant.Roles import Role
from app import db
from sqlalchemy.exc import IntegrityError
from flask import jsonify
from app.utils.db_manager import switch_to_school_db
from app.utils.helpers import generate_student_id

class UserService:

    @staticmethod
    def create_school_admin(data):
        try:
            required_fields = ['username', 'email', 'password', 'first_name', 'last_name', 'skid', 'school_id']
            for field in required_fields:
                if not data.get(field):
                    raise ValueError(f"Missing required field: {field}")
            
            skid = data['skid']
            
            # Validate uniqueness
            if User.get_by_username(data['username']):
                raise ValueError("Username already exists")
            if User.get_by_email(data['email']):
                raise ValueError("Email already exists")

            school = School.query.get(data['school_id'])
            if not school:
                raise ValueError("Invalid school_id")

            # Create in main users table
            user = User(
                username=data['username'],
                email=data['email'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                phone=data.get('phone'),
                role=UserRole.SCHOOL_ADMIN,
                skid=skid,
                school_id=school.id
            )
            user.set_password(data['password'])
            user.save()

            # Set this user as admin of the school
            school.school_admin_id = user.id
            db.session.commit()

            # Create in tenant DB: school_users and school_admins
            with switch_to_school_db(skid) as session:
                school_user = SchoolUsers(
                    username=data['username'],
                    email=data['email'],
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    skid=skid,
                    is_active=True
                )
                session.add(school_user)
                session.flush()

                school_admin_profile = SchoolAdmin(
                    user_id=school_user.id,
                    designation=str(data.get('designation', UserRole.SCHOOL_ADMIN))
                )
                session.add(school_admin_profile)
                session.commit()

                # Link back school_user_id to main DB
                user.school_user_id = school_user.id
                db.session.commit()

            return user

        except Exception as e:
            db.session.rollback()
            raise Exception(f"Failed to create school admin: {str(e)}")

    
    @staticmethod
    def create_school_user(data):
        try:
            required_fields = ['username', 'email', 'password', 'first_name', 'last_name', 'role', 'skid', 'school_id']
            for field in required_fields:
                if not data.get(field):
                    raise ValueError(f"Missing required field: {field}")
            
            skid = data['skid']
            
            if data['role'] not in ['TEACHER', 'STUDENT', 'PARENT', 'STAFF']:
                raise ValueError("Invalid school user role")

            school = School.query.get(data['school_id'])
            if not school:
                raise ValueError("Invalid school_id")

            # Create in main DB
            user = User(
                username=data['username'],
                email=data['email'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                phone=data.get('phone'),
                role=UserRole(data['role']),
                skid=skid,
                school_id=school.id
            )
            user.set_password(data['password'])
            user.save()

            # Insert into tenant DB
            with switch_to_school_db(skid) as tenant_session:
                school_user = SchoolUsers(
                    username=data['username'],
                    email=data['email'],
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    phone_number=data.get('phone'),
                    skid=skid,
                    is_active=True
                )
                tenant_session.add(school_user)
                tenant_session.flush()

                # Create respective profile
                if user.role == UserRole.TEACHER:
                    profile = Teacher(
                        user_id=school_user.id,
                        employee_id=data.get('employee_id'),
                        designation=data.get('designation'),
                        date_of_joining=data.get('date_of_joining'),
                        qualifications=data.get('qualifications'),
                        salary=data.get('salary')
                    )
                elif user.role == UserRole.STUDENT:
                    profile = Student(
                        user_id=school_user.id,
                        student_id=data.get('student_id'),
                        admission_date=data.get('admission_date'),
                        class_id=data.get('class_id'),
                        section_id=data.get('section_id')
                    )
                else:
                    raise ValueError("Only teacher/student logic implemented. Add parent/staff if needed.")

                tenant_session.add(profile)
                tenant_session.commit()

                user.school_user_id = school_user.id
                db.session.commit()

            return user

        except Exception as e:
            db.session.rollback()
            raise Exception(f"Failed to create school user: {str(e)}")

    
    @staticmethod
    def update_user(user_id, user_data):
        """
        Update existing user
        """
        try:
            user = User.get_by_id(user_id)
            if not user:
                raise ValueError("User not found")
            
            # Update fields if provided
            updatable_fields = ['email', 'first_name', 'last_name', 'phone', 'role', 'school_id']
            
            for field in updatable_fields:
                if field in user_data:
                    if field == 'email':
                        # Check if email is already taken by another user
                        existing_user = User.get_by_email(user_data['email'])
                        if existing_user and existing_user.id != user.id:
                            raise ValueError("Email already exists")
                    
                    elif field == 'role':
                        # Validate role
                        try:
                            role = UserRole(user_data['role'])
                            setattr(user, field, role)
                        except ValueError:
                            raise ValueError("Invalid role")
                        continue
                    
                    elif field == 'school_id':
                        # Validate school
                        if user_data['school_id']:
                            school = School.get_by_id(user_data['school_id'])
                            if not school:
                                raise ValueError("Invalid school_id")
                    
                    setattr(user, field, user_data[field])
            
            # Update password if provided
            if 'password' in user_data and user_data['password']:
                user.set_password(user_data['password'])
            
            user.save()
            return user
            
        except IntegrityError as e:
            db.session.rollback()
            raise ValueError("Email already exists")
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Failed to update user: {str(e)}")
    
    @staticmethod
    def deactivate_user(user_id):
        """
        Deactivate user (soft delete)
        """
        try:
            user = User.get_by_id(user_id)
            if not user:
                raise ValueError("User not found")
            
            user.delete()  # This sets is_active to False
            return user
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Failed to deactivate user: {str(e)}")
    
    @staticmethod
    def activate_user(user_id):
        """
        Activate user
        """
        try:
            # Get user even if inactive
            user = User.query.filter_by(id=user_id).first()
            if not user:
                raise ValueError("User not found")
            
            user.activate()
            return user
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Failed to activate user: {str(e)}")
    
    @staticmethod
    def get_users_by_school(skid, page=1, limit=10, search='', gender='', role='', status=''):
        """
        Get paginated users for a specific school with filtering and sorting
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Build base query
                query = tenant_session.query(SchoolUsers).join(Role, SchoolUsers.role_id == Role.id)

                # Filter by status (active/inactive)
                if status.lower() == 'active':
                    query = query.filter(SchoolUsers.is_active == True)
                elif status.lower() == 'inactive':
                    query = query.filter(SchoolUsers.is_active == False)
                else:
                    query = query.filter(SchoolUsers.is_active == True)  # Default to active

                # Filter by gender
                if gender:
                    query = query.filter(SchoolUsers.gender == gender)

                # Filter by role
                if role:
                    # Convert role string to match role_code in database
                    role_upper = role.upper()
                    query = query.filter(Role.role_code == role_upper)

                # Filter by search term (searches in name, email, phone)
                if search:
                    search_term = f"%{search}%"
                    query = query.filter(
                        (SchoolUsers.first_name.ilike(search_term)) |
                        (SchoolUsers.last_name.ilike(search_term)) |
                        (SchoolUsers.email.ilike(search_term)) |
                        (SchoolUsers.phone.ilike(search_term))
                    )

                # Get total count before pagination
                total = query.count()

                # Calculate pagination
                offset = (page - 1) * limit
                total_pages = (total + limit - 1) // limit

                # Order by name and apply pagination
                users = query.order_by(
                    SchoolUsers.first_name,
                    SchoolUsers.last_name
                ).offset(offset).limit(limit).all()

                users_data = [user.to_dict() for user in users]

            # Enrich with login info from main DB (outside tenant session)
            school_user_ids = [u['id'] for u in users_data]
            if school_user_ids:
                main_users = User.query.filter(
                    User.school_user_id.in_(school_user_ids),
                    User.skid == skid
                ).all()
                # Map school_user_id -> main User
                main_user_map = {mu.school_user_id: mu for mu in main_users}
                for u in users_data:
                    main_user = main_user_map.get(u['id'])
                    u['has_login'] = main_user is not None
                    u['main_user_id'] = main_user.id if main_user else None
                    u['login_active'] = main_user.is_active if main_user else False

            return {
                'users': users_data,
                'total': total,
                'page': page,
                'limit': limit,
                'totalPages': total_pages
            }
        except Exception as e:
            raise Exception(f"Failed to get users: {str(e)}")

    @staticmethod
    def get_staff_by_school(skid):
        """
        Get all staff users with role information (excludes School Admin, Student, Parent)
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Define roles to exclude
                excluded_role_codes = ['SCHOOL_ADMIN', 'STUDENT', 'PARENT']
                
                users = (
                    tenant_session.query(SchoolUsers)
                    .join(Role, SchoolUsers.role_id == Role.id)
                    .filter(
                        SchoolUsers.is_active == True,
                        Role.role_code.notin_(excluded_role_codes)
                    )
                    .order_by(SchoolUsers.first_name, SchoolUsers.last_name)
                    .all()
                )
                
                return [
                    {
                        **user.to_dict()
                    }
                    for user in users
                ]
        except Exception as e:
            raise Exception(f"Failed to get staff: {str(e)}")
    
    @staticmethod
    def get_user_by_id(user_id, include_inactive=False):
        """
        Get user by ID
        """
        try:
            if include_inactive:
                user = User.query.filter_by(id=user_id).first()
            else:
                user = User.get_by_id(user_id)
            
            return user
            
        except Exception as e:
            raise Exception(f"Failed to get user: {str(e)}")
    
    @staticmethod
    def get_super_admins():
        """Get list of all super admin users"""
        try:
            admins = User.query.filter(
                User.role == UserRole.SUPER_ADMIN
            ).order_by(User.created_at.desc()).all()
            return [admin.to_dict() for admin in admins]
        except Exception as e:
            raise Exception(f"Failed to get super admins: {str(e)}")

    @staticmethod
    def create_super_admin(data):
        """Create a new super admin user"""
        try:
            username = data.get('username', '').strip()
            email = data.get('email', '').strip()
            password = data.get('password', '')

            if not password:
                raise ValueError("Password is required")
            if len(password) < 8:
                raise ValueError("Password must be at least 8 characters")
            if not username and not email:
                raise ValueError("Either username or email is required")

            # Auto-generate username from email if not provided
            if not username and email:
                username = email.split('@')[0]
            # Auto-generate email placeholder if not provided
            if not email and username:
                email = f"{username}@system.local"

            # Validate uniqueness
            if User.get_by_username(username):
                raise ValueError("Username already exists")
            if User.get_by_email(email):
                raise ValueError("Email already exists")

            admin = User(
                username=username,
                email=email,
                first_name=data.get('first_name', username),
                last_name=data.get('last_name', ''),
                phone=data.get('phone'),
                role=UserRole.SUPER_ADMIN,
                school_id=None,
                school_user_id=None
            )
            admin.set_password(password)
            admin.save()

            return admin
        except ValueError:
            raise
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Failed to create super admin: {str(e)}")

    @staticmethod
    def change_password(user_id, old_password, new_password):
        """
        Change user password with strength validation.
        """
        try:
            from app.utils.security import validate_password_strength

            user = User.get_by_id(user_id)
            if not user:
                raise ValueError("User not found")

            if not user.check_password(old_password):
                raise ValueError("Invalid current password")

            # Validate new password strength
            is_valid, error_msg = validate_password_strength(new_password)
            if not is_valid:
                raise ValueError(error_msg)

            user.set_password(new_password)
            user.save()

            return user

        except ValueError:
            raise
        except Exception as e:
            db.session.rollback()
            raise Exception("Failed to change password")

    @staticmethod
    def provision_single_login(school_user_id, skid, school_id, password):
        """
        Create a login (User record in main DB) for an existing SchoolUsers record.
        Used when upgrading from BASIC plan or manually granting login access.
        """
        try:
            if not password or len(password) < 8:
                raise ValueError("Password must be at least 8 characters")

            # Check if already provisioned
            existing = User.query.filter_by(school_user_id=school_user_id, skid=skid).first()
            if existing:
                raise ValueError("User already has login access")

            # Get school for school_code
            school = School.query.get(school_id)
            if not school:
                raise ValueError("Invalid school_id")

            # Read SchoolUsers + role from tenant DB
            with switch_to_school_db(skid) as tenant_session:
                school_user = tenant_session.query(SchoolUsers).filter_by(id=school_user_id).first()
                if not school_user:
                    raise ValueError("School user not found")
                if not school_user.is_active:
                    raise ValueError("School user is inactive")

                # Get role code
                role_obj = tenant_session.query(Role).filter_by(id=school_user.role_id).first()
                role_code = role_obj.role_code if role_obj else None

                if role_code not in ('STUDENT', 'PARENT'):
                    raise ValueError("Only STUDENT and PARENT users can be provisioned this way")

                # Extract user data while session is open
                user_data = {
                    'username': school_user.username,
                    'email': school_user.email,
                    'first_name': school_user.first_name,
                    'last_name': school_user.last_name,
                    'phone': school_user.phone,
                    'role_code': role_code,
                    'school_user_id': school_user.id,
                }

            # Validate required fields
            if not user_data['username']:
                raise ValueError("Missing required field: username")
            if not user_data['email']:
                raise ValueError("Missing required field: email")
            if not user_data['first_name']:
                raise ValueError("Missing required field: first_name")

            # Check username uniqueness - append school_code if conflict
            username = user_data['username']
            if User.query.filter_by(username=username).first():
                username = f"{username}_{school.code}"
                if User.query.filter_by(username=username).first():
                    raise ValueError(f"Username '{user_data['username']}' already exists even with school code suffix")

            # Check email uniqueness
            if User.query.filter_by(email=user_data['email']).first():
                raise ValueError(f"Email '{user_data['email']}' is already registered in another school")

            # Create User record in main DB
            user = User(
                username=username,
                email=user_data['email'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                phone=user_data['phone'],
                role=UserRole(user_data['role_code']),
                skid=skid,
                school_id=school_id,
                school_user_id=user_data['school_user_id']
            )
            user.set_password(password)
            user.save()

            return user

        except ValueError:
            raise
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Failed to provision login: {str(e)}")

    @staticmethod
    def provision_bulk_logins(skid, school_id, default_password, role_filter=None):
        """
        Bulk create logins for STUDENT/PARENT SchoolUsers who don't have User records.
        Returns a detailed report of results.
        """
        try:
            if not default_password or len(default_password) < 8:
                raise ValueError("Default password must be at least 8 characters")

            # Get school for school_code
            school = School.query.get(school_id)
            if not school:
                raise ValueError("Invalid school_id")

            # Read eligible SchoolUsers from tenant DB
            with switch_to_school_db(skid) as tenant_session:
                query = tenant_session.query(SchoolUsers).join(Role, SchoolUsers.role_id == Role.id)

                # Filter to STUDENT/PARENT roles
                eligible_roles = ['STUDENT', 'PARENT']
                if role_filter and role_filter.upper() in eligible_roles:
                    query = query.filter(Role.role_code == role_filter.upper())
                else:
                    query = query.filter(Role.role_code.in_(eligible_roles))

                query = query.filter(SchoolUsers.is_active == True)
                all_school_users = query.all()

                # Collect user data while session is open
                school_users_data = []
                for su in all_school_users:
                    role_obj = tenant_session.query(Role).filter_by(id=su.role_id).first()
                    school_users_data.append({
                        'id': su.id,
                        'username': su.username,
                        'email': su.email,
                        'first_name': su.first_name,
                        'last_name': su.last_name,
                        'phone': su.phone,
                        'full_name': su.full_name,
                        'role_code': role_obj.role_code if role_obj else None,
                        'role_name': role_obj.role_name if role_obj else None,
                    })

            total_eligible = len(school_users_data)

            # Find which ones already have a User record
            school_user_ids = [su['id'] for su in school_users_data]
            existing_users = User.query.filter(
                User.school_user_id.in_(school_user_ids),
                User.skid == skid
            ).all() if school_user_ids else []
            already_provisioned_ids = {u.school_user_id for u in existing_users}

            # Pre-fetch all existing usernames and emails for conflict checking
            existing_usernames = {u.username for u in User.query.with_entities(User.username).all()}
            existing_emails = {u.email for u in User.query.with_entities(User.email).all()}

            success_count = 0
            failed_count = 0
            already_provisioned = len(already_provisioned_ids)
            failures = []
            successes = []

            for su_data in school_users_data:
                # Skip already provisioned
                if su_data['id'] in already_provisioned_ids:
                    continue

                # Validate required fields
                missing_fields = []
                if not su_data['username']:
                    missing_fields.append('username')
                if not su_data['email']:
                    missing_fields.append('email')
                if not su_data['first_name']:
                    missing_fields.append('first_name')

                if missing_fields:
                    failed_count += 1
                    failures.append({
                        'school_user_id': su_data['id'],
                        'name': su_data['full_name'],
                        'role': su_data['role_name'],
                        'reason': f"Missing required fields: {', '.join(missing_fields)}"
                    })
                    continue

                # Check username uniqueness
                username = su_data['username']
                if username in existing_usernames:
                    username = f"{username}_{school.code}"
                    if username in existing_usernames:
                        failed_count += 1
                        failures.append({
                            'school_user_id': su_data['id'],
                            'name': su_data['full_name'],
                            'role': su_data['role_name'],
                            'reason': f"Username '{su_data['username']}' conflict even with school code suffix"
                        })
                        continue

                # Check email uniqueness
                if su_data['email'] in existing_emails:
                    failed_count += 1
                    failures.append({
                        'school_user_id': su_data['id'],
                        'name': su_data['full_name'],
                        'role': su_data['role_name'],
                        'reason': f"Email '{su_data['email']}' already registered in another school"
                    })
                    continue

                # Create User record
                try:
                    user = User(
                        username=username,
                        email=su_data['email'],
                        first_name=su_data['first_name'],
                        last_name=su_data['last_name'],
                        phone=su_data['phone'],
                        role=UserRole(su_data['role_code']),
                        skid=skid,
                        school_id=school_id,
                        school_user_id=su_data['id']
                    )
                    user.set_password(default_password)
                    db.session.add(user)
                    db.session.flush()

                    # Track in sets to prevent duplicates within this batch
                    existing_usernames.add(username)
                    existing_emails.add(su_data['email'])

                    success_count += 1
                    successes.append({
                        'school_user_id': su_data['id'],
                        'name': su_data['full_name'],
                        'role': su_data['role_name'],
                        'username': username,
                        'email': su_data['email'],
                    })
                except Exception as e:
                    failed_count += 1
                    failures.append({
                        'school_user_id': su_data['id'],
                        'name': su_data['full_name'],
                        'role': su_data['role_name'],
                        'reason': str(e)
                    })

            # Commit all successful records
            db.session.commit()

            return {
                'total_eligible': total_eligible,
                'already_provisioned': already_provisioned,
                'success_count': success_count,
                'failed_count': failed_count,
                'successes': successes,
                'failures': failures
            }

        except ValueError:
            raise
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Failed to provision bulk logins: {str(e)}")

    @staticmethod
    def get_provisioning_report(skid, school_id):
        """
        Get a full report of all users in a school with their login status.
        Used for export after provisioning.
        """
        try:
            # Get school info
            school = School.query.get(school_id)
            if not school:
                raise ValueError("Invalid school_id")

            # Read all SchoolUsers from tenant DB
            with switch_to_school_db(skid) as tenant_session:
                all_users = (
                    tenant_session.query(SchoolUsers)
                    .join(Role, SchoolUsers.role_id == Role.id)
                    .filter(SchoolUsers.is_active == True)
                    .order_by(Role.role_code, SchoolUsers.first_name, SchoolUsers.last_name)
                    .all()
                )

                users_data = []
                for u in all_users:
                    role_obj = tenant_session.query(Role).filter_by(id=u.role_id).first()
                    users_data.append({
                        'school_user_id': u.id,
                        'username': u.username,
                        'email': u.email,
                        'first_name': u.first_name,
                        'last_name': u.last_name,
                        'full_name': u.full_name,
                        'phone': u.phone,
                        'gender': u.gender,
                        'role': role_obj.role_name if role_obj else 'Unknown',
                        'role_code': role_obj.role_code if role_obj else 'UNKNOWN',
                    })

            # Enrich with login info from main DB
            school_user_ids = [u['school_user_id'] for u in users_data]
            if school_user_ids:
                main_users = User.query.filter(
                    User.school_user_id.in_(school_user_ids),
                    User.skid == skid
                ).all()
                main_user_map = {mu.school_user_id: mu for mu in main_users}
                for u in users_data:
                    main_user = main_user_map.get(u['school_user_id'])
                    u['has_login'] = main_user is not None
                    u['login_active'] = main_user.is_active if main_user else False
                    u['login_username'] = main_user.username if main_user else None

            return {
                'school_name': school.name,
                'school_code': school.code,
                'users': users_data,
                'total': len(users_data)
            }

        except Exception as e:
            raise Exception(f"Failed to get provisioning report: {str(e)}")