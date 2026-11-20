from app.models.main.User import User, UserRole
from app.models.tenant import Student, Teacher, SchoolUsers, TeacherSubject
from app import db
from flask import jsonify
from app.utils.db_manager import switch_to_school_db
from app.utils.helpers import generate_student_id
from app.services.userRole_service import UserRolesService
from sqlalchemy.orm import joinedload

class TeacherService:
    @staticmethod
    def create_teacher_user(data, skid):
        """
        All-or-nothing (see app/utils/account_create.py): the login is checked but saved last; the
        school record, teacher profile and role link are saved together in between.
        """
        from app.utils.account_create import add_role_link, remove_school_user, role_for
        user = None
        school_user_id = None
        tenant_saved = False
        try:
            # Main DB: add + flush only (saved at the end)
            from app.models.main.School import School
            school = School.query.filter_by(skid=skid).first()
            if not school:
                raise ValueError("School not found")
            user = User(
                username=data['username'],
                email=data['email'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                phone=data.get('phone'),
                role=UserRole.TEACHER,  # never from the request
                skid=skid,
                # from the school itself: the teacher form never sent school_id, so teacher logins had none
                # and admins couldn't switch them on/off ("Cannot deactivate user from different school")
                school_id=school.id
            )
            user.set_password(data['password'])
            db.session.add(user)
            db.session.flush()

            # Insert into tenant DB
            with switch_to_school_db(skid) as tenant_session:
                school_user = SchoolUsers(
                    username=data['username'],
                    email=data['email'],
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    phone=data.get('phone'),
                    gender=data.get('gender'),
                    date_of_birth=data.get('date_of_birth'),
                    address=data.get('address'),
                    skid=skid,
                    is_active=True
                )
                tenant_session.add(school_user)
                tenant_session.flush()
                school_user_id = school_user.id
                # Teacher role, looked up by code and saved in this same transaction
                add_role_link(tenant_session, school_user, role_for(tenant_session, 'TEACHER'))

                tenant_session.add(Teacher(
                    user_id=school_user_id,
                    # from main (bc9a858): a default when none is sent (the column is required)
                    employee_id=data.get('employee_id') or f"TCH-{skid[:6].upper()}-{school_user_id}",
                    designation=data.get('designation'),
                    date_of_joining=data.get('date_of_joining'),
                    qualifications=data.get('qualifications'),
                    salary=data.get('salary')
                ))
                tenant_session.commit()
                tenant_saved = True

            user.school_user_id = school_user_id
            db.session.commit()

            return user.to_dict()

        except Exception as e:
            db.session.rollback()
             # Rollback tenant session if open
            if 'tenant_session' in locals():
                tenant_session.rollback()
    
            # The login was never saved (rolled back above); remove the school rows if they were
            if tenant_saved:
                try:
                    remove_school_user(skid, school_user_id)
                except Exception as cleanup_err:
                    print(f"[Cleanup failed] Could not remove school user {school_user_id}: {cleanup_err}")

            raise Exception(f"Failed to create school user: {str(e)}")
            
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
                return "Teacher with this username or email already exists"
            
            # Check tenant DB
            with switch_to_school_db(skid) as tenant_session:
                existing_tenant_user = tenant_session.query(SchoolUsers).filter(
                    (SchoolUsers.username == data['username']) | (SchoolUsers.email == data['email'])
                ).first()
                
                if existing_tenant_user:
                    return "Teacher with this username or email already exists"
            
            # Check if employee ID already exists (if provided)
            if data.get('employee_id'):
                with switch_to_school_db(skid) as tenant_session:
                    existing_teacher = tenant_session.query(Teacher).filter(
                        Teacher.employee_id == data['employee_id']
                    ).first()
                    
                    if existing_teacher:
                        return "Employee ID already exists"
            
            return None  # No duplicates found
            
        except Exception as e:
            return f"Error checking for duplicates: {str(e)}"
   
   
    @staticmethod
    def update_teacher_user(teacher_id, data, skid):
        """Update teacher across main DB and tenant DB"""
        try:
            # Validate email uniqueness if being changed
            if 'email' in data and data['email']:
                existing = User.query.filter(
                    User.email == data['email'],
                    User.school_user_id != teacher_id
                ).first()
                if existing:
                    raise ValueError("Email already exists in the system")

                with switch_to_school_db(skid) as tenant_session:
                    existing_tenant = tenant_session.query(SchoolUsers).filter(
                        SchoolUsers.email == data['email'],
                        SchoolUsers.id != teacher_id
                    ).first()
                    if existing_tenant:
                        raise ValueError("Email already exists in this school")

            # Validate username uniqueness if being changed
            if 'username' in data and data['username']:
                existing = User.query.filter(
                    User.username == data['username'],
                    User.school_user_id != teacher_id
                ).first()
                if existing:
                    raise ValueError("Username already exists in the system")

                with switch_to_school_db(skid) as tenant_session:
                    existing_tenant = tenant_session.query(SchoolUsers).filter(
                        SchoolUsers.username == data['username'],
                        SchoolUsers.id != teacher_id
                    ).first()
                    if existing_tenant:
                        raise ValueError("Username already exists in this school")

            # Start with tenant database
            with switch_to_school_db(skid) as tenant_session:
                # Get teacher record
                teacher = tenant_session.query(Teacher).filter_by(user_id=teacher_id).first()
                if not teacher:
                    return None
                
                # Get school user record
                school_user = tenant_session.query(SchoolUsers).filter_by(id=teacher.user_id).first()
                if not school_user:
                    return None
                
                # Update Teacher-specific fields
                teacher_fields = ['employee_id', 'designation', 'date_of_joining', 'qualifications', 'salary']
                for key, value in data.items():
                    if key in teacher_fields and hasattr(teacher, key):
                        setattr(teacher, key, value)
                
                # Update SchoolUsers fields
                user_fields = ['first_name', 'last_name', 'email', 'phone', 'address', 'gender', 'date_of_birth']
                for key, value in data.items():
                    if key in user_fields and hasattr(school_user, key):
                        setattr(school_user, key, value)
                
                tenant_session.add(teacher)
                tenant_session.add(school_user)
                tenant_session.commit()
                
                # Now update main DB users table
                main_user = db.session.query(User).filter_by(
                    school_user_id=school_user.id,
                    skid=skid
                ).first()
                
                if main_user:
                    # Update main user fields
                    main_user_fields = ['first_name', 'last_name', 'email', 'phone', 'username']
                    for key, value in data.items():
                        if key in main_user_fields and hasattr(main_user, key):
                            setattr(main_user, key, value)
                    
                    db.session.add(main_user)
                    db.session.commit()
                
                return school_user.to_dict()
        
        except Exception as e:
            # Rollback both sessions on error
            try:
                tenant_session.rollback()
            except:
                pass
            db.session.rollback()
            raise Exception(f"Failed to update teacher: {str(e)}")
    
    
    @staticmethod
    def delete_teacher_user(teacher_id, skid):
        """Delete teacher from tenant DB and main DB"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Get teacher record
                teacher = tenant_session.query(Teacher).filter_by(user_id=teacher_id).first()
                if not teacher:
                    return None
                
                user_id = teacher.user_id
                
                # Get school user record
                school_user = tenant_session.query(SchoolUsers).filter_by(id=user_id).first()
                if not school_user:
                    return None
                
                # Delete from tenant DB (teacher first due to FK constraint)
                tenant_session.delete(teacher)
                tenant_session.delete(school_user)
                tenant_session.commit()
                
                # Delete from main DB users table
                main_user = db.session.query(User).filter_by(
                    school_user_id=user_id,
                    skid=skid,
                    role=UserRole.TEACHER
                ).first()
                
                if main_user:
                    db.session.delete(main_user)
                    db.session.commit()
                
                return True
        
        except Exception as e:
            # Rollback both sessions on error
            try:
                tenant_session.rollback()
            except:
                pass
            db.session.rollback()
            raise Exception(f"Failed to delete teacher: {str(e)}")

    @staticmethod
    def get_teacher_data(skid, school_user_id):
        """Get single teacher data by school_user_id"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                school_user = (
                    tenant_session.query(SchoolUsers)
                    .options(joinedload(SchoolUsers.teacher))
                    .filter(SchoolUsers.id == school_user_id)
                    .first()
                )
                print(school_user)
                if not school_user:
                    return None                
                return school_user.to_dict()

        except Exception as e:
            raise Exception(f"Failed to get teacher data: {str(e)}")

          
    @staticmethod
    def get_teachers_paginated(skid, page=1, limit=10, search='', status='', gender=''):
        """
        Get paginated list of teachers with filtering
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Base query
                query = (
                    tenant_session.query(SchoolUsers)
                    .join(Teacher, SchoolUsers.id == Teacher.user_id)
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
                teachers_data = query.offset(offset).limit(limit).all()

                # The list showed "-" for Employee ID / Designation: only the school-user record was returned.
                teacher_rows = {t.user_id: t for t in tenant_session.query(Teacher).filter(
                    Teacher.user_id.in_([u.id for u in teachers_data])).all()} if teachers_data else {}
                teacher_list = []
                for school_user in teachers_data:
                    item = school_user.to_dict()
                    teacher = teacher_rows.get(school_user.id)
                    item['employee_id'] = teacher.employee_id if teacher else None
                    item['designation'] = teacher.designation if teacher else None
                    item['date_of_joining'] = teacher.date_of_joining.isoformat() if teacher and teacher.date_of_joining else None
                    teacher_list.append(item)

                # Calculate total pages
                total_pages = (total + limit - 1) // limit

            # Enrich with login info from main DB (outside tenant session)
            school_user_ids = [t['id'] for t in teacher_list]
            if school_user_ids:
                main_users = User.query.filter(
                    User.school_user_id.in_(school_user_ids),
                    User.skid == skid
                ).all()
                main_user_map = {mu.school_user_id: mu for mu in main_users}
                for t in teacher_list:
                    main_user = main_user_map.get(t['id'])
                    t['has_login'] = main_user is not None
                    t['main_user_id'] = main_user.id if main_user else None
                    t['login_active'] = main_user.is_active if main_user else False

            return {
                'data': teacher_list,
                'meta': {
                    'total': total,
                    'page': page,
                    'limit': limit,
                    'totalPages': total_pages
                }
            }

        except Exception as e:
            raise Exception(f"Failed to get teachers: {str(e)}")

    @staticmethod
    def get_teachers(skid):
        try:
            with switch_to_school_db(skid) as tenant_session:
                teachers = (
                    tenant_session.query(SchoolUsers)
                    .join(Teacher, SchoolUsers.id == Teacher.user_id)
                    .all()
                )
                return [teacher.to_dict() for teacher in teachers]

        except Exception as e:
            raise Exception(f"Failed to get teachers: {str(e)}")
            
    @staticmethod
    def get_subject_ids_by_teacher(teacher_id, skid):
        """
        Returns list of subject IDs assigned to a teacher
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                subject_ids = (
                    tenant_session.query(TeacherSubject.subject_id)
                    .filter(TeacherSubject.teacher_id == teacher_id)
                    .all()
                )
                return [sid[0] for sid in subject_ids]  # Convert list of tuples to list of IDs
        except Exception as e:
            raise Exception(f"Failed to fetch teacher subjects: {str(e)}")

    @staticmethod
    def assign_subjects_to_teacher(teacher_id, subject_ids, skid):
        """
        Sync a teacher's subject assignments.
        Replaces all existing assignments with the provided subject_ids.
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Verify teacher exists
                teacher = tenant_session.query(Teacher).filter_by(user_id=teacher_id).first()
                if not teacher:
                    return None

                # Delete all existing TeacherSubject for this teacher
                tenant_session.query(TeacherSubject).filter_by(teacher_id=teacher_id).delete()

                # Create new assignments
                for sid in subject_ids:
                    tenant_session.add(TeacherSubject(teacher_id=teacher_id, subject_id=sid))

                tenant_session.commit()
                return subject_ids
        except Exception as e:
            raise Exception(f"Failed to assign subjects to teacher: {str(e)}")
