from flask import Blueprint, request, jsonify
from app.services.student_service import StudentService
from app.decorators import log_actions, login_required
from app.models.main.User import UserRole
from app.utils.teaching_scope import (current_teacher_id, forbidden, teacher_scope_sections, strip_fields,
    STUDENT_FIELDS_HIDDEN_FROM_TEACHERS, TEACHER_FIELDS_HIDDEN_FROM_TEACHERS)

student_bp = Blueprint('students', __name__)

# Blank optional fields are stored as NULL ('' breaks class/section/roll numbers and unique admission_number)
STUDENT_OPTIONAL_FIELDS = (
    'gender', 'date_of_birth', 'blood_group', 'emergency_contact', 'address', 'admission_number',
    'aadhar_number', 'birth_certificate_number', 'nationality', 'religion', 'category', 'mother_tongue',
    'roll_no', 'admission_date', 'class_id', 'section_id', 'parent_id',
)
STUDENT_REQUIRED_FIELDS = (
    ('username', 'Username'), ('password', 'Password'), ('first_name', 'First name'),
    ('last_name', 'Last name'), ('email', 'Email'), ('phone', 'Phone'),
)


def _link_parent(skid, student_user_id, parent_id):
    """Save the parent chosen in the student form (create or change the student_parents link)."""
    if not parent_id:
        return None
    from app.services.studentParent_service import StudentParentService
    return StudentParentService.update_student_parent_link(int(student_user_id), int(parent_id), 'Guardian', skid)


def _institution_user_id_for(skid, username):
    from app.models.tenant import InstitutionUsers
    from app.utils.db_manager import switch_to_institution_db
    with switch_to_institution_db(skid) as tenant_session:
        su = tenant_session.query(InstitutionUsers).filter_by(username=username).first()
        return su.id if su else None


def _admission_number_taken(skid, admission_number, exclude_user_id=None):
    """students.admission_number is unique in the tenant DB."""
    from app.models.tenant import Student
    from app.utils.db_manager import switch_to_institution_db
    with switch_to_institution_db(skid) as tenant_session:
        q = tenant_session.query(Student).filter(Student.admission_number == admission_number)
        if exclude_user_id is not None:
            q = q.filter(Student.user_id != int(exclude_user_id))
        return q.first() is not None

