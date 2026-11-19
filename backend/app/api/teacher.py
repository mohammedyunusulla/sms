from flask import Blueprint, request, jsonify
from app.services.teacher_service import TeacherService
from app.decorators import log_actions, login_required
from app.utils.user_status import set_school_user_active, status_response
from app.models.tenant.Teacher import Teacher
from app.models.main.User import UserRole

teacher_bp = Blueprint('teachers', __name__)

@teacher_bp.route('/create/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
@log_actions('CREATE_TEACHER_USER')
def create_teacher(skid):
    """
    Create a new teacher
    Only super admin and school admin can create users
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'message': 'No data provided'}), 400
        if not skid:
            raise ValueError("School ID (skid) is required")
        
        # Check for duplicate before creating
        duplicate_check = TeacherService.check_duplicate_user(data, skid)
        if duplicate_check:
            return jsonify({'message': duplicate_check, 'status': 'exists', 'code': 200}), 200
        
        user = TeacherService.create_teacher_user(data, skid)
        
        return jsonify({
            'message': 'User created successfully',
            'user': user,
            'status': 'success',
            'code': 200
        }), 200
        
    except ValueError as e:
        return jsonify({'message': str(e)}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to create user: {str(e)}'}), 500


@teacher_bp.route('/update/<skid>/<teacher_id>', methods=['PUT'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL'])
@log_actions('UPDATE_TEACHER_USER')
def update_teacher(skid, teacher_id):
    """
    Update an existing teacher
    Only super admin and school admin can update users
    Teacher can update there own profile after login, with restricted fields
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'message': 'No data provided'}), 400
        if not skid:
            raise ValueError("School ID (skid) is required")
        if not teacher_id:
            raise ValueError("Teacher ID is required")
        
        updated_user = TeacherService.update_teacher_user(teacher_id, data, skid)
        
        if not updated_user:
            return jsonify({'message': 'Teacher not found'}), 404
        
        return jsonify({
            'message': 'User updated successfully',
            'user': updated_user,
            'status': 'success',
            'code': 200
        }), 200
        
    except ValueError as e:
        return jsonify({'message': str(e)}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to update user: {str(e)}'}), 500


@teacher_bp.route('/delete/<skid>/<teacher_id>', methods=['DELETE'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
@log_actions('DELETE_TEACHER_USER')
def delete_teacher(skid, teacher_id):
    """
    Delete a teacher
    Only super admin and school admin can delete users
    """
    try:
        if not skid:
            raise ValueError("School ID (skid) is required")
        if not teacher_id:
            raise ValueError("Teacher ID is required")
        
        # Soft delete: inactive + login disabled; all records are kept and can be reactivated.
        return status_response(set_school_user_active(skid, teacher_id, False, Teacher, 'Teacher'))
        
    except ValueError as e:
        return jsonify({'message': str(e)}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to delete user: {str(e)}'}), 500

 
@teacher_bp.route('/profile/<skid>/<school_user_id>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'TEACHER'])
@log_actions('GET_TEACHERS')
def get_teacher_data_by_id(skid, school_user_id):
    """
    Get data of single teacher by school_user_id
    """
    try:
        if not skid:
            raise ValueError("School ID (skid) is required")
            
        teacher_data = TeacherService.get_teacher_data(skid, school_user_id)

        return jsonify({
            'teacher_data': teacher_data,
            'status': 'success',
            'code': 200
        }), 200
   
    except Exception as e:
        return jsonify({'message': f'Failed to get teacher data: {str(e)}'}), 500
 
 
@teacher_bp.route('/list/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER'])
@log_actions('GET_TEACHERS')
def get_teachers_paginated(skid):
    """
    Get paginated list of teachers in the specific school with filtering and sorting
    Query Parameters:
    - page: Page number (default: 1)
    - limit: Items per page (default: 10)
    - search: Search term for name, email, phone, employee_id
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

        # Get teachers with pagination and filters
        result = TeacherService.get_teachers_paginated(
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
        return jsonify({'message': f'Failed to get teachers: {str(e)}'}), 500

# Fetch the subjects assigned to that teacher
@teacher_bp.route('/<int:teacher_id>/subjects/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
def get_teacher_subjects(teacher_id, skid):
    try:
        subject_ids = TeacherService.get_subject_ids_by_teacher(teacher_id, skid)
        return jsonify({
            "subject_ids": subject_ids,
            'status': 'success',
            'code': 200
        }), 200
    except Exception as e:
        return jsonify(message=str(e))


# Assign subjects to a teacher (sync/replace all assignments)
@teacher_bp.route('/<int:teacher_id>/assign-subjects/<skid>', methods=['PUT'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
@log_actions('ASSIGN_SUBJECTS_TO_TEACHER')
def assign_subjects_to_teacher(teacher_id, skid):
    """
    Sync a teacher's subject assignments.
    Replaces all existing assignments with the provided subject_ids.
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'message': 'No data provided'}), 400
        if not skid:
            return jsonify({'message': 'School ID (skid) is required'}), 400

        subject_ids = data.get('subject_ids', [])
        if not isinstance(subject_ids, list):
            return jsonify({'message': 'subject_ids must be a list'}), 400

        result = TeacherService.assign_subjects_to_teacher(teacher_id, subject_ids, skid)

        if result is None:
            return jsonify({'message': 'Teacher not found'}), 404

        return jsonify({
            'message': 'Subjects assigned successfully',
            'subject_ids': result,
            'status': 'success',
            'code': 200
        }), 200

    except Exception as e:
        return jsonify({'message': f'Failed to assign subjects: {str(e)}'}), 500


@teacher_bp.route('/reactivate/<skid>/<teacher_id>', methods=['PATCH'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL'])
@log_actions('REACTIVATE_TEACHER_USER')
def reactivate_teacher(skid, teacher_id):
    """Undo a soft delete: active again and login re-enabled."""
    try:
        return status_response(set_school_user_active(skid, teacher_id, True, Teacher, 'Teacher'))
    except Exception as e:
        return jsonify({'code': 500, 'status': 'error', 'message': f'Failed to reactivate teacher: {str(e)}'}), 500
