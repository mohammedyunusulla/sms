from app.models.main.User import User, UserRole
from app.models.main.School import School
from app.models.tenant import Student, SchoolUsers, StudentEnrollment, Class, StudentParent, Parent, AcademicYear
from app.models.tenant.Sections import Section
from app import db
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from flask import jsonify
from app.utils.db_manager import switch_to_school_db
from app.services.userRole_service import UserRolesService
from datetime import datetime, date, timedelta

class StudentService:

    @staticmethod
    def create_student_user(data, skid):
        user = None
        school_user_id = None
    
        try:
            school = School.query.filter_by(skid=skid).first()
            if not school:
                raise ValueError("School not found")
            
            from app.models.main.School import SchoolPlan
            plan = school.plan
            create_login = plan in [SchoolPlan.STANDARD, SchoolPlan.PREMIUM]
    
            # Step 1: Create main user (only for STANDARD/PREMIUM)
            if create_login:
                user = User(
                    username=data['username'],
                    email=data['email'],
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    phone=data.get('phone'),
                    role=UserRole(data['role']),
                    skid=skid,
                    plan=plan.value,  # Convert enum to string
                    school_id=data.get('school_id')
                )
                user.set_password(data['password'])
                db.session.add(user)
                db.session.flush()  # Get user.id but don't commit yet
    
            # Step 2: Create tenant user (always)
            with switch_to_school_db(skid) as tenant_session:
                school_user = SchoolUsers(
                    username=data['username'],
                    email=data['email'],
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    phone=data.get('phone'),
                    gender=data.get('gender'),
                    date_of_birth=data.get('date_of_birth'),
                    role_id=data.get('role_id'),
                    skid=skid,
                    is_active=True
                )

                tenant_session.add(school_user)
                tenant_session.flush()
                school_user_id = school_user.id
    
                # Create student profile + enrollment
                student_profile = Student(
                    user_id=school_user_id,
                    roll_no=data.get('roll_no'),
                    admission_date=data.get('admission_date'),
                    class_id=data.get('class_id'),
                    section_id=data.get('section_id'),
                    # Essential fields for ID Cards & Certificates
                    student_photo=data.get('student_photo'),
                    blood_group=data.get('blood_group'),
                    emergency_contact=data.get('emergency_contact'),
                    # Identification Details
                    admission_number=data.get('admission_number'),
                    aadhar_number=data.get('aadhar_number'),
                    birth_certificate_number=data.get('birth_certificate_number'),
                    nationality=data.get('nationality', 'Indian'),
                    religion=data.get('religion'),
                    category=data.get('category'),
                    mother_tongue=data.get('mother_tongue')
                )
                tenant_session.add(student_profile)
    
                # Resolve academic year: use provided value or fall back to current
                academic_year_id = data.get('academic_year_id')
                if not academic_year_id:
                    current_year = tenant_session.query(AcademicYear).filter_by(is_current=True).first()
                    if current_year:
                        academic_year_id = current_year.id

                enrollment = StudentEnrollment(
                    student_id=school_user_id,
                    class_id=data.get('class_id'),
                    section_id=data.get('section_id'),
                    academic_year_id=academic_year_id,
                    enrollment_date=data.get('admission_date') or datetime.utcnow().date()
                )
                tenant_session.add(enrollment)
    
                # Commit tenant DB first
                tenant_session.commit()

            # Step 3: Commit main DB and set school_user_id (if login was created)
            if create_login and user:
                user.school_user_id = school_user_id
                db.session.commit()

            # Step 4: Assign role in tenant DB (ALWAYS - regardless of create_login)
            # This must happen AFTER main DB commit so the user can be found by school_user_id
            role_data = {
                "user_id": school_user_id,
                "role_id": data.get("role_id"),
                "assigned_by": 1,
                "update_main_db": create_login  # Flag to control main DB update
            }
            UserRolesService.assign_role_to_user(role_data, skid)
    
            # Step 5: Return proper object
            if create_login and user:
                return user.to_dict()
            else:
                with switch_to_school_db(skid) as tenant_session:
                    school_user = tenant_session.get(SchoolUsers, school_user_id)
                    return school_user.to_dict()
    
        except Exception as e:
            db.session.rollback()
            if 'tenant_session' in locals():
                tenant_session.rollback()
    
            # Cleanup orphan main user if created
            if user and user.id:
                try:
                    db.session.delete(user)
                    db.session.commit()
                except Exception as cleanup_err:
                    db.session.rollback()
                    print(f"[Cleanup failed] Could not delete main user: {cleanup_err}")
    
            raise Exception(f"Failed to create school user: {str(e)}")

    
    @staticmethod
    def set_student_active(skid, student_id, active):
        """
        Soft delete / reactivate a student.
        Only the active flags change (tenant school_users + main-DB login); attendance, marks,
        fees, enrollments and parent links are kept, so reactivating restores everything.
        """
        with switch_to_school_db(skid) as tenant_session:
            school_user = tenant_session.query(SchoolUsers).filter_by(id=student_id).first()
            is_student = school_user and tenant_session.query(Student).filter_by(user_id=student_id).first()
            if not is_student:
                return {'success': False, 'code': 404, 'message': 'Student not found'}
            if bool(school_user.is_active) == bool(active):
                state = 'active' if active else 'inactive'
                return {'success': False, 'code': 400, 'message': f'Student is already {state}'}
            school_user.is_active = bool(active)
            name = f"{school_user.first_name} {school_user.last_name}".strip()

        # Login account (only exists if a login was provisioned)
        main_user = User.query.filter_by(school_user_id=student_id, skid=skid).first()
        if main_user:
            main_user.is_active = bool(active)
            db.session.commit()

        return {
            'success': True,
            'code': 200,
            'message': f"{name} {'reactivated' if active else 'deactivated (records kept, can be reactivated)'}",
            'data': {'student_id': student_id, 'is_active': bool(active), 'login_updated': bool(main_user)},
        }

    @staticmethod
    def update_student(user_id, skid, data):
        """
        Update student information across main and tenant databases
        user_id: The school_user_id (ID from SchoolUsers table in tenant DB)
        skid: School identifier
        data: Dictionary containing fields to update

        Plan-aware update:
        - BASIC plan: Only updates tenant DB (user doesn't exist in main DB)
        - STANDARD/PREMIUM: Updates both main DB and tenant DB
        """
        main_user = None
        tenant_session = None
        school_user_id = user_id

        # Define fields that should never be updated
        # is_active is changed only via the delete/reactivate endpoints, never as a side effect of editing.
        PROTECTED_FIELDS = {'id', 'created_at', 'user_id', 'is_active'}

        try:
            # Step 1: Get school info to determine plan
            school = School.query.filter_by(skid=skid).first()
            if not school:
                raise ValueError("School not found")

            from app.models.main.School import SchoolPlan
            plan = school.plan
            create_login = plan in [SchoolPlan.STANDARD, SchoolPlan.PREMIUM]

            # Step 2: Try to fetch from main DB (only if plan allows login)
            if create_login:
                main_user = db.session.query(User).filter_by(
                    school_user_id=user_id,
                    skid=skid
                ).first()
                if not main_user:
                    raise ValueError("User not found in main database.")

            # Step 3: Fetch from tenant DB to get current values
            with switch_to_school_db(skid) as temp_session:
                current_school_user = temp_session.query(SchoolUsers).filter_by(
                    id=school_user_id,
                    skid=skid
                ).first()
                if not current_school_user:
                    raise ValueError("User not found in tenant database.")

            # Step 4: Update the main database (if plan allows login)
            if create_login and main_user:
                for key, value in data.items():
                    # Skip protected fields, password (handled separately), and fields not in model
                    if key in PROTECTED_FIELDS or key == 'password' or not hasattr(main_user, key):
                        continue
                    setattr(main_user, key, value)

                # If a new password is provided, set it
                if 'password' in data and data['password']:
                    main_user.set_password(data['password'])

                db.session.commit()

            # Step 5: Update the tenant database (ALWAYS update)
            with switch_to_school_db(skid) as tenant_session:
                # Find the SchoolUsers entry
                school_user = tenant_session.query(SchoolUsers).filter_by(
                    id=school_user_id,
                    skid=skid
                ).first()
                if not school_user:
                    raise ValueError("User not found in tenant database.")

                # Update SchoolUsers's fields
                for key, value in data.items():
                    # Skip protected fields and password
                    if key in PROTECTED_FIELDS or key == 'password':
                        continue

                    if hasattr(school_user, key):
                        setattr(school_user, key, value)

                # Find the Student profile and update its fields
                student_profile = tenant_session.query(Student).filter_by(
                    user_id=school_user_id
                ).first()
                if not student_profile:
                    raise ValueError("Student profile not found in tenant database.")

                # Update student-specific fields
                for key, value in data.items():
                    # Skip protected fields
                    if key in PROTECTED_FIELDS:
                        continue

                    if hasattr(student_profile, key):
                        setattr(student_profile, key, value)

                tenant_session.commit()

            # Step 6: Return appropriate response
            if create_login and main_user:
                return main_user.to_dict()
            else:
                with switch_to_school_db(skid) as temp_session:
                    school_user = temp_session.query(SchoolUsers).filter_by(id=school_user_id).first()
                    return school_user.to_dict() if school_user else {}

        except Exception as e:
            # Central rollback for the update function
            db.session.rollback()
            if tenant_session is not None:
                tenant_session.rollback()
            raise Exception(f"Failed to update user: {str(e)}")

    
    @staticmethod
    def check_duplicate_user(data, skid):
        """
        Check if user already exists in both main DB and tenant DB
        Returns error message if duplicate found, None if no duplicates
        """
        try:
            # Check main DB first
            existing_main_user = User.query.filter(
                (User.username == data['username']) | (User.email == data['email'])
            ).filter(User.skid == skid).first()

            if existing_main_user:
                return "Student with this username or email already exists"

            # Check tenant DB
            with switch_to_school_db(skid) as tenant_session:
                existing_tenant_user = tenant_session.query(SchoolUsers).filter(
                    (SchoolUsers.username == data['username']) | (SchoolUsers.email == data['email'])
                ).first()

                if existing_tenant_user:
                    return "Student with this username or email already exists"

            # Check if student ID already exists (if provided)
            if data.get('roll_no'):
                with switch_to_school_db(skid) as tenant_session:
                    existing_student = tenant_session.query(Student).filter(
                        Student.roll_no == data['roll_no']
                    ).first()
                    if existing_student:
                        return "Student ID already exists"
            return None

        except Exception as e:
            return f"Error checking for duplicates: {str(e)}"

    @staticmethod
    def check_duplicate_user_for_update(data, skid, current_user_id):
        """
        Check if user already exists while excluding the current user being updated
        Returns error message if duplicate found, None if no duplicates

        Args:
            data: Dictionary containing username, email, roll_no
            skid: School identifier
            current_user_id: The school_user_id of the user being updated
        """
        try:
            # Check username uniqueness if provided and different
            if 'username' in data:
                # Check main DB (exclude current user)
                existing_main_user = User.query.filter(
                    User.username == data['username'],
                    User.school_user_id != current_user_id
                ).filter(User.skid == skid).first()

                if existing_main_user:
                    return "Username already exists in the system"

                # Check tenant DB (exclude current user)
                with switch_to_school_db(skid) as tenant_session:
                    existing_tenant_user = tenant_session.query(SchoolUsers).filter(
                        SchoolUsers.username == data['username'],
                        SchoolUsers.id != current_user_id
                    ).first()

                    if existing_tenant_user:
                        return "Username already exists in this school"

            # Check email uniqueness if provided and different
            if 'email' in data:
                # Check main DB (exclude current user)
                existing_main_user = User.query.filter(
                    User.email == data['email'],
                    User.school_user_id != current_user_id
                ).filter(User.skid == skid).first()

                if existing_main_user:
                    return "Email already exists in the system"

                # Check tenant DB (exclude current user)
                with switch_to_school_db(skid) as tenant_session:
                    existing_tenant_user = tenant_session.query(SchoolUsers).filter(
                        SchoolUsers.email == data['email'],
                        SchoolUsers.id != current_user_id
                    ).first()

                    if existing_tenant_user:
                        return "Email already exists in this school"

            # Check if roll_no already exists (if provided and different)
            if data.get('roll_no'):
                with switch_to_school_db(skid) as tenant_session:
                    existing_student = tenant_session.query(Student).filter(
                        Student.roll_no == data['roll_no'],
                        Student.user_id != current_user_id
                    ).first()
                    if existing_student:
                        return "Student ID already exists"

            return None

        except Exception as e:
            return f"Error checking for duplicates: {str(e)}"
    
    @staticmethod
    def get_students_paginated(skid, page=1, limit=10, search='', status='', gender=''):
        """
        Get paginated list of students with filtering
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Base query
                query = (
                    tenant_session.query(SchoolUsers, Student, Class, Section)
                    .join(Student, SchoolUsers.id == Student.user_id)
                    .outerjoin(Class, Student.class_id == Class.id)
                    .outerjoin(Section, Student.section_id == Section.id)
                )

                # Apply filters
                if search:
                    search_term = f"%{search}%"
                    query = query.filter(
                        (SchoolUsers.first_name.ilike(search_term)) |
                        (SchoolUsers.last_name.ilike(search_term)) |
                        (SchoolUsers.email.ilike(search_term)) |
                        (SchoolUsers.phone.ilike(search_term))
                    )

                if status:
                    query = query.filter(SchoolUsers.is_active == (status.lower() == 'active'))

                if gender:
                    query = query.filter(SchoolUsers.gender == gender)

                # Get total count before pagination
                total = query.count()

                # Apply pagination
                offset = (page - 1) * limit
                students_data = query.offset(offset).limit(limit).all()

                student_list = []
                for school_user, student, class_, section in students_data:
                    # Convert base SchoolUser data to dict
                    user_dict = school_user.to_dict()

                    # Attach student profile info
                    user_dict["profile"] = student.to_dict() if student else None

                    # Attach nested class and section objects
                    user_dict["class"] = class_.to_dict() if class_ else None
                    user_dict["section"] = section.to_dict() if section else None

                    student_list.append(user_dict)

                # Calculate total pages
                total_pages = (total + limit - 1) // limit

            # Enrich with login info from main DB (outside tenant session)
            school_user_ids = [s['id'] for s in student_list]
            if school_user_ids:
                main_users = User.query.filter(
                    User.school_user_id.in_(school_user_ids),
                    User.skid == skid
                ).all()
                main_user_map = {mu.school_user_id: mu for mu in main_users}
                for s in student_list:
                    main_user = main_user_map.get(s['id'])
                    s['has_login'] = main_user is not None
                    s['main_user_id'] = main_user.id if main_user else None
                    s['login_active'] = main_user.is_active if main_user else False

            return {
                'data': student_list,
                'meta': {
                    'total': total,
                    'page': page,
                    'limit': limit,
                    'totalPages': total_pages
                }
            }

        except Exception as e:
            raise Exception(f"Failed to get Students: {str(e)}")

    @staticmethod
    def get_students(skid, academic_year_id):
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Base query
                query = (
                    tenant_session.query(SchoolUsers, Student, Class, Section)
                    .join(Student, SchoolUsers.id == Student.user_id)
                    .outerjoin(Class, Student.class_id == Class.id)
                    .outerjoin(Section, Student.section_id == Section.id)
                    .outerjoin(
                        StudentEnrollment,
                        (StudentEnrollment.student_id == Student.user_id)
                    )
                )
                # Filter by academic year if provided
                if academic_year_id:
                    query = query.filter(StudentEnrollment.academic_year_id == academic_year_id)

                Students = query.all()

                student_list = []
                for school_user, student, class_, section in Students:
                    # Convert base SchoolUser data to dict
                    user_dict = school_user.to_dict()

                    # Attach student profile info (like your existing "profile" key)
                    user_dict["profile"] = student.to_dict() if student else None

                    # Attach nested class and section objects (like "role" or "profile")
                    user_dict["class"] = class_.to_dict() if class_ else None
                    user_dict["section"] = section.to_dict() if section else None

                    student_list.append(user_dict)

                return student_list

        except Exception as e:
            raise Exception(f"Failed to get Students: {str(e)}")

    @staticmethod
    def get_student_by_id(skid, id):
        try:
            with switch_to_school_db(skid) as tenant_session:
                student = (
                    tenant_session.query(SchoolUsers, Student, Class, Section)
                    .join(Student, SchoolUsers.id == Student.user_id)
                    .outerjoin(Class, Student.class_id == Class.id)
                    .outerjoin(Section, Student.section_id == Section.id)
                    .filter(Student.user_id == id)
                    .first()
                )

                if not student:
                    return None

                school_user, student, class_, section = student

                # Convert base SchoolUser data to dict
                user_dict = school_user.to_dict()

                # Attach student profile info (like your existing "profile" key)
                user_dict["profile"] = student.to_dict() if student else None

                # Attach nested class and section objects (like "role" or "profile")
                user_dict["class"] = class_.to_dict() if class_ else None
                user_dict["section"] = section.to_dict() if section else None
                
                # Fetch parent information
                parent_result = (
                    tenant_session.query(StudentParent, Parent, SchoolUsers)
                    .join(Parent, StudentParent.parent_user_id == Parent.user_id)
                    .join(SchoolUsers, Parent.user_id == SchoolUsers.id)
                    .filter(StudentParent.student_user_id == id)
                    .first()
                )
                
                parent_data = None
                if parent_result:
                    try:
                        link, parent_obj, parent_user = parent_result
                        parent_data = {
                            'id': parent_obj.user_id,
                            'relation_type': link.relation_type,
                            'father_full_name': parent_obj.father_full_name,
                            'mother_full_name': parent_obj.mother_full_name,
                            'father_phone': parent_obj.father_phone,
                            'mother_phone': parent_obj.mother_phone,
                            'email': parent_user.email,
                            'phone': parent_user.phone,
                            'address': parent_obj.address,
                            'city': parent_obj.city,
                            'state': parent_obj.state,
                            'postal_code': parent_obj.postal_code,
                            'father_occupation': parent_obj.father_occupation,
                            'father_qualification': parent_obj.father_qualification,
                            'mother_occupation': parent_obj.mother_occupation,
                            'mother_qualification': parent_obj.mother_qualification
                        }
                    except (ValueError, TypeError, AttributeError) as e:
                        print(f"Error unpacking parent data: {e}")
                        parent_data = None
                
                # ✅ Set parent data outside the if block
                user_dict["parent"] = parent_data


                return user_dict

        except Exception as e:
            raise Exception(f"Failed to get Student by ID: {str(e)}")

    
    @staticmethod
    def get_students_for_section(skid, academic_year_id, section_id, page=1, limit=10, search='', gender='', status=''):
        """
        Get students for a specific section with pagination and filtering

        Args:
            skid: School ID
            academic_year_id: Academic year ID
            section_id: Section ID
            page: Page number (default 1)
            limit: Items per page (default 10)
            search: Search by name or email
            gender: Filter by gender
            status: Filter by enrollment status

        Returns:
            Dictionary with students list and pagination metadata
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Build query with filters
                query = tenant_session.query(StudentEnrollment).filter_by(
                    section_id=section_id
                )

                # Filter by academic year if provided
                if academic_year_id:
                    query = query.filter_by(academic_year_id=academic_year_id)

                enrollments = query.all()
                students = []

                for enrollment in enrollments:
                    result = tenant_session.query(SchoolUsers, Student).join(
                        Student, SchoolUsers.id == Student.user_id
                    ).filter(
                        SchoolUsers.id == enrollment.student_id
                    ).first()

                    if result:
                        user, student_profile = result

                        # Apply search filter (name or email)
                        if search:
                            search_lower = search.lower()
                            full_name = f"{user.first_name} {user.last_name}".lower()
                            if search_lower not in full_name and search_lower not in user.email.lower():
                                continue

                        # Apply gender filter
                        if gender and hasattr(user, 'gender') and user.gender:
                            if user.gender.lower() != gender.lower():
                                continue

                        # Apply status filter (enrollment status)
                        if status:
                            if enrollment.status.lower() != status.lower():
                                continue

                        students.append({
                            "id": user.id,
                            "full_name": f"{user.first_name} {user.last_name}",
                            "email": user.email,
                            "phone": user.phone,
                            "gender": user.gender if hasattr(user, 'gender') else None,
                            "dob": user.date_of_birth,
                            "is_active": user.is_active if hasattr(user, 'is_active') else True,
                            "enrollment_status": enrollment.status,
                            "profile": {
                                "roll_no": student_profile.roll_no,
                                "admission_date": student_profile.admission_date,
                                "class_id": student_profile.class_id,
                                "section_id": student_profile.section_id
                            } if student_profile else None
                        })

                # Calculate pagination
                total = len(students)
                total_pages = (total + limit - 1) // limit  # Ceiling division

                # Apply pagination
                start_idx = (page - 1) * limit
                end_idx = start_idx + limit
                paginated_students = students[start_idx:end_idx]

                return {
                    'students': paginated_students,
                    'total': total,
                    'totalPages': total_pages
                }

        except Exception as e:
            raise Exception(f"Failed to get Students: {str(e)}")

    @staticmethod
    def bulk_create_students(students_data, skid, default_password='Admin@123'):
        """
        Create multiple students in bulk
        Follows same logic as create_student_user for plan-based login creation
        """
        try:
            # Get school information
            school = School.query.filter_by(skid=skid).first()
            if not school:
                raise ValueError("School not found")
            
            # Determine if we should create logins based on school plan
            from app.models.main.School import SchoolPlan
            plan = school.plan
            create_login = plan in [SchoolPlan.STANDARD, SchoolPlan.PREMIUM]
    
            # Initialize counters
            successful = 0
            failed = 0
            errors = []
            created_students = []
    
            for idx, student_data in enumerate(students_data):
                user = None  # Track main DB user
                school_user_id = None  # Track tenant DB user ID
                
                try:
                    # Validate required fields
                    required_fields = ['first_name', 'last_name', 'email', 'phone', 'gender', 'class_id', 'section_id']
                    missing_fields = [field for field in required_fields if not student_data.get(field)]
                    
                    if missing_fields:
                        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
    
                    # Generate username if not provided
                    username = student_data.get('username', student_data['email'])

                    # Check for duplicates in main DB (only if create_login is True)
                    # Note: users.email and users.username are globally unique in main DB,
                    # so we deliberately do NOT filter by skid here — matching the actual
                    # DB constraint avoids leaking a raw IntegrityError to the caller.
                    if create_login:
                        existing_main_user = User.query.filter(
                            (User.email == student_data['email']) |
                            (User.username == username)
                        ).first()

                        if existing_main_user:
                            conflict_field = 'email' if existing_main_user.email == student_data['email'] else 'username'
                            conflict_value = existing_main_user.email if conflict_field == 'email' else existing_main_user.username
                            raise ValueError(
                                f"{conflict_field.capitalize()} '{conflict_value}' is already registered in the system"
                            )
    
                    # Check for duplicates in tenant DB (always check)
                    with switch_to_school_db(skid) as temp_session:
                        existing_tenant_user = temp_session.query(SchoolUsers).filter(
                            (SchoolUsers.username == username) | (SchoolUsers.email == student_data['email'])
                        ).first()
                        
                        if existing_tenant_user:
                            raise ValueError("User with this username or email already exists in this school")
    
                    # Step 1: Create main user (ONLY for STANDARD/PREMIUM plans)
                    if create_login:
                        user = User(
                            username=username,
                            email=student_data['email'],
                            first_name=student_data['first_name'],
                            last_name=student_data['last_name'],
                            phone=student_data.get('phone'),
                            role=UserRole.STUDENT,
                            skid=skid,
                            plan=plan.value,  # Convert enum to string
                            school_id=school.id
                        )
                        user.set_password(student_data.get('password', default_password))
                        db.session.add(user)
                        db.session.flush()  # Get user.id but don't commit yet
    
                    # Step 2: Create tenant user (ALWAYS - regardless of plan)
                    with switch_to_school_db(skid) as tenant_session:
                        school_user = SchoolUsers(
                            username=username,
                            email=student_data['email'],
                            first_name=student_data['first_name'],
                            last_name=student_data['last_name'],
                            phone=student_data.get('phone'),
                            gender=student_data.get('gender'),
                            date_of_birth=StudentService._parse_excel_date(student_data.get('date_of_birth'), 'date_of_birth'),
                            role_id=student_data.get('role_id', 4),  # Default student role
                            skid=skid,
                            is_active=True
                        )

                        tenant_session.add(school_user)
                        tenant_session.flush()
                        school_user_id = school_user.id
    
                        # Create student profile
                        student_profile = Student(
                            user_id=school_user_id,
                            roll_no=student_data.get('roll_no'),
                            admission_date=StudentService._parse_excel_date(student_data.get('admission_date'), 'admission_date') or datetime.utcnow().date(),
                            class_id=student_data['class_id'],
                            section_id=student_data['section_id'],
                            # Essential fields for ID Cards & Certificates
                            student_photo=student_data.get('student_photo'),
                            blood_group=student_data.get('blood_group'),
                            emergency_contact=student_data.get('emergency_contact'),
                            # Identification Details
                            admission_number=student_data.get('admission_number'),
                            aadhar_number=student_data.get('aadhar_number'),
                            birth_certificate_number=student_data.get('birth_certificate_number'),
                            nationality=student_data.get('nationality', 'Indian'),
                            religion=student_data.get('religion'),
                            category=student_data.get('category'),
                            mother_tongue=student_data.get('mother_tongue')
                        )
                        tenant_session.add(student_profile)

                        # Resolve academic year — use provided value or fall back to current
                        bulk_academic_year_id = student_data.get('academic_year_id')
                        if not bulk_academic_year_id:
                            current_year = tenant_session.query(AcademicYear).filter_by(is_current=True).first()
                            if current_year:
                                bulk_academic_year_id = current_year.id

                        # Create enrollment record
                        enrollment = StudentEnrollment(
                            student_id=school_user_id,
                            class_id=student_data['class_id'],
                            section_id=student_data['section_id'],
                            academic_year_id=bulk_academic_year_id,
                            enrollment_date=StudentService._parse_excel_date(student_data.get('admission_date'), 'admission_date') or datetime.utcnow().date(),
                        )
                        tenant_session.add(enrollment)
                        
                        # Commit tenant DB
                        tenant_session.commit()

                    # Step 3: Commit main DB and set school_user_id (if login was created)
                    if create_login and user:
                        user.school_user_id = school_user_id
                        db.session.commit()

                    # Step 4: Assign role (ALWAYS - regardless of create_login)
                    # This must happen AFTER main DB commit so the user can be found by school_user_id
                    role_data = {
                        "user_id": school_user_id,
                        "role_id": student_data.get("role_id", 4),
                        "assigned_by": 1,
                        "update_main_db": create_login  # Flag to control main DB update
                    }
                    UserRolesService.assign_role_to_user(role_data, skid)
    
                    successful += 1
                    created_students.append({
                        'row': idx + 1,
                        'name': f"{student_data['first_name']} {student_data['last_name']}",
                        'email': student_data['email'],
                        'roll_no': student_data.get('roll_no'),
                        'login_enabled': create_login,
                        'status': 'success'
                    })
    
                except Exception as e:
                    # Rollback both sessions
                    db.session.rollback()
                    if 'tenant_session' in locals():
                        tenant_session.rollback()

                    # Cleanup orphan main user if created
                    if user and user.id:
                        try:
                            db.session.delete(user)
                            db.session.commit()
                        except Exception as delete_error:
                            db.session.rollback()
                            print(f"Failed to clean up user from main DB: {delete_error}")

                    # Translate noisy DB errors into a friendly message.
                    if isinstance(e, IntegrityError):
                        msg_lower = str(e.orig).lower() if getattr(e, 'orig', None) else str(e).lower()
                        if 'users_email_key' in msg_lower or 'school_users_email_key' in msg_lower:
                            error_msg = f"Email '{student_data.get('email', '')}' is already registered"
                        elif 'users_username_key' in msg_lower or 'school_users_username_key' in msg_lower:
                            error_msg = f"Username '{student_data.get('username', student_data.get('email', ''))}' is already registered"
                        else:
                            error_msg = 'Duplicate or constraint violation in database'
                    else:
                        error_msg = str(e)

                    failed += 1
                    errors.append({
                        'row': idx + 1,
                        'name': f"{student_data.get('first_name', '')} {student_data.get('last_name', '')}",
                        'email': student_data.get('email', ''),
                        'error': error_msg,
                        'status': 'failed'
                    })
                    continue
    
            return {
                'total': len(students_data),
                'successful': successful,
                'failed': failed,
                'errors': errors,
                'created_students': created_students,
                'plan': plan.value,
                'login_created': create_login,
                'summary': {
                    'success_rate': round((successful / len(students_data)) * 100, 2) if len(students_data) > 0 else 0,
                    'total_processed': len(students_data)
                }
            }
    
        except Exception as e:
            db.session.rollback()
            raise e
    
    
    @staticmethod
    def _parse_excel_date(value, field_name='date'):
        """Accept either YYYY-MM-DD string or Excel serial and return date."""
        if value is None:
            return None

        # Already a date object
        if isinstance(value, date):
            return value

        # Try string in ISO format
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                pass  # fall through and try numeric

        # Try Excel serial number (float/int)
        try:
            serial = float(value)
            # Excel's day 1 is 1899-12-30 in most libs; adjust if your config differs
            excel_epoch = date(1899, 12, 30)
            return excel_epoch + timedelta(days=int(serial))
        except (TypeError, ValueError):
            # If nothing works, raise a clear error for that row
            raise ValueError(f"Invalid {field_name} value: {value!r}. Expected YYYY-MM-DD or a valid Excel date.")

    
    @staticmethod
    def promote_students(data, skid, promoted_by=None):
        """
        Move students from one class/section/year to the next year.

        PASSED -> new enrollment in the target class/section for the target year (REGULAR).
        FAILED -> detained: new enrollment in their *current* class/section for the target year (DETAINED).
        Every move is written to promotion_history. A student is skipped (with a reason) when the
        target already exists, before anything about them is changed.
        """
        from app.models.tenant.PromotionHistory import PromotionHistory

        def as_int(value, label):
            try:
                return int(value)
            except (TypeError, ValueError):
                raise ValueError(f"{label} is not valid")

        student_ids = [as_int(sid, "Student") for sid in (data.get("student_ids") or [])]
        from_class_id = as_int(data.get("from_class_id"), "Current class")
        from_section_id = as_int(data.get("from_section_id"), "Current section")
        from_year_id = as_int(data.get("from_academic_year_id"), "Current academic year")
        to_class_id = as_int(data.get("to_class_id"), "Target class")
        to_section_id = as_int(data.get("to_section_id"), "Target section")
        to_year_id = as_int(data.get("to_academic_year_id"), "Target academic year")
        raw_date = data.get("promotion_date")
        try:
            promotion_date = datetime.strptime(str(raw_date)[:10], "%Y-%m-%d").date() if raw_date else date.today()
        except ValueError:
            raise ValueError("Promotion date is not valid")
        default_status = str(data.get("default_status") or "PASSED").upper()
        per_student_status = {str(k): str(v).upper() for k, v in (data.get("per_student_status") or {}).items()}
        remarks = (data.get("remarks") or "").strip() or None

        if not School.query.filter_by(skid=skid).first():
            raise ValueError("School not found")
        if to_year_id == from_year_id:
            raise ValueError("Choose a different academic year to promote into (use Move to change a section within the year)")

        promoted, detained, skipped = [], [], []
        with switch_to_school_db(skid) as tenant_session:
            target_class = tenant_session.query(Class).filter_by(id=to_class_id).first()
            if not target_class:
                raise ValueError("Target class not found")
            target_section = tenant_session.query(Section).filter_by(id=to_section_id).first()
            if not target_section:
                raise ValueError("Target section not found")
            if target_section.class_id != to_class_id:
                raise ValueError("The target section doesn't belong to the target class")
            if not tenant_session.query(AcademicYear).filter_by(id=to_year_id).first():
                raise ValueError("Target academic year not found")
            from_section = tenant_session.query(Section).filter_by(id=from_section_id).first()
            if not from_section or from_section.class_id != from_class_id:
                raise ValueError("The current section doesn't belong to the current class")

            for sid in student_ids:
                student = tenant_session.query(Student).filter_by(user_id=sid).first()
                name = f"{student.user.first_name} {student.user.last_name}" if student and student.user else f"Student {sid}"
                if not student:
                    skipped.append({"student_id": sid, "name": name, "error": "Student not found"})
                    continue

                # Current enrollment (case-insensitive 'active'). Older students may only have the
                # class/section on their profile and no enrollment at all: accept that placement.
                current = (
                    tenant_session.query(StudentEnrollment)
                    .filter(
                        StudentEnrollment.student_id == sid,
                        StudentEnrollment.class_id == from_class_id,
                        StudentEnrollment.section_id == from_section_id,
                        StudentEnrollment.academic_year_id == from_year_id,
                        func.lower(StudentEnrollment.status) == "active",
                    )
                    .order_by(StudentEnrollment.id.desc())
                    .first()
                )
                has_any_enrollment = tenant_session.query(StudentEnrollment).filter(StudentEnrollment.student_id == sid).first() is not None
                profile_matches = student.class_id == from_class_id and student.section_id == from_section_id
                if not current and (has_any_enrollment or not profile_matches):
                    skipped.append({"student_id": sid, "name": name, "error": "Not currently enrolled in this class/section for the current year"})
                    continue

                status = per_student_status.get(str(sid), default_status)
                is_detained = status == "FAILED"
                dest_class_id, dest_section_id = (from_class_id, from_section_id) if is_detained else (to_class_id, to_section_id)

                # Check the target BEFORE changing anything about this student
                already = (
                    tenant_session.query(StudentEnrollment)
                    .filter(
                        StudentEnrollment.student_id == sid,
                        StudentEnrollment.academic_year_id == to_year_id,
                        func.lower(StudentEnrollment.status) == "active",
                    )
                    .first()
                )
                if already:
                    skipped.append({"student_id": sid, "name": name, "error": "Already has an active enrollment in the target academic year"})
                    continue

                if current:
                    current.status = "DETAINED" if is_detained else "PROMOTED"
                    current.promotion_date = promotion_date
                    if remarks:
                        current.remarks = remarks
                tenant_session.add(StudentEnrollment(
                    student_id=sid,
                    class_id=dest_class_id,
                    section_id=dest_section_id,
                    academic_year_id=to_year_id,
                    enrollment_date=promotion_date,
                    status="active",
                    remarks=("Detained" if is_detained else "Promoted") + (f": {remarks}" if remarks else ""),
                ))
                student.class_id = dest_class_id
                student.section_id = dest_section_id
                tenant_session.add(PromotionHistory(
                    student_user_id=sid,
                    from_academic_year_id=from_year_id,
                    to_academic_year_id=to_year_id,
                    from_class_id=from_class_id,
                    to_class_id=dest_class_id,
                    from_section_id=from_section_id,
                    to_section_id=dest_section_id,
                    promotion_date=promotion_date,
                    promotion_type="DETAINED" if is_detained else "REGULAR",
                    promoted_by=promoted_by,
                    remarks=remarks,
                ))
                (detained if is_detained else promoted).append({"student_id": sid, "name": name})

            tenant_session.commit()

        return {
            "promoted_count": len(promoted),
            "detained_count": len(detained),
            "skipped_count": len(skipped),
            "total_students": len(student_ids),
            "promoted": promoted,
            "detained": detained,
            "errors": skipped or None,
        }