@student_bp.route('/create/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN'], permission='manage_students')
@log_actions('CREATE_TEACHER_USER')
def create_student(skid):
    """
    Create a new student
    Only super admin and institution admin can create users
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'message': 'No data provided'}), 400
        if not skid:
            return jsonify({'message': 'Institution ID is required'}), 400

        from app.utils.form_input import clean_payload, missing_fields_message, error
        from app.utils.helpers import validate_password
        data = clean_payload(data, STUDENT_OPTIONAL_FIELDS)
        # Where student sign-in is switched off no login is made, so no password is asked for
        from app.utils.features import login_enabled
        creates_login = login_enabled(skid, 'STUDENT')
        required = STUDENT_REQUIRED_FIELDS if creates_login else tuple(f for f in STUDENT_REQUIRED_FIELDS if f[0] != 'password')
        missing = missing_fields_message(data, required)
        if missing:
            return error(missing, 400)
        if creates_login:
            ok, password_error = validate_password(data['password'])
            if not ok:
                return error(password_error, 400)
        else:
            data.pop('password', None)

        duplicate_check = StudentService.check_duplicate_user(data, skid)
        if duplicate_check:
            return error(duplicate_check, 500 if duplicate_check.startswith('Error checking') else 409)
        if data.get('admission_number') and _admission_number_taken(skid, data['admission_number']):
            return error(f"Admission number '{data['admission_number']}' is already used by another student", 409)

        StudentService.create_student_user(data, skid)

        # Link the parent picked in the form (this used to be silently dropped)
        message = 'Student created successfully'
        if data.get('parent_id'):
            try:
                _link_parent(skid, _institution_user_id_for(skid, data['username']), data['parent_id'])
            except Exception as link_error:
                message = f'Student created, but linking the parent failed: {link_error}'

        return jsonify({
            'message': message,
            'status': 'success',
            'code': 200
        }), 200
        
    except ValueError as e:
        return jsonify({'message': str(e)}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to create user: {str(e)}'}), 500


@student_bp.route('/bulk-create/<skid>', methods=['POST'])
@login_required(['PRINCIPAL', 'INSTITUTION_ADMIN'], permission='manage_students')
def bulk_create_students(skid):
    """
    Bulk create students from uploaded data
    Expected JSON: {
        "students": [...student data...],
        "default_password": "Admin@123"
    }
    """
    try:
        data = request.get_json()
        students_data = data.get('students', [])
        default_password = data.get('default_password', 'Admin@123')
        
        if not students_data:
            return jsonify({
                'code': 400,
                'status': 'error',
                'message': 'No student data provided'
            }), 400
        
        # Call the service method
        result = StudentService.bulk_create_students(
            students_data=students_data,
            skid=skid,
            default_password=default_password
        )
        
        return jsonify({
            'code': 200,
            'status': 'success',
            'message': f'Bulk import completed. {result["successful"]} successful, {result["failed"]} failed.',
            'data': result
        }), 200
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'status': 'error',
            'message': str(e)
        }), 500


@student_bp.route('/update/<skid>/<student_id>', methods=['PUT'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN'], permission='manage_students')
@log_actions('UPDATE-STUDENT')
def update_student(skid, student_id):
    """
    Update existing student
    Checks for duplicate username/email before updating
    
    Flow Diagram:
      API Route (student.py)
          ↓
      Check duplicates with check_duplicate_user_for_update()
          ↓ (if no duplicates)
      Service Layer (student_service.py:update_student)
          ↓
          Step 1: Is student sign-in on for the institution?
          Step 2: Fetch from main DB (if the student has a login)
          Step 3: Fetch from tenant DB to verify exists
          Step 4: Update main DB (if the student has a login)
          Step 5: Update tenant DB (ALWAYS)
          Step 6: Return response
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No data provided'}), 400

        from app.utils.form_input import clean_payload, error
        data = clean_payload(data, STUDENT_OPTIONAL_FIELDS)
        for key, label in STUDENT_REQUIRED_FIELDS:
            if key != 'password' and key in data and not data[key]:
                return error(f'{label} is required', 400)
        if data.get('admission_number') and _admission_number_taken(skid, data['admission_number'], exclude_user_id=student_id):
            return error(f"Admission number '{data['admission_number']}' is already used by another student", 409)

        # Check for duplicates (excluding current student)
        # Only check fields that are being updated
        check_data = {}
        if 'username' in data:
            check_data['username'] = data['username']
        if 'email' in data:
            check_data['email'] = data['email']
        if 'roll_no' in data:
            check_data['roll_no'] = data['roll_no']

        if check_data:
            duplicate_check = StudentService.check_duplicate_user_for_update(check_data, skid, int(student_id))
            if duplicate_check:
                return error(duplicate_check, 500 if duplicate_check.startswith('Error checking') else 409)

        StudentService.update_student(student_id, skid, data)
        # Save a changed parent (no parent_id sent = leave the existing link alone)
        if data.get('parent_id'):
            _link_parent(skid, student_id, data['parent_id'])

        return jsonify({
            'message': 'Student updated successfully',
            'status': 'success',
            'code': 200
        }), 200

    except ValueError as e:
        return jsonify({'message': str(e)}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to update student: {str(e)}'}), 500


@student_bp.route('/list/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN', 'PRINCIPAL', 'TEACHER', 'CLERK'], permission=('view_students', 'manage_students'))
@log_actions('GET_STUDENTS')
def get_students_paginated(skid):
    """
    Get paginated list of students in the specific institution with filtering and sorting
    Query Parameters:
    - page: Page number (default: 1)
    - limit: Items per page (default: 10)
    - search: Search term for name, email, phone, student_id
    - status: Filter by status (active, inactive)
    - gender: Filter by gender (Male, Female, Other)
    """
    try:
        if not skid:
            raise ValueError("Institution ID (skid) is required")

        # Get query parameters
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        search = request.args.get('search', '', type=str)
        status = request.args.get('status', '', type=str)
        gender = request.args.get('gender', '', type=str)

        # Validate pagination parameters
        page = max(1, page)
        limit = max(1, min(limit, 100))  # Limit max 100 items per page

        # Get students with pagination and filters (a teacher: only their sections)
        section_ids = teacher_scope_sections(skid)
        result = StudentService.get_students_paginated(
            skid=skid,
            page=page,
            limit=limit,
            search=search,
            status=status,
            gender=gender,
            section_ids=section_ids,
            class_id=request.args.get('class_id', type=int),
            section_id=request.args.get('section_id', type=int),
        )
        if section_ids is not None:
            strip_fields(result['data'], STUDENT_FIELDS_HIDDEN_FROM_TEACHERS)

        return jsonify({
            'data': result['data'],
            'meta': result['meta'],
            'status': 'success',
            'code': 200
        }), 200

    except Exception as e:
        return jsonify({'message': f'Failed to get students: {str(e)}'}), 500


