from app.models.main.User import User, UserRole
from app.models.main.School import School
from app.models.tenant import SchoolUsers, Parent, StudentParent, Student
from app import db
from sqlalchemy.exc import IntegrityError
from flask import jsonify
from app.utils.db_manager import switch_to_school_db
from app.services.userRole_service import UserRolesService
from datetime import datetime, date
from sqlalchemy.orm import joinedload
import logging
_log = logging.getLogger(__name__)


def _account_phone(data):
    """The login account's phone: the form only has father / mother phones (it used to be left empty - QA A24)."""
    return data.get('phone') or data.get('father_phone') or data.get('mother_phone')


class ParentService:
    
    @staticmethod
    def create_parent_user(data, skid):
        """
        Create a new parent user in both main and tenant databases
        Based on school plan: BASIC (no login), STANDARD/PREMIUM (with login)
        """
        from app.utils.account_create import add_role_link, remove_school_user, role_for
        user = None
        school_user_id = None
        tenant_saved = False

        try:
            # Get school information
            school = School.query.filter_by(skid=skid).first()
            if not school:
                raise ValueError("School not found")
            
            # Always the school's own plan: taking it from the request let a BASIC school's parent get a login
            plan = school.plan
            # school.plan is a SchoolPlan enum (never equal to a plain string); compare by value
            create_login = getattr(plan, 'value', plan) in ('STANDARD', 'PREMIUM')
            
            # Step 1: Create main user (only for STANDARD/PREMIUM)
            if create_login:
                user = User(
                    username=data.get('username', data['email']),
                    email=data['email'],
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    phone=_account_phone(data),
                    role=UserRole.PARENT,
                    skid=skid,
                    plan=getattr(plan, 'value', plan),  # store the plan name, not the enum object
                    school_id=school.id
                )
                user.set_password(data['password'])
                db.session.add(user)
                db.session.flush()  # Get user.id but don't commit yet
            
            # Step 2: Create tenant user (always)
            with switch_to_school_db(skid) as tenant_session:
                school_user = SchoolUsers(
                    username=data.get('username', data['email']),
                    email=data['email'],
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    phone=_account_phone(data),
                    gender=data.get('gender'),
                    date_of_birth=data.get('date_of_birth'),
                    skid=skid,
                    is_active=True
                )

                tenant_session.add(school_user)
                tenant_session.flush()
                school_user_id = school_user.id
                # Parent role, looked up by code and saved in this same transaction
                add_role_link(tenant_session, school_user, role_for(tenant_session, 'PARENT'))
                
                # Create parent profile
                parent_profile = Parent(
                    user_id=school_user_id,
                    relation_type=data.get('relation_type'),
                    father_full_name=data.get('father_full_name'),
                    father_phone=data.get('father_phone'),
                    father_occupation=data.get('father_occupation'),
                    father_qualification=data.get('father_qualification'),
                    mother_full_name=data.get('mother_full_name'),
                    mother_phone=data.get('mother_phone'),
                    mother_occupation=data.get('mother_occupation'),
                    mother_qualification=data.get('mother_qualification'),
                    address=data.get('address'),
                    city=data.get('city'),
                    state=data.get('state'),
                    postal_code=data.get('postal_code')
                )
                tenant_session.add(parent_profile)
                
                # School record + profile + role: one commit
                tenant_session.commit()
                tenant_saved = True

            # Step 3: Commit main DB only if login was created
            if create_login and user:
                user.school_user_id = school_user_id
                db.session.commit()
            
            # Step 5: Return proper object
            if create_login and user:
                return user.to_dict()
            else:
                with switch_to_school_db(skid) as tenant_session:
                    school_user = tenant_session.get(SchoolUsers, school_user_id)
                    return school_user.to_dict()
        
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
                    _log.error(f"[Cleanup failed] Could not remove school user {school_user_id}: {cleanup_err}")
            raise Exception(f"Failed to create parent user: {str(e)}")


    @staticmethod
    def check_duplicate_user(data, skid):
        """
        Check if parent already exists in both main DB and tenant DB
        Returns error message if duplicate found, None if no duplicates
        """
        try:
            username = data.get('username', data.get('email'))
            email = data.get('email')
            
            # Check main DB first
            existing_main_user = User.query.filter(
                (User.username == username) | (User.email == email)
            ).filter(User.skid == skid).first()
            
            if existing_main_user:
                return "Parent with this username or email already exists"
            
            # Check tenant DB
            with switch_to_school_db(skid) as tenant_session:
                existing_tenant_user = tenant_session.query(SchoolUsers).filter(
                    (SchoolUsers.username == username) | (SchoolUsers.email == email)
                ).first()
                
                if existing_tenant_user:
                    return "Parent with this username or email already exists"
            
            return None
            
        except Exception as e:
            return f"Error checking for duplicates: {str(e)}"
            
    @staticmethod
    def update_parent_user(parent_id, data, skid):
        """Update parent across main DB and tenant DB"""
        try:
            # Validate email uniqueness if being changed
            if 'email' in data and data['email']:
                existing = User.query.filter(
                    User.email == data['email'],
                    User.school_user_id != parent_id
                ).first()
                if existing:
                    raise ValueError("Email already exists in the system")

                with switch_to_school_db(skid) as tenant_session:
                    existing_tenant = tenant_session.query(SchoolUsers).filter(
                        SchoolUsers.email == data['email'],
                        SchoolUsers.id != parent_id
                    ).first()
                    if existing_tenant:
                        raise ValueError("Email already exists in this school")

            # Validate username uniqueness if being changed
            if 'username' in data and data['username']:
                existing = User.query.filter(
                    User.username == data['username'],
                    User.school_user_id != parent_id
                ).first()
                if existing:
                    raise ValueError("Username already exists in the system")

                with switch_to_school_db(skid) as tenant_session:
                    existing_tenant = tenant_session.query(SchoolUsers).filter(
                        SchoolUsers.username == data['username'],
                        SchoolUsers.id != parent_id
                    ).first()
                    if existing_tenant:
                        raise ValueError("Username already exists in this school")

            with switch_to_school_db(skid) as tenant_session:
                # Get school user
                school_user = tenant_session.query(SchoolUsers).filter_by(id=parent_id).first()
                if not school_user:
                    return None

                # Get parent profile
                parent = tenant_session.query(Parent).filter_by(user_id=parent_id).first()
                if not parent:
                    return None

                # Update Parent fields
                parent_fields = [
                    'relation_type', 'father_full_name', 'father_phone', 
                    'father_occupation', 'father_qualification', 'mother_full_name',
                    'mother_phone', 'mother_occupation', 'mother_qualification',
                    'address', 'city', 'state', 'postal_code'
                ]
                for key, value in data.items():
                    if key in parent_fields and hasattr(parent, key):
                        setattr(parent, key, value)
                
                # Update SchoolUsers fields
                user_fields = ['first_name', 'last_name', 'email', 'username', 'phone', 'gender', 'date_of_birth']
                # Required account columns: never overwrite them with an empty value
                required_user_fields = {'first_name', 'email', 'username'}
                for key, value in data.items():
                    if key in required_user_fields and not value:
                        continue
                    if key == 'last_name' and value is None:
                        continue
                    if key in user_fields and hasattr(school_user, key):
                        setattr(school_user, key, value)
                
                tenant_session.add(parent)
                tenant_session.add(school_user)
                tenant_session.commit()
                
                # Update main DB if user exists
                main_user = db.session.query(User).filter_by(
                    school_user_id=school_user.id,
                    skid=skid
                ).first()
                
                if main_user:
                    main_user_fields = ['first_name', 'last_name', 'email', 'username', 'phone']
                    for key, value in data.items():
                        if key in required_user_fields and not value:
                            continue
                        if key == 'last_name' and value is None:
                            continue
                        if key in main_user_fields and hasattr(main_user, key):
                            setattr(main_user, key, value)
                    
                    db.session.add(main_user)
                    db.session.commit()
                
                return school_user.to_dict()
        
        except Exception as e:
            try:
                tenant_session.rollback()
            except:
                pass
            db.session.rollback()
            raise Exception(f"Failed to update parent: {str(e)}")
    
    
    @staticmethod
    def delete_parent_user(parent_id, skid):
        """Delete parent from tenant DB and main DB""" 
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Get school user
                school_user = tenant_session.query(SchoolUsers).filter_by(id=parent_id).first()
                if not school_user:
                    return None
                
                # Get parent profile
                parent = tenant_session.query(Parent).filter_by(user_id=parent_id).first()
                if not parent:
                    return None
                
                # Delete from tenant DB (parent first due to FK constraint)
                tenant_session.delete(parent)
                tenant_session.delete(school_user)
                tenant_session.commit()
                
                # Delete from main DB if exists
                main_user = db.session.query(User).filter_by(
                    school_user_id=parent_id,
                    skid=skid,
                    role=UserRole.PARENT
                ).first()
                
                if main_user:
                    db.session.delete(main_user)
                    db.session.commit()
                
                return True
        
        except Exception as e:
            try:
                tenant_session.rollback()
            except:
                pass
            db.session.rollback()
            raise Exception(f"Failed to delete parent: {str(e)}")
    
    
    @staticmethod
    def get_parents_paginated(skid, page=1, limit=10, search='', status='', gender='', section_ids=None):
        """
        Get paginated list of parents with filtering
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Base query
                query = (
                    tenant_session.query(SchoolUsers)
                    .join(Parent, SchoolUsers.id == Parent.user_id)
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

                # A teacher sees only parents of students in the sections they teach
                if section_ids is not None:
                    query = query.filter(SchoolUsers.id.in_(
                        tenant_session.query(StudentParent.parent_user_id)
                        .join(Student, Student.user_id == StudentParent.student_user_id)
                        .filter(Student.section_id.in_(list(section_ids)))
                    ))

                # Get total count before pagination
                total = query.count()

                # Apply pagination
                offset = (page - 1) * limit
                parents_data = query.offset(offset).limit(limit).all()

                parent_list = [parent.to_dict() for parent in parents_data]

                # Calculate total pages
                total_pages = (total + limit - 1) // limit

            # Enrich with login info from main DB (outside tenant session)
            school_user_ids = [p['id'] for p in parent_list]
            if school_user_ids:
                main_users = User.query.filter(
                    User.school_user_id.in_(school_user_ids),
                    User.skid == skid
                ).all()
                main_user_map = {mu.school_user_id: mu for mu in main_users}
                for p in parent_list:
                    main_user = main_user_map.get(p['id'])
                    p['has_login'] = main_user is not None
                    p['main_user_id'] = main_user.id if main_user else None
                    p['login_active'] = main_user.is_active if main_user else False

            return {
                'data': parent_list,
                'meta': {
                    'total': total,
                    'page': page,
                    'limit': limit,
                    'totalPages': total_pages
                }
            }

        except Exception as e:
            raise Exception(f"Failed to fetch parents: {str(e)}")

    @staticmethod
    def get_all_parents(skid):
        """
        Get all parents for a school (legacy method)
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                parents = (
                    tenant_session.query(SchoolUsers)
                    .options(
                        joinedload(SchoolUsers.parent),
                        joinedload(SchoolUsers.role_obj)
                    )
                    .join(Parent, SchoolUsers.id == Parent.user_id)
                    .filter(
                        SchoolUsers.role_id == 5,  # Parent role
                        SchoolUsers.is_active == True
                    )
                    .all()
                )

                return [parent.to_dict() for parent in parents]
        except Exception as e:
            raise Exception(f"Failed to fetch parents: {str(e)}")

    @staticmethod
    def get_parent_by_id(parent_id, skid):
        """
        Get parent details by ID
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                parent = tenant_session.query(Parent).filter(
                    Parent.user_id == parent_id
                ).first()

                if not parent:
                    raise ValueError("Parent not found")

                # The profile used to be all there was: no username / email / active status (the detail showed
                # "Inactive", editing showed a blank username) and no children (QA A23/A25/A26).
                user = tenant_session.query(SchoolUsers).filter_by(id=parent.user_id).first()
                result = parent.to_dict()
                if user:
                    result.update({
                        'username': user.username, 'email': user.email, 'phone': user.phone,
                        'first_name': user.first_name, 'last_name': user.last_name,
                        'full_name': f"{user.first_name} {user.last_name or ''}".strip(),
                        'is_active': user.is_active,
                    })
                from app.models.tenant import Class
                from app.models.tenant.Sections import Section
                children = []
                for link, child, child_user in tenant_session.query(StudentParent, Student, SchoolUsers).join(
                    Student, Student.user_id == StudentParent.student_user_id
                ).join(
                    SchoolUsers, SchoolUsers.id == Student.user_id
                ).filter(StudentParent.parent_user_id == parent.user_id).all():
                    cls = tenant_session.query(Class).filter_by(id=child.class_id).first() if child.class_id else None
                    sec = tenant_session.query(Section).filter_by(id=child.section_id).first() if child.section_id else None
                    children.append({
                        'student_user_id': child.user_id,
                        'name': f"{child_user.first_name} {child_user.last_name or ''}".strip(),
                        'admission_number': child.admission_number,
                        'class_name': cls.class_name if cls else None,
                        'section_name': sec.section_name if sec else None,
                        'relation_type': getattr(link.relation_type, 'value', link.relation_type),
                        'is_active': child_user.is_active,
                    })
                result['children'] = children
                return result
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to fetch parent: {str(e)}")

    @staticmethod
    def link_student_to_parent(student_user_id, parent_user_id, relation_type, skid):
        """
        Link existing student to existing parent
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Check if relationship already exists
                existing_link = tenant_session.query(StudentParent).filter(
                    StudentParent.student_user_id == student_user_id,
                    StudentParent.parent_user_id == parent_user_id
                ).first()
                
                if existing_link:
                    raise ValueError("Student is already linked to this parent")
                
                # Verify student and parent exist
                student = tenant_session.query(Student).filter(
                    Student.user_id == student_user_id
                ).first()
                parent = tenant_session.query(Parent).filter(
                    Parent.user_id == parent_user_id
                ).first()
                
                if not student:
                    raise ValueError("Student not found")
                if not parent:
                    raise ValueError("Parent not found")
                
                # Create new relationship
                student_parent = StudentParent(
                    student_user_id=student_user_id,
                    parent_user_id=parent_user_id,
                    relation_type=relation_type
                )
                tenant_session.add(student_parent)
                tenant_session.commit()
                
                return {"success": True, "message": "Student linked to parent successfully"}
        except Exception as e:
            raise Exception(f"Failed to link student to parent: {str(e)}")

    @staticmethod
    def get_student_parents(student_user_id, skid):
        """
        Get all parents linked to a student
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                parents = tenant_session.query(Parent, StudentParent.relation_type).join(
                    StudentParent, Parent.user_id == StudentParent.parent_user_id
                ).filter(
                    StudentParent.student_user_id == student_user_id
                ).all()
                
                return [
                    {
                        "id": parent.user_id,
                        "name": f"{parent.first_name} {parent.last_name}",
                        "first_name": parent.first_name,
                        "last_name": parent.last_name,
                        "email": parent.email,
                        "phone": parent.phone_number,
                        "relation_type": relation_type,
                        "occupation": parent.occupation,
                        "education_level": parent.education_level
                    }
                    for parent, relation_type in parents
                ]
        except Exception as e:
            raise Exception(f"Failed to fetch student parents: {str(e)}")

    @staticmethod
    def unlink_student_parent(student_user_id, parent_user_id, skid):
        """
        Unlink student from parent
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                student_parent = tenant_session.query(StudentParent).filter(
                    StudentParent.student_user_id == student_user_id,
                    StudentParent.parent_user_id == parent_user_id
                ).first()
                
                if not student_parent:
                    raise ValueError("Student-parent relationship not found")
                
                tenant_session.delete(student_parent)
                tenant_session.commit()
                
                return {"success": True, "message": "Student unlinked from parent successfully"}
        except Exception as e:
            raise Exception(f"Failed to unlink student from parent: {str(e)}")

    @staticmethod
    def update_parent(parent_id, data, skid):
        """
        Update parent information
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                parent = tenant_session.query(Parent).filter(
                    Parent.user_id == parent_id
                ).first()
                
                if not parent:
                    raise ValueError("Parent not found")
                
                # Update parent profile
                parent.first_name = data.get('first_name', parent.first_name)
                parent.last_name = data.get('last_name', parent.last_name)
                parent.email = data.get('email', parent.email)
                parent.phone_number = data.get('phone', parent.phone_number)
                parent.occupation = data.get('occupation', parent.occupation)
                parent.education_level = data.get('education_level', parent.education_level)
                
                # Update school user
                school_user = tenant_session.query(SchoolUsers).filter(
                    SchoolUsers.id == parent_id
                ).first()
                
                if school_user:
                    school_user.first_name = data.get('first_name', school_user.first_name)
                    school_user.last_name = data.get('last_name', school_user.last_name)
                    school_user.email = data.get('email', school_user.email)
                    school_user.phone_number = data.get('phone', school_user.phone_number)
                
                tenant_session.commit()
                
                return parent
        except Exception as e:
            raise Exception(f"Failed to update parent: {str(e)}")