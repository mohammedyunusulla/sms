# app/routes/studentParent_routes.py
from flask import Blueprint, request, jsonify
from app.services.studentParent_service import StudentParentService 
from app.decorators import login_required
from app.decorators.auth import own_parent_required

studentParent_bp = Blueprint('studentParent', __name__)

# ASSIGN STUDENTS TO PARENT
@studentParent_bp.route('/assign/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'], permission='manage_students')
def assign_students_to_parent(skid):
    try:
        data = request.get_json()
        
        if not skid:
            raise ValueError("School ID (skid) is required")
        
        # Validate required fields
        if not data or 'parent_user_id' not in data or 'student_user_ids' not in data:
            raise ValueError("parent_user_id and student_user_ids are required")
        
        if not isinstance(data['student_user_ids'], list) or not data['student_user_ids']:
            raise ValueError("student_user_ids must be a non-empty list")
        
        result = StudentParentService.assign_students_to_parent(data, skid)
        return jsonify({
            'message': 'Students assigned to parent successfully',
            'data': result,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to assign students: {str(e)}', 'status': 'error', 'code': 500}), 500


# UPDATE STUDENT PARENT LINK
@studentParent_bp.route('/update/<skid>/<int:student_user_id>', methods=['PUT'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'], permission='manage_students')
def update_student_parent_link(skid, student_user_id):
    """
    Update parent link for a student
    """
    try:
        data = request.get_json()
        
        if not skid:
            raise ValueError("School ID (skid) is required")
        
        parent_user_id = data.get('parent_user_id')
        relation_type = data.get('relation_type', 'Guardian')
        
        result = StudentParentService.update_student_parent_link(
            student_user_id, 
            parent_user_id, 
            relation_type, 
            skid
        )
        
        return jsonify({
            'message': result['message'],
            'action': result['action'],
            'status': 'success',
            'code': 200
        }), 200
        
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to update parent link: {str(e)}', 'status': 'error', 'code': 500}), 500


# GET PARENT'S CHILDREN (for parent mobile app - returns full details)
@studentParent_bp.route('/children/<int:parent_user_id>/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'TEACHER', 'PARENT'], permission=('view_students', 'manage_students'), own_roles=('PARENT',))
@own_parent_required('parent_user_id')
def get_parent_children(parent_user_id, skid):
    try:
        if not skid:
            raise ValueError("School ID (skid) is required")

        result = StudentParentService.get_parent_children(parent_user_id, skid)

        return jsonify({
            'message': 'Parent children retrieved successfully',
            'data': result,
            'status': 'success',
            'code': 200
        }), 200
    except Exception as e:
        return jsonify({'message': f'Failed to get parent children: {str(e)}', 'status': 'error', 'code': 500}), 500


# GET PARENT'S STUDENTS
@studentParent_bp.route('/parent/<int:parent_user_id>/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'TEACHER'], permission=('view_students', 'manage_students'))
def get_parent_students(parent_user_id, skid):
    try:
        if not skid:
            raise ValueError("School ID (skid) is required")
        
        result = StudentParentService.get_parent_students(parent_user_id, skid)
        if not result:
            return jsonify({'message': 'Parent not found', 'status': 'error', 'code': 404}), 404
        
        return jsonify({
            'message': 'Parent students retrieved successfully',
            'data': result,
            'status': 'success',
            'code': 200
        }), 200
    except Exception as e:
        return jsonify({'message': f'Failed to get parent students: {str(e)}', 'status': 'error', 'code': 500}), 500

# GET STUDENT'S PARENTS
@studentParent_bp.route('/student/<int:student_user_id>/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'TEACHER'], permission=('view_students', 'manage_students'))
def get_student_parents(student_user_id, skid):
    try:
        if not skid:
            raise ValueError("School ID (skid) is required")
        
        result = StudentParentService.get_student_parents(student_user_id, skid)
        if not result:
            return jsonify({'message': 'Student not found', 'status': 'error', 'code': 404}), 404
        
        return jsonify({
            'message': 'Student parents retrieved successfully',
            'data': result,
            'status': 'success',
            'code': 200
        }), 200
    except Exception as e:
        return jsonify({'message': f'Failed to get student parents: {str(e)}', 'status': 'error', 'code': 500}), 500

# REMOVE STUDENT FROM PARENT
@studentParent_bp.route('/remove/<skid>', methods=['DELETE'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'], permission='manage_students')
def remove_student_from_parent(skid):
    try:
        data = request.get_json()
        
        if not skid:
            raise ValueError("School ID (skid) is required")
        
        if not data or 'parent_user_id' not in data or 'student_user_id' not in data:
            raise ValueError("parent_user_id and student_user_id are required")
        
        result = StudentParentService.remove_student_from_parent(
            data['student_user_id'], 
            data['parent_user_id'], 
            skid
        )
        
        if result:
            return jsonify({
                'message': 'Student removed from parent successfully',
                'status': 'success',
                'code': 200
            }), 200
        else:
            return jsonify({
                'message': 'Parent-student relationship not found',
                'status': 'error',
                'code': 404
            }), 404
    except Exception as e:
        return jsonify({'message': f'Failed to remove student from parent: {str(e)}', 'status': 'error', 'code': 500}), 500

# UPDATE RELATION TYPE
@studentParent_bp.route('/update-relation/<skid>', methods=['PUT'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'], permission='manage_students')
def update_relation_type(skid):
    try:
        data = request.get_json()
        
        if not skid:
            raise ValueError("School ID (skid) is required")
        
        if not data or 'parent_user_id' not in data or 'student_user_id' not in data or 'relation_type' not in data:
            raise ValueError("parent_user_id, student_user_id, and relation_type are required")
        
        result = StudentParentService.update_relation_type(
            data['student_user_id'],
            data['parent_user_id'],
            data['relation_type'],
            skid
        )
        
        if result:
            return jsonify({
                'message': 'Relation type updated successfully',
                'data': result,
                'status': 'success',
                'code': 200
            }), 200
        else:
            return jsonify({
                'message': 'Parent-student relationship not found',
                'status': 'error',
                'code': 404
            }), 404
    except Exception as e:
        return jsonify({'message': f'Failed to update relation type: {str(e)}', 'status': 'error', 'code': 500}), 500

# GET ALL PARENT-STUDENT RELATIONSHIPS FOR A SCHOOL
@studentParent_bp.route('/all/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'], permission=('view_students', 'manage_students'))
def get_all_parent_student_relationships(skid):
    try:
        if not skid:
            raise ValueError("School ID (skid) is required")
        
        result = StudentParentService.get_all_relationships(skid)
        return jsonify({
            'message': 'All parent-student relationships retrieved successfully',
            'data': result,
            'status': 'success',
            'code': 200
        }), 200
    except Exception as e:
        return jsonify({'message': f'Failed to get relationships: {str(e)}', 'status': 'error', 'code': 500}), 500