@student_bp.route('/list/<skid>/<academic_year_id>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN', 'CLERK'], permission=('view_students', 'manage_students'))
@log_actions('GET_STUDENTS')
def get_students(skid, academic_year_id):
    """
    Get list of students for a specific academic year (legacy endpoint)
    """
    try:
        if not skid:
            raise ValueError("Institution ID (skid) is required")

        students = StudentService.get_students(skid, academic_year_id)

        return jsonify({
            'students': students,
            'status': 'success',
            'code': 200
        }), 200

    except Exception as e:
        return jsonify({'message': f'Failed to get students: {str(e)}'}), 500

# Fetch student list for the section based on the sectionId
@student_bp.route('/list/inSection/<skid>/<academic_year_id>/<int:section_id>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN', 'TEACHER', 'CLERK'], permission=('view_students', 'manage_students', 'manage_attendance', 'view_attendance', 'manage_marks', 'manage_assignments'))
def get_students_for_section(skid, academic_year_id, section_id):
    """
    Get all students for a specific class-section with pagination and filtering
    Query Parameters:
        - page: Page number (default: 1)
        - limit: Items per page (default: 10)
        - search: Search by name or email
        - gender: Filter by gender (Male, Female, Other)
        - status: Filter by status (active, inactive)
    """
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        search = request.args.get('search', '', type=str)
        gender = request.args.get('gender', '', type=str)
        status = request.args.get('status', '', type=str)

        # Validate pagination params
        if page < 1:
            page = 1
        if limit < 1 or limit > 100:
            limit = 10

        # A teacher may only list the sections they teach
        section_ids = teacher_scope_sections(skid)
        if section_ids is not None and section_id not in section_ids:
            return forbidden("You can only see students of the sections you teach")

        # Call service with filters
        result = StudentService.get_students_for_section(
            skid=skid,
            academic_year_id=academic_year_id,
            section_id=section_id,
            page=page,
            limit=limit,
            search=search,
            gender=gender,
            status=status
        )
        if section_ids is not None:
            strip_fields(result['students'], STUDENT_FIELDS_HIDDEN_FROM_TEACHERS)

        return jsonify({
            'message': 'Students retrieved successfully',
            'data': result['students'],
            'meta': {
                'total': result['total'],
                'page': page,
                'limit': limit,
                'totalPages': result['totalPages']
            },
            'status': 'success',
            'code': 200
        }), 200

    except Exception as e:
        return jsonify({'message': f'Failed to retrieve students: {str(e)}', 'status': 'error', 'code': 500}), 500

@student_bp.route('/get-by-id/<skid>/<int:id>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN', 'CLERK'], permission=('view_students', 'manage_students'))
@log_actions('GET_STUDENTS')
def get_student_by_id(skid, id):
    """
    Get list of students
    """
    try:
        if not skid:
            raise ValueError("Institution ID (skid) is required")
            
        student = StudentService.get_student_by_id(skid, id)

        return jsonify({
            'student': student,
            'status': 'success',
            'code': 200
        }), 200
   
    except Exception as e:
        return jsonify({'message': f'Failed to get students: {str(e)}'}), 500
        

