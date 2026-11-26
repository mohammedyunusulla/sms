from app.models.main.User import User, UserRole
from app.models.main.Institution import Institution
from app.models.tenant import Student, Teacher, InstitutionUsers, InstitutionAdmin
from app.models.tenant.Roles import Role
from app import db
from sqlalchemy.exc import IntegrityError
from flask import jsonify
from app.utils.db_manager import switch_to_institution_db
from app.utils.helpers import generate_student_id

class UserService:

    @staticmethod
    def create_institution_admin(data):
        try:
            required_fields = ['username', 'email', 'password', 'first_name', 'last_name', 'skid', 'institution_id']
            for field in required_fields:
                if not data.get(field):
                    raise ValueError(f"Missing required field: {field}")
            
            skid = data['skid']
            
            # Validate uniqueness
            if User.get_by_username(data['username']):
                raise ValueError("Username already exists")
            if User.get_by_email(data['email']):
                raise ValueError("Email already exists")

            institution = Institution.query.get(data['institution_id'])
            if not institution:
                raise ValueError("Invalid institution_id")

            # Create in main users table
            user = User(
                username=data['username'],
                email=data['email'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                phone=data.get('phone'),
                role=UserRole.INSTITUTION_ADMIN,
                skid=skid,
                institution_id=institution.id
            )
            user.set_password(data['password'])
            user.save()
            saved_user_id = user.id

            # Set this user as admin of the institution
            previous_admin_id = institution.institution_admin_id
            institution.institution_admin_id = user.id
            db.session.commit()

            # Create in tenant DB: institution_users and institution_admins
            with switch_to_institution_db(skid) as session:
                institution_user = InstitutionUsers(
                    username=data['username'],
                    email=data['email'],
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    skid=skid,
                    is_active=True
                )
                session.add(institution_user)
                session.flush()
                # Give the tenant record its Institution Admin role (it used to be left empty, QA A35)
                from app.utils.account_create import role_for, add_role_link
                add_role_link(session, institution_user, role_for(session, 'INSTITUTION_ADMIN'))

                institution_admin_profile = InstitutionAdmin(
                    user_id=institution_user.id,
                    # str(UserRole.INSTITUTION_ADMIN) stored the text "UserRole.INSTITUTION_ADMIN"
                    designation=(str(data.get('designation') or '').strip() or 'Institution Admin')[:100]
                )
                session.add(institution_admin_profile)
                session.commit()

                # Link back institution_user_id to main DB
                user.institution_user_id = institution_user.id
                db.session.commit()

            return user

        except Exception as e:
            db.session.rollback()
            # All or nothing: the tenant step failed after the login was saved, so undo the login too
            if 'saved_user_id' in locals():
                try:
                    if 'previous_admin_id' in locals():
                        institution.institution_admin_id = previous_admin_id
                    leftover = User.query.get(saved_user_id)
                    if leftover:
                        db.session.delete(leftover)
                    db.session.commit()
                except Exception:
                    db.session.rollback()
            if isinstance(e, ValueError):
                raise
            raise Exception(f"Failed to create institution admin: {str(e)}")

    
    @staticmethod
    def create_institution_user(data):
        try:
            required_fields = ['username', 'email', 'password', 'first_name', 'last_name', 'role', 'skid', 'institution_id']
            for field in required_fields:
                if not data.get(field):
                    raise ValueError(f"Missing required field: {field}")
            
            skid = data['skid']
            
            if data['role'] not in ['TEACHER', 'STUDENT', 'PARENT', 'STAFF']:
                raise ValueError("Invalid institution user role")

            institution = Institution.query.get(data['institution_id'])
            if not institution:
                raise ValueError("Invalid institution_id")

            # Create in main DB
            user = User(
                username=data['username'],
                email=data['email'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                phone=data.get('phone'),
                role=UserRole(data['role']),
                skid=skid,
                institution_id=institution.id
            )
            user.set_password(data['password'])
            user.save()

            # Insert into tenant DB
            with switch_to_institution_db(skid) as tenant_session:
                institution_user = InstitutionUsers(
                    username=data['username'],
                    email=data['email'],
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    phone_number=data.get('phone'),
                    skid=skid,
                    is_active=True
                )
                tenant_session.add(institution_user)
                tenant_session.flush()

                # Create respective profile
                if user.role == UserRole.TEACHER:
                    profile = Teacher(
                        user_id=institution_user.id,
                        employee_id=data.get('employee_id'),
                        designation=data.get('designation'),
                        date_of_joining=data.get('date_of_joining'),
                        qualifications=data.get('qualifications'),
                        salary=data.get('salary')
                    )
                elif user.role == UserRole.STUDENT:
                    profile = Student(
                        user_id=institution_user.id,
                        student_id=data.get('student_id'),
                        admission_date=data.get('admission_date'),
                        class_id=data.get('class_id'),
                        section_id=data.get('section_id')
                    )
                else:
                    raise ValueError("Only teacher/student logic implemented. Add parent/staff if needed.")

                tenant_session.add(profile)
                tenant_session.commit()

                user.institution_user_id = institution_user.id
                db.session.commit()

            return user

        except Exception as e:
            db.session.rollback()
            raise Exception(f"Failed to create institution user: {str(e)}")

    
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
            updatable_fields = ['email', 'first_name', 'last_name', 'phone', 'role', 'institution_id']
            
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
                    
                    elif field == 'institution_id':
                        # Validate institution
                        if user_data['institution_id']:
                            institution = Institution.get_by_id(user_data['institution_id'])
                            if not institution:
                                raise ValueError("Invalid institution_id")
                    
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
    def get_users_by_institution(skid, page=1, limit=10, search='', gender='', role='', status=''):
        """
        Get paginated users for a specific institution with filtering and sorting
        """
        try:
            with switch_to_institution_db(skid) as tenant_session:
                # Build base query
                query = tenant_session.query(InstitutionUsers).join(Role, InstitutionUsers.role_id == Role.id)

                # Filter by status (active/inactive)
                if status.lower() == 'active':
                    query = query.filter(InstitutionUsers.is_active == True)
                elif status.lower() == 'inactive':
                    query = query.filter(InstitutionUsers.is_active == False)
                else:
                    query = query.filter(InstitutionUsers.is_active == True)  # Default to active

                # Filter by gender
                if gender:
                    query = query.filter(InstitutionUsers.gender == gender)

                # Filter by role
                if role:
                    # Convert role string to match role_code in database
                    role_upper = role.upper()
                    query = query.filter(Role.role_code == role_upper)

                # Filter by search term (searches in name, email, phone)
                if search:
                    search_term = f"%{search}%"
                    query = query.filter(
                        (InstitutionUsers.first_name.ilike(search_term)) |
                        (InstitutionUsers.last_name.ilike(search_term)) |
                        (InstitutionUsers.email.ilike(search_term)) |
                        (InstitutionUsers.phone.ilike(search_term))
                    )

                # Get total count before pagination
                total = query.count()

                # Calculate pagination
                offset = (page - 1) * limit
                total_pages = (total + limit - 1) // limit

                # Order by name and apply pagination
                users = query.order_by(
                    InstitutionUsers.first_name,
                    InstitutionUsers.last_name
                ).offset(offset).limit(limit).all()

                users_data = [user.to_dict() for user in users]

            # Enrich with login info from main DB (outside tenant session)
            institution_user_ids = [u['id'] for u in users_data]
            if institution_user_ids:
                main_users = User.query.filter(
                    User.institution_user_id.in_(institution_user_ids),
                    User.skid == skid
                ).all()
                # Map institution_user_id -> main User
                main_user_map = {mu.institution_user_id: mu for mu in main_users}
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
    def get_staff_by_institution(skid):
        """
        Get all staff users with role information (excludes Institution Admin, Student, Parent)
        """
        try:
            with switch_to_institution_db(skid) as tenant_session:
                # Define roles to exclude
                excluded_role_codes = ['INSTITUTION_ADMIN', 'STUDENT', 'PARENT']
                
                users = (
                    tenant_session.query(InstitutionUsers)
                    .join(Role, InstitutionUsers.role_id == Role.id)
                    .filter(
                        InstitutionUsers.is_active == True,
                        Role.role_code.notin_(excluded_role_codes)
                    )
                    .order_by(InstitutionUsers.first_name, InstitutionUsers.last_name)
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
            from app.utils.helpers import validate_password
            ok, problem = validate_password(password)
            if not ok:
                raise ValueError(problem)
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
                institution_id=None,
                institution_user_id=None
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
    def provision_single_login(institution_user_id, skid, institution_id, password):
        """
        Create a login (User record in main DB) for an existing InstitutionUsers record.
        Used after sign-in is switched on for a role, for people created without a login.
        """
        try:
            from app.utils.helpers import validate_password
            ok, problem = validate_password(password)
            if not ok:
                raise ValueError(problem)

            # Check if already provisioned
            existing = User.query.filter_by(institution_user_id=institution_user_id, skid=skid).first()
            if existing:
                raise ValueError("User already has login access")

            # Get institution for institution_code
            institution = Institution.query.get(institution_id)
            if not institution:
                raise ValueError("Invalid institution_id")

            # Read InstitutionUsers + role from tenant DB
            with switch_to_institution_db(skid) as tenant_session:
                institution_user = tenant_session.query(InstitutionUsers).filter_by(id=institution_user_id).first()
                if not institution_user:
                    raise ValueError("Institution user not found")
                if not institution_user.is_active:
                    raise ValueError("Institution user is inactive")

                # Get role code
                role_obj = tenant_session.query(Role).filter_by(id=institution_user.role_id).first()
                # the login role: the built-in role itself, or the one a custom role is based on
                role_code = str((role_obj.base_role or role_obj.role_code) if role_obj else '').upper() or None

                from app.utils.features import LOGIN_ROLES, login_enabled
                if role_code not in LOGIN_ROLES:
                    raise ValueError("This person's role can't be given a login this way")
                if not login_enabled(skid, role_code):
                    raise ValueError(f"Sign-in is switched off for {LOGIN_ROLES[role_code]}s at this institution")

                # Extract user data while session is open
                user_data = {
                    'username': institution_user.username,
                    'email': institution_user.email,
                    'first_name': institution_user.first_name,
                    'last_name': institution_user.last_name,
                    'phone': institution_user.phone,
                    'role_code': role_code,
                    'institution_user_id': institution_user.id,
                }

            # Validate required fields
            if not user_data['username']:
                raise ValueError("Missing required field: username")
            if not user_data['email']:
                raise ValueError("Missing required field: email")
            if not user_data['first_name']:
                raise ValueError("Missing required field: first_name")

            # Check username uniqueness - append institution_code if conflict
            username = user_data['username']
            if User.query.filter_by(username=username).first():
                username = f"{username}_{institution.code}"
                if User.query.filter_by(username=username).first():
                    raise ValueError(f"Username '{user_data['username']}' already exists even with institution code suffix")

            # Check email uniqueness
            if User.query.filter_by(email=user_data['email']).first():
                raise ValueError(f"Email '{user_data['email']}' is already registered in another institution")

            # Create User record in main DB
            user = User(
                username=username,
                email=user_data['email'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                phone=user_data['phone'],
                role=UserRole(user_data['role_code']),
                skid=skid,
                institution_id=institution_id,
                institution_user_id=user_data['institution_user_id']
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
    def provision_bulk_logins(skid, institution_id, default_password, role_filter=None):
        """
        Bulk create logins for STUDENT/PARENT InstitutionUsers who don't have User records.
        Returns a detailed report of results.
        """
        try:
            from app.utils.helpers import validate_password
            ok, problem = validate_password(default_password)
            if not ok:
                raise ValueError(f"Default password: {problem}")

            # Get institution for institution_code
            institution = Institution.query.get(institution_id)
            if not institution:
                raise ValueError("Invalid institution_id")

            # Read eligible InstitutionUsers from tenant DB
            with switch_to_institution_db(skid) as tenant_session:
                query = tenant_session.query(InstitutionUsers).join(Role, InstitutionUsers.role_id == Role.id)

                # Only roles whose sign-in is switched on (one of them when role_filter is given)
                from sqlalchemy import func as sa_func
                from app.utils.features import settings_for
                eligible_roles = settings_for(skid)['login_roles']
                if role_filter:
                    eligible_roles = [r for r in eligible_roles if r == str(role_filter).upper()]
                login_role = sa_func.upper(sa_func.coalesce(Role.base_role, Role.role_code))
                query = query.filter(login_role.in_(eligible_roles or ['-']))

                query = query.filter(InstitutionUsers.is_active == True)
                all_institution_users = query.all()

                # Collect user data while session is open
                institution_users_data = []
                for su in all_institution_users:
                    role_obj = tenant_session.query(Role).filter_by(id=su.role_id).first()
                    institution_users_data.append({
                        'id': su.id,
                        'username': su.username,
                        'email': su.email,
                        'first_name': su.first_name,
                        'last_name': su.last_name,
                        'phone': su.phone,
                        'full_name': su.full_name,
                        'role_code': str((role_obj.base_role or role_obj.role_code) if role_obj else '').upper() or None,
                        'role_name': role_obj.role_name if role_obj else None,
                    })

            total_eligible = len(institution_users_data)

            # Find which ones already have a User record
            institution_user_ids = [su['id'] for su in institution_users_data]
            existing_users = User.query.filter(
                User.institution_user_id.in_(institution_user_ids),
                User.skid == skid
            ).all() if institution_user_ids else []
            already_provisioned_ids = {u.institution_user_id for u in existing_users}

            # Pre-fetch all existing usernames and emails for conflict checking
            existing_usernames = {u.username for u in User.query.with_entities(User.username).all()}
            existing_emails = {u.email for u in User.query.with_entities(User.email).all()}

            success_count = 0
            failed_count = 0
            already_provisioned = len(already_provisioned_ids)
            failures = []
            successes = []

            for su_data in institution_users_data:
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
                        'institution_user_id': su_data['id'],
                        'name': su_data['full_name'],
                        'role': su_data['role_name'],
                        'reason': f"Missing required fields: {', '.join(missing_fields)}"
                    })
                    continue

                # Check username uniqueness
                username = su_data['username']
                if username in existing_usernames:
                    username = f"{username}_{institution.code}"
                    if username in existing_usernames:
                        failed_count += 1
                        failures.append({
                            'institution_user_id': su_data['id'],
                            'name': su_data['full_name'],
                            'role': su_data['role_name'],
                            'reason': f"Username '{su_data['username']}' conflict even with institution code suffix"
                        })
                        continue

                # Check email uniqueness
                if su_data['email'] in existing_emails:
                    failed_count += 1
                    failures.append({
                        'institution_user_id': su_data['id'],
                        'name': su_data['full_name'],
                        'role': su_data['role_name'],
                        'reason': f"Email '{su_data['email']}' already registered in another institution"
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
                        institution_id=institution_id,
                        institution_user_id=su_data['id']
                    )
                    user.set_password(default_password)
                    db.session.add(user)
                    db.session.flush()

                    # Track in sets to prevent duplicates within this batch
                    existing_usernames.add(username)
                    existing_emails.add(su_data['email'])

                    success_count += 1
                    successes.append({
                        'institution_user_id': su_data['id'],
                        'name': su_data['full_name'],
                        'role': su_data['role_name'],
                        'username': username,
                        'email': su_data['email'],
                    })
                except Exception as e:
                    failed_count += 1
                    failures.append({
                        'institution_user_id': su_data['id'],
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
    def get_provisioning_report(skid, institution_id):
        """
        Get a full report of all users in an institution with their login status.
        Used for export after provisioning.
        """
        try:
            # Get institution info
            institution = Institution.query.get(institution_id)
            if not institution:
                raise ValueError("Invalid institution_id")

            # Read all InstitutionUsers from tenant DB
            with switch_to_institution_db(skid) as tenant_session:
                all_users = (
                    tenant_session.query(InstitutionUsers)
                    .join(Role, InstitutionUsers.role_id == Role.id)
                    .filter(InstitutionUsers.is_active == True)
                    .order_by(Role.role_code, InstitutionUsers.first_name, InstitutionUsers.last_name)
                    .all()
                )

                users_data = []
                for u in all_users:
                    role_obj = tenant_session.query(Role).filter_by(id=u.role_id).first()
                    users_data.append({
                        'institution_user_id': u.id,
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
            institution_user_ids = [u['institution_user_id'] for u in users_data]
            if institution_user_ids:
                main_users = User.query.filter(
                    User.institution_user_id.in_(institution_user_ids),
                    User.skid == skid
                ).all()
                main_user_map = {mu.institution_user_id: mu for mu in main_users}
                for u in users_data:
                    main_user = main_user_map.get(u['institution_user_id'])
                    u['has_login'] = main_user is not None
                    u['login_active'] = main_user.is_active if main_user else False
                    u['login_username'] = main_user.username if main_user else None

            return {
                'institution_name': institution.name,
                'institution_code': institution.code,
                'users': users_data,
                'total': len(users_data)
            }

        except Exception as e:
            raise Exception(f"Failed to get provisioning report: {str(e)}")
    # ------------------------------------------------------------------
    # Institution-user based view/edit (the Users list shows tenant institution_users)
    # ------------------------------------------------------------------
    @staticmethod
    def get_institution_user(skid, institution_user_id):
        """Return a tenant institution user with role and login info, or None."""
        with switch_to_institution_db(skid) as tenant_session:
            su = tenant_session.query(InstitutionUsers).filter_by(id=int(institution_user_id)).first()
            if not su:
                return None
            role = tenant_session.query(Role).filter_by(id=su.role_id).first() if su.role_id else None
            data = {
                'id': su.id,
                'username': su.username,
                'first_name': su.first_name,
                'last_name': su.last_name,
                'name': su.full_name,
                'full_name': su.full_name,
                'email': su.email,
                'phone': su.phone,
                'gender': su.gender,
                'date_of_birth': su.date_of_birth.isoformat() if su.date_of_birth else None,
                'address': su.address,
                'role': role.role_code if role else (
                    'INSTITUTION_ADMIN' if tenant_session.query(InstitutionAdmin).filter_by(user_id=su.id).first() else None),
                'role_name': role.role_name if role else None,
                'is_active': bool(su.is_active),
                'status': 'active' if su.is_active else 'inactive',
                'created_at': su.created_at.isoformat() if getattr(su, 'created_at', None) else None,
                'updated_at': su.updated_at.isoformat() if getattr(su, 'updated_at', None) else None,
            }
        main_user = User.query.filter_by(institution_user_id=int(institution_user_id), skid=skid).first()
        if not data['role'] and main_user:
            # Institution admins have no tenant role row; their role lives on the main login
            data['role'] = main_user.role.value if hasattr(main_user.role, 'value') else str(main_user.role)
            data['role_name'] = data['role'].replace('_', ' ').title()
        data['has_login'] = main_user is not None
        data['main_user_id'] = main_user.id if main_user else None
        data['login_active'] = bool(main_user.is_active) if main_user else False
        return data

    @staticmethod
    def update_institution_user(skid, institution_user_id, data):
        """
        Update a tenant institution user's personal details and keep their login (if any) in sync.
        Role and active status are NOT changed here (status uses delete/reactivate).
        """
        editable = ['username', 'first_name', 'last_name', 'email', 'phone', 'gender', 'date_of_birth', 'address']
        changes = {k: (v.strip() if isinstance(v, str) else v) for k, v in data.items() if k in editable}
        if 'first_name' in changes and not changes['first_name']:
            raise ValueError('First name is required')
        if 'email' in changes and not changes['email']:
            raise ValueError('Email is required')
        institution_user_id = int(institution_user_id)
        main_user = User.query.filter_by(institution_user_id=institution_user_id, skid=skid).first()

        with switch_to_institution_db(skid) as tenant_session:
            su = tenant_session.query(InstitutionUsers).filter_by(id=institution_user_id).first()
            if not su:
                raise LookupError('User not found')
            for field in ('username', 'email'):
                value = changes.get(field)
                if value and value != getattr(su, field):
                    clash = tenant_session.query(InstitutionUsers).filter(getattr(InstitutionUsers, field) == value, InstitutionUsers.id != institution_user_id).first()
                    main_clash = User.query.filter(getattr(User, field) == value, User.id != (main_user.id if main_user else 0)).first()
                    if clash or main_clash:
                        raise ValueError(f"That {field} is already in use")
            for key, value in changes.items():
                setattr(su, key, value or None if key in ('phone', 'gender', 'date_of_birth', 'address') else value)

        if main_user:
            for key in ('username', 'first_name', 'last_name', 'email', 'phone'):
                if key in changes and hasattr(main_user, key):
                    setattr(main_user, key, changes[key] or None if key == 'phone' else changes[key])
            db.session.commit()
        return UserService.get_institution_user(skid, institution_user_id)
