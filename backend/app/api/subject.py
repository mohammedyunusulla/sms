# app/routes/subject_routes.py (Fixed filename and blueprint name)
from flask import Blueprint, request, jsonify
from app.services.subject_service import SubjectService
from app.decorators import login_required

subject_bp = Blueprint('subjects', __name__)

# CREATE SUBJECT
@subject_bp.route('/get/<skid>/<int:subject_id>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL'], permission=('view_classes', 'view_exams', 'manage_classes'))
def get_subject(skid, subject_id):
    """Get a single subject (used by the subject edit page)."""
    try:
        subject = SubjectService.get_subject_by_id(subject_id, skid)
        return jsonify({'message': 'Subject retrieved successfully', 'data': subject, 'status': 'success', 'code': 200}), 200
    except Exception as e:
        if 'not found' in str(e).lower():
            return jsonify({'message': 'Subject not found', 'status': 'error', 'code': 404}), 404
        return jsonify({'message': f'Failed to get subject: {str(e)}', 'status': 'error', 'code': 500}), 500


@subject_bp.route('/create/subject/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'], permission='manage_classes')
def create_subject(skid):
    try:
        data = request.get_json()
        
        if not skid:
            raise ValueError("School ID (skid) is required")
            
        # Validate required fields
        if not data.get('subject_name'):
            raise ValueError("Subject name is required")
            
        # Validate class_id if provided
        if not data.get('class_id'):
            raise ValueError("Class ID is required")
        
        new_subject = SubjectService.create_subject(data, skid)
        return jsonify({
            'message': 'Subject created successfully',
            'data': new_subject,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to create subject: {str(e)}', 'status': 'error', 'code': 500}), 500

# UPDATE SUBJECT
@subject_bp.route('/update/subject/<skid>/<int:subject_id>', methods=['PUT'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'], permission='manage_classes')
def update_subject(skid, subject_id):
    try:
        data = request.get_json()
        
        if not skid:
            raise ValueError("School ID (skid) is required")
            
        # Validate required fields
        if not data.get('subject_name'):
            raise ValueError("Subject name is required")
        
        updated_subject = SubjectService.update_subject(subject_id, data, skid)
        return jsonify({
            'message': 'Subject updated successfully',
            'data': updated_subject,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to update subject: {str(e)}', 'status': 'error', 'code': 500}), 500


# DELETE SUBJECT
@subject_bp.route('/delete/subject/<skid>/<int:subject_id>', methods=['DELETE'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'], permission='manage_classes')
def delete_subject(skid, subject_id):
    try:
        if not skid:
            raise ValueError("School ID (skid) is required")
            
        SubjectService.delete_subject(subject_id, skid)
        return jsonify({
            'message': 'Subject deleted successfully',
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to delete subject: {str(e)}', 'status': 'error', 'code': 500}), 500


# LIST SUBJECTS FOR A CLASS
@subject_bp.route('/list/<skid>/<int:class_id>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'], permission=('view_classes', 'view_exams', 'manage_classes'))
def get_subjects_by_class(skid, class_id):
    try:
        if not skid:
            raise ValueError("School ID (skid) is required")
            
        subjects = SubjectService.get_subjects_by_class(class_id, skid)
        return jsonify({
            'message': 'Subjects retrieved successfully',
            'data': subjects,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to retrieve subjects: {str(e)}', 'status': 'error', 'code': 500}), 500
        
# LIST SUBJECTS FOR A CLASS
@subject_bp.route('/list/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'], permission=('view_classes', 'view_exams', 'manage_classes'))
def get_subjects_list(skid):
    try:
        if not skid:
            raise ValueError("School ID (skid) is required")
            
        subjects_list = SubjectService.get_subjects_list(skid)
        return jsonify({
            'message': 'Subjects retrieved successfully',
            'data': subjects_list,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to retrieve subjects: {str(e)}', 'status': 'error', 'code': 500}), 500


# ADD SUBJECTS TO SECTION
@subject_bp.route('/add-to-section/<skid>/<int:section_id>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'], permission='manage_classes')
def add_subjects_to_section(skid, section_id):
    """Assign subjects to a section"""
    try:
        data = request.get_json()
        
        if not data or 'subject_ids' not in data:
            return jsonify({
                'message': 'subject_ids is required in request body',
                'status': 'error',
                'code': 400
            }), 400
        
        subject_ids = data['subject_ids']
        
        if not isinstance(subject_ids, list) or len(subject_ids) == 0:
            return jsonify({
                'message': 'subject_ids must be a non-empty array',
                'status': 'error',
                'code': 400
            }), 400
        
        result = SubjectService.add_subjects_to_section(skid, section_id, subject_ids)
        
        return jsonify({
            'message': f'{result["added_count"]} subject(s) added successfully',
            'data': result,
            'status': 'success',
            'code': 200
        }), 200
        
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to add subjects: {str(e)}', 'status': 'error', 'code': 500}), 500


# REMOVE SUBJECT FROM SECTION
@subject_bp.route('/remove-from-section/<skid>/<int:section_id>/<int:subject_id>', methods=['PUT', 'DELETE'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'], permission='manage_classes')
def remove_subject_from_section(skid, section_id, subject_id):
    """Remove a subject from a section"""
    try:
        result = SubjectService.remove_subject_from_section(skid, section_id, subject_id)
        
        return jsonify({
            'message': 'Subject removed from section successfully',
            'status': 'success',
            'code': 200
        }), 200
        
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 404}), 404
    except Exception as e:
        return jsonify({'message': f'Failed to remove subject: {str(e)}', 'status': 'error', 'code': 500}), 500


# GET SUBJECTS FOR A SECTION
@subject_bp.route('/section/<skid>/<int:section_id>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'TEACHER', 'CLERK'], permission=('view_classes', 'view_exams', 'manage_classes'))
def get_subjects_by_section(skid, section_id):
    """Get all subjects assigned to a specific section"""
    try:
        if not skid:
            raise ValueError("School ID (skid) is required")
        
        subjects = SubjectService.get_subjects_by_section(section_id, skid)
        return jsonify({
            'message': 'Section subjects retrieved successfully',
            'data': subjects,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to retrieve subjects: {str(e)}', 'status': 'error', 'code': 500}), 500


# GET AVAILABLE SUBJECTS FOR A SECTION
@subject_bp.route('/available/<skid>/<int:section_id>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'TEACHER'], permission=('view_classes', 'view_exams', 'manage_classes'))
def get_available_subjects(skid, section_id):
    """Get subjects that can be assigned to this section"""
    try:
        if not skid:
            raise ValueError("School ID (skid) is required")
        
        subjects = SubjectService.get_available_subjects_for_section(section_id, skid)
        return jsonify({
            'message': 'Available subjects retrieved successfully',
            'data': subjects,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to retrieve subjects: {str(e)}', 'status': 'error', 'code': 500}), 500