@student_bp.route('/promote/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN'], permission='manage_students')
@log_actions('PROMOTE_STUDENTS')
def promote_students(skid):
    """
    Promote a list of students from one class/section/year to another.
    Request Body:
    {
      "student_ids": [1, 2, 3],
      "from_class_id": 10,
      "from_section_id": 3,
      "from_academic_year_id": 2,
      "to_class_id": 11,
      "to_section_id": 1,
      "to_academic_year_id": 3,
      "promotion_date": "2026-04-01",
      "default_status": "PASSED",
      "per_student_status": {"1": "PASSED", "2": "FAILED"},
      "remarks": "Annual promotion"
    }
    Returns:
        JSON response with promotion result
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'message': 'No data provided'}), 400
            
        if not skid:
            return jsonify({'message': 'Institution ID is required'}), 400
        
        # Validate required fields
        student_ids = data.get("student_ids") or []
        if not student_ids:
            return jsonify({"message": "No students selected"}), 400

        required_fields = [
            'from_class_id', 'from_section_id', 'from_academic_year_id',
            'to_class_id', 'to_section_id', 'to_academic_year_id'
        ]
        
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return jsonify({
                "message": f"Missing required fields: {', '.join(missing_fields)}"
            }), 400
        
        # Call service method
        result = StudentService.promote_students(data, skid, promoted_by=request.current_user.institution_user_id)

        # Report what really happened (it used to say "promoted successfully" even when nobody moved)
        moved = result['promoted_count'] + result['detained_count']
        parts = []
        if result['promoted_count']:
            parts.append(f"{result['promoted_count']} promoted")
        if result['detained_count']:
            parts.append(f"{result['detained_count']} detained (kept in the same class)")
        if result['skipped_count']:
            parts.append(f"{result['skipped_count']} skipped")
        summary = f"{', '.join(parts)} of {result['total_students']}"
        if moved == 0:
            first = (result['errors'] or [{}])[0]
            return jsonify({
                'message': f"No students were promoted: {first.get('name', '')} - {first.get('error', 'unknown reason')}"
                if len(result['errors'] or []) == 1 else f"No students were promoted ({summary}). First reason: {first.get('error')}",
                'data': result,
                'status': 'error',
                'code': 400,
            }), 400
        return jsonify({
            'message': summary[0].upper() + summary[1:],
            'data': result,
            'status': 'success',
            'code': 200
        }), 200

    except ValueError as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to promote students: {str(e)}'}), 500

def _set_student_active_response(skid, student_id, active):
    result = StudentService.set_student_active(skid, student_id, active)
    if result['success']:
        return jsonify({'code': 200, 'status': 'success', 'message': result['message'], 'data': result['data']}), 200
    return jsonify({'code': result['code'], 'status': 'error', 'message': result['message']}), result['code']


@student_bp.route('/delete/<int:student_id>/<skid>', methods=['DELETE'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN', 'PRINCIPAL'], permission='delete_students')
@log_actions('DEACTIVATE_STUDENT')
def delete_student(student_id, skid):
    """Soft delete: mark the student inactive and disable their login. All records are kept."""
    try:
        return _set_student_active_response(skid, student_id, False)
    except Exception as e:
        return jsonify({'code': 500, 'status': 'error', 'message': f'Failed to delete student: {str(e)}'}), 500


@student_bp.route('/reactivate/<int:student_id>/<skid>', methods=['PATCH'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN', 'PRINCIPAL'], permission='manage_students')
@log_actions('REACTIVATE_STUDENT')
def reactivate_student(student_id, skid):
    """Undo a soft delete: mark the student active and re-enable their login."""
    try:
        return _set_student_active_response(skid, student_id, True)
    except Exception as e:
        return jsonify({'code': 500, 'status': 'error', 'message': f'Failed to reactivate student: {str(e)}'}), 500
