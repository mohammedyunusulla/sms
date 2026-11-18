from flask import Blueprint, request, jsonify
from app.services.student_service import StudentService
from app.decorators import log_actions, login_required
from app.models.main.User import UserRole

student_bp = Blueprint('students', __name__)

@student_bp.route('/create/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
@log_actions('CREATE_TEACHER_USER')
def create_student(skid):
    """
    Create a new student
    Only super admin and school admin can create users
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'message': 'No data provided'}), 400
        if not skid:
            return jsonify({'message': 'School ID is required'}), 400
        
        duplicate_check = StudentService.check_duplicate_user(data, skid)
        if duplicate_check:
            return jsonify({'message': duplicate_check}), 400

        StudentService.create_student_user(data, skid)

        return jsonify({
            'message': 'Student created successfully',
            'status': 'success',
            'code': 200
        }), 200
        
    except ValueError as e:
        return jsonify({'message': str(e)}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to create user: {str(e)}'}), 500


@student_bp.route('/bulk-create/<skid>', methods=['POST'])
@login_required(['PRINCIPAL', 'SCHOOL_ADMIN'])
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
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
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
          Step 1: Get school plan
          Step 2: Fetch from main DB (if plan allows login)
          Step 3: Fetch from tenant DB to verify exists
          Step 4: Update main DB (if plan allows login)
          Step 5: Update tenant DB (ALWAYS)
          Step 6: Return response
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No data provided'}), 400

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
                return jsonify({'message': duplicate_check}), 400

        StudentService.update_student(student_id, skid, data)

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
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER'])
@log_actions('GET_STUDENTS')
def get_students_paginated(skid):
    """
    Get paginated list of students in the specific school with filtering and sorting
    Query Parameters:
    - page: Page number (default: 1)
    - limit: Items per page (default: 10)
    - search: Search term for name, email, phone, student_id
    - status: Filter by status (active, inactive)
    - gender: Filter by gender (Male, Female, Other)
    """
    try:
        if not skid:
            raise ValueError("School ID (skid) is required")

        # Get query parameters
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        search = request.args.get('search', '', type=str)
        status = request.args.get('status', '', type=str)
        gender = request.args.get('gender', '', type=str)

        # Validate pagination parameters
        page = max(1, page)
        limit = max(1, min(limit, 100))  # Limit max 100 items per page

        # Get students with pagination and filters
        result = StudentService.get_students_paginated(
            skid=skid,
            page=page,
            limit=limit,
            search=search,
            status=status,
            gender=gender
        )

        return jsonify({
            'data': result['data'],
            'meta': result['meta'],
            'status': 'success',
            'code': 200
        }), 200

    except Exception as e:
        return jsonify({'message': f'Failed to get students: {str(e)}'}), 500


@student_bp.route('/list/<skid>/<academic_year_id>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
@log_actions('GET_STUDENTS')
def get_students(skid, academic_year_id):
    """
    Get list of students for a specific academic year (legacy endpoint)
    """
    try:
        if not skid:
            raise ValueError("School ID (skid) is required")

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
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'TEACHER'])
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
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
@log_actions('GET_STUDENTS')
def get_student_by_id(skid, id):
    """
    Get list of students
    """
    try:
        if not skid:
            raise ValueError("School ID (skid) is required")
            
        student = StudentService.get_student_by_id(skid, id)

        return jsonify({
            'student': student,
            'status': 'success',
            'code': 200
        }), 200
   
    except Exception as e:
        return jsonify({'message': f'Failed to get students: {str(e)}'}), 500
        

@student_bp.route('/promote/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
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
            return jsonify({'message': 'School ID is required'}), 400
        
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
        result = StudentService.promote_students(data, skid)
        
        return jsonify({
            'message': 'Students promoted successfully',
            'data': result,
            'status': 'success',
            'code': 200
        }), 200
        
    except ValueError as e:
        return jsonify({'message': str(e)}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to promote students: {str(e)}'}), 500