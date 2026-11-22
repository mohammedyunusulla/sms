from flask import Blueprint, request, jsonify
from app.services.parent_service import ParentService
from app.decorators import log_actions, login_required
from app.utils.user_status import set_school_user_active, status_response
from app.models.tenant.Parent import Parent
from app.utils.teaching_scope import (current_teacher_id, forbidden, teacher_scope_sections, strip_fields,
    STUDENT_FIELDS_HIDDEN_FROM_TEACHERS, TEACHER_FIELDS_HIDDEN_FROM_TEACHERS)

parent_bp = Blueprint('parents', __name__)

PARENT_OPTIONAL_FIELDS = (
    'relation_type', 'father_phone', 'father_occupation', 'father_qualification', 'mother_full_name',
    'mother_phone', 'mother_occupation', 'mother_qualification', 'address', 'city', 'state', 'postal_code',
    'phone', 'gender', 'date_of_birth',
)
# Father's name becomes the account's first name (school_users.first_name is NOT NULL)
PARENT_REQUIRED_FIELDS = (('username', 'Username'), ('password', 'Password'), ('father_full_name', "Father's name"))


@parent_bp.route('/create/details/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'], permission='manage_students')
@log_actions('CREATE_PARENT_USER')  
def create_parent(skid):
    """
    Create a new parent
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'message': 'No data provided'}), 400
        if not skid:
            raise ValueError("School ID (skid) is required")

        import re
        from app.utils.form_input import clean_payload, missing_fields_message, error
        from app.utils.helpers import validate_password
        data = clean_payload(data, PARENT_OPTIONAL_FIELDS)
        missing = missing_fields_message(data, PARENT_REQUIRED_FIELDS)
        if missing:
            return error(missing, 400)
        # The parent form uses the username as the login email
        data['email'] = data.get('email') or data['username']
        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', data['email']):
            return error('Username must be a valid email address', 400)
        ok, password_error = validate_password(data['password'])
        if not ok:
            return error(password_error, 400)
        data['first_name'] = data.get('first_name') or data['father_full_name']
        data['last_name'] = data.get('last_name') or data.get('mother_full_name') or ''

        # Check for duplicates
        duplicate_check = ParentService.check_duplicate_user(data, skid)
        if duplicate_check:
            return error(duplicate_check, 409)
        
        user = ParentService.create_parent_user(data, skid)
        
        return jsonify({
            'message': 'Parent created successfully',
            'data': user,
            'status': 'success',
            'code': 200
        }), 200
        
    except ValueError as e:
        return jsonify({
            'message': str(e),
            'status': 'error',
            'code': 400
        }), 400
    except Exception as e:
        return jsonify({
            'message': f'Failed to create parent: {str(e)}',
            'status': 'error',
            'code': 500
        }), 500


@parent_bp.route('/update/<skid>/<parent_id>', methods=['PUT'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'], permission='manage_students')
@log_actions('UPDATE_PARENT_USER')
def update_parent(skid, parent_id):
    """
    Update an existing parent
    Only super admin and school admin can update users
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'message': 'No data provided'}), 400
        if not skid:
            raise ValueError("School ID (skid) is required")
        if not parent_id:
            raise ValueError("Parent ID is required")
        
        # Update the parent
        updated_user = ParentService.update_parent_user(parent_id, data, skid)
        
        if not updated_user:
            return jsonify({'message': 'Parent not found'}), 404
        
        return jsonify({
            'message': 'Parent updated successfully',
            'user': updated_user,
            'status': 'success',
            'code': 200
        }), 200
        
    except ValueError as e:
        return jsonify({'message': str(e)}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to update parent: {str(e)}'}), 500


@parent_bp.route('/delete/<skid>/<parent_id>', methods=['DELETE'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'], permission=('delete_students', 'manage_students'))
@log_actions('DELETE_PARENT_USER')
def delete_parent(skid, parent_id):
    """
    Delete a parent
    Only super admin and school admin can delete users
    """
    try:
        if not skid:
            raise ValueError("School ID (skid) is required")
        if not parent_id:
            raise ValueError("Parent ID is required")
        
        # Soft delete: inactive + login disabled; all records are kept and can be reactivated.
        return status_response(set_school_user_active(skid, parent_id, False, Parent, 'Parent'))
        
    except ValueError as e:
        return jsonify({'message': str(e)}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to delete parent: {str(e)}'}), 500



@parent_bp.route('/list/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER'], permission=('view_students', 'manage_students'))
def get_parents_paginated(skid):
    """
    Get paginated list of parents in the specific school with filtering and sorting
    Query Parameters:
    - page: Page number (default: 1)
    - limit: Items per page (default: 10)
    - search: Search term for name, email, phone
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

        # A teacher sees only parents of students in the sections they teach
        section_ids = teacher_scope_sections(skid)

        # Get parents with pagination and filters
        result = ParentService.get_parents_paginated(
            skid=skid,
            page=page,
            limit=limit,
            search=search,
            status=status,
            gender=gender,
            section_ids=section_ids,
        )

        return jsonify({
            'data': result['data'],
            'meta': result['meta'],
            'status': 'success',
            'code': 200
        }), 200

    except Exception as e:
        return jsonify({
            'message': f'Failed to fetch parents: {str(e)}',
            'status': 'error',
            'code': 500
        }), 500


@parent_bp.route('/<skid>/<int:parent_id>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'], permission=('view_students', 'manage_students'))
def get_parent_detail(parent_id, skid):
    """
    Get parent details
    """
    try:
        parent = ParentService.get_parent_by_id(parent_id, skid)
        
        return jsonify({
            'message': 'Parent details fetched successfully',
            'data': parent,
            'status': 'success',
            'code': 200
        }), 200
        
    except ValueError as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 404}), 404
    except Exception as e:
        return jsonify({
            'message': f'Failed to fetch parent: {str(e)}',
            'status': 'error',
            'code': 500
        }), 500


@parent_bp.route('/link-student/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'], permission='manage_students')
@log_actions('LINK_PARENT_STUDENT')
def link_parent_student(skid):
    """
    Link parent to student
    """
    try:
        data = request.get_json()
        
        student_user_id = data.get('student_user_id')
        parent_user_id = data.get('parent_user_id')
        relation_type = data.get('relation_type', 'Guardian')
        
        if not student_user_id or not parent_user_id:
            return jsonify({
                'message': 'student_user_id and parent_user_id are required',
                'status': 'error',
                'code': 400
            }), 400
        
        result = ParentService.link_student_to_parent(
            student_user_id, parent_user_id, relation_type, skid
        )
        
        return jsonify({
            'message': 'Parent linked to student successfully',
            'data': result,
            'status': 'success',
            'code': 200
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Failed to link parent: {str(e)}',
            'status': 'error',
            'code': 500
        }), 500

@parent_bp.route('/student/<int:student_id>/parents/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'], permission=('view_students', 'manage_students'))
def get_student_parents(student_id, skid):
    """
    Get all parents for a student
    """
    try:
        parents = ParentService.get_student_parents(student_id, skid)
        
        return jsonify({
            'message': 'Student parents fetched successfully',
            'data': parents,
            'status': 'success',
            'code': 200
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Failed to fetch student parents: {str(e)}',
            'status': 'error',
            'code': 500
        }), 500


@parent_bp.route('/reactivate/<skid>/<parent_id>', methods=['PATCH'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'], permission='manage_students')
@log_actions('REACTIVATE_PARENT_USER')
def reactivate_parent(skid, parent_id):
    """Undo a soft delete: active again and login re-enabled."""
    try:
        return status_response(set_school_user_active(skid, parent_id, True, Parent, 'Parent'))
    except Exception as e:
        return jsonify({'code': 500, 'status': 'error', 'message': f'Failed to reactivate parent: {str(e)}'}), 500
