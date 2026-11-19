# app/routes/class_routes.py
from flask import Blueprint, request, jsonify
from app.services.class_service import ClassService
from app.decorators import login_required

class_bp = Blueprint('classes', __name__)

# CREATE CLASS
@class_bp.route('/create/class/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
def create_class(skid):
    try:
        data = request.get_json()
        new_class = ClassService.create_class(data, skid)
        print(new_class)
        return jsonify({
            'message': 'Class created successfully',
            'class': new_class,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve)}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to create class: {str(e)}'}), 500


@class_bp.route('/update/class/<skid>/<int:class_id>', methods=['PUT'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
def update_class(skid, class_id):
    """
    Update a class
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'message': 'No data provided', 'status': 'error', 'code': 400}), 400
        
        if not skid:
            raise ValueError("School ID (skid) is required")
        
        updated_class = ClassService.update_class(class_id, data, skid)
        
        return jsonify({
            'message': 'Class updated successfully',
            'data': updated_class,
            'status': 'success',
            'code': 200
        }), 200
        
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to update class: {str(e)}', 'status': 'error', 'code': 500}), 500


@class_bp.route('/class/delete/<skid>/<int:class_id>', methods=['DELETE'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
def delete_class(skid, class_id):
    """
    Delete a class and all its sections
    """
    try:
        if not skid:
            raise ValueError("School ID (skid) is required")
        ClassService.delete_class(class_id, skid)
        
        return jsonify({
            'message': 'Class deleted successfully',
            'status': 'success',
            'code': 200
        }), 200
        
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to delete class: {str(e)}', 'status': 'error', 'code': 500}), 500


@class_bp.route('/list/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'TEACHER'])
def get_classes(skid):
    """
    Get all classes for the current user's school
    """
    try:
        classes = ClassService.get_classes_by_school(skid)
        print("classses---", classes)
        
        return jsonify({
            'message': 'Classes retrieved successfully',
            'data': classes,
            'status': 'success',
            'code': 200
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to retrieve classes: {str(e)}', 'status': 'error', 'code': 500}), 500
        
@class_bp.route('/<int:class_id>/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'TEACHER'])
def get_class_by_id(class_id, skid):
    """
    Get a specific class by ID with student count
    """
    try:
        if not skid:
            raise ValueError("School ID (skid) is required")

        class_data = ClassService.get_class_by_id(class_id, skid)

        return jsonify({
            'message': 'Class details retrieved successfully',
            'data': class_data,
            'status': 'success',
            'code': 200
        }), 200

    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to retrieve class: {str(e)}', 'status': 'error', 'code': 500}), 500

#----------------------------------------------- SECTIONS APIS --------------------------------------------------------


@class_bp.route('/create/section/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
def create_section(skid):
    """
    Create a new section
    Only super admin and school admin can create sections
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'message': 'No data provided', 'status': 'error', 'code': 400}), 400
        
        if not skid:
            raise ValueError("School ID (skid) is required")
        
        new_section = ClassService.create_section(data, skid)
        
        return jsonify({
            'message': 'Section created successfully',
            'data': new_section,
            'status': 'success',
            'code': 200
        }), 200
        
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to create section: {str(e)}', 'status': 'error', 'code': 500}), 500


@class_bp.route('/update/section/<skid>/<int:section_id>', methods=['PUT'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
def update_section(skid, section_id):
    """
    Update a section
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'message': 'No data provided', 'status': 'error', 'code': 400}), 400
        if not skid:
            raise ValueError("School ID (skid) is required")
        
        updated_section = ClassService.update_section(section_id, data, skid)
        
        return jsonify({
            'message': 'Section updated successfully',
            'data': updated_section,
            'status': 'success',
            'code': 200
        }), 200
        
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to update section: {str(e)}', 'status': 'error', 'code': 500}), 500


@class_bp.route('/section/delete/<skid>/<int:section_id>', methods=['DELETE'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
def delete_section(skid, section_id):
    """
    Delete a section
    """
    try:
        if not skid:
            raise ValueError("School ID (skid) is required")
        
        ClassService.delete_section(section_id, skid)
        
        return jsonify({
            'message': 'Section deleted successfully',
            'status': 'success',
            'code': 200
        }), 200
        
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to delete section: {str(e)}', 'status': 'error', 'code': 500}), 500


@class_bp.route('/sections/<skid>/<int:class_id>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'TEACHER'])
def get_sections_by_class(skid, class_id):
    """
    Get all sections for a specific class
    """
    try:
        sections = ClassService.get_sections_by_class(class_id, skid)
        
        return jsonify({
            'message': 'Sections retrieved successfully',
            'data': sections,
            'status': 'success',
            'code': 200
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to retrieve sections: {str(e)}', 'status': 'error', 'code': 500}), 500


@class_bp.route('/add-to-section/<skid>/<int:section_id>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL'])
def add_students_to_section(skid, section_id):
    """
    Add one or multiple students to a specific section
    Accepts both single student_id or array of student_ids
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'message': 'Request body is required', 
                'status': 'error', 
                'code': 400
            }), 400
        
        # Handle both single student_id and array of student_ids
        student_ids = []
        if 'student_ids' in data:
            # Array of student IDs (new format)
            student_ids = data['student_ids']
            if not isinstance(student_ids, list) or len(student_ids) == 0:
                return jsonify({
                    'message': 'student_ids must be a non-empty array', 
                    'status': 'error', 
                    'code': 400
                }), 400
        elif 'student_id' in data:
            # Single student ID (backward compatibility)
            student_ids = [data['student_id']]
        else:
            return jsonify({
                'message': 'Either student_id or student_ids is required', 
                'status': 'error', 
                'code': 400
            }), 400
        
        # Add students to section
        result = ClassService.add_students_to_section(skid, section_id, student_ids)
        
        return jsonify({
            'message': f'{result["added_count"]} student(s) added successfully',
            'data': {
                'added_count': result['added_count'],
                'failed_count': result['failed_count'],
                'failed_students': result['failed_students']
            },
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
            'message': f'Failed to add students: {str(e)}', 
            'status': 'error', 
            'code': 500
        }), 500


@class_bp.route('/remove-from-section/<skid>/<int:section_id>/<int:student_id>', methods=['DELETE'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL'])
def remove_student_from_section(skid, section_id, student_id):
    """
    Remove a student from a specific class or its sections
    """
    try:
        success = ClassService.remove_student_from_section(skid, section_id, student_id)
        if not success:
            return jsonify({'message': 'Failed to remove student: Enrollment record not found', 'status': 'error', 'code': 404}), 404
            
        return jsonify({
            'message': 'Student removed from section successfully',
            'data': success,
            'status': 'success',
            'code': 200
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to remove student: {str(e)}', 'status': 'error', 'code': 500}), 500


@class_bp.route('/move-to-section/<skid>/<int:new_section_id>/<int:student_id>', methods=['PUT'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL'])
def move_student_to_section(skid, new_section_id, student_id):
    """
    Move a student from current section to a new section
    """
    try:
        result = ClassService.move_student_to_section(skid, new_section_id, student_id)
        
        if result:
            return jsonify({
                'message': 'Student moved to new section successfully',
                'status': 'success',
                'code': 200
            }), 200
        else:
            return jsonify({
                'message': 'Failed to move student',
                'status': 'error',
                'code': 400
            }), 400
            
    except ValueError as e:
        return jsonify({
            'message': str(e),
            'status': 'error',
            'code': 404
        }), 404
    except Exception as e:
        return jsonify({
            'message': f'Failed to move student: {str(e)}',
            'status': 'error',
            'code': 500
        }), 500


@class_bp.route('/remove-subject-from-section/<skid>/<int:section_id>/<int:subject_id>', methods=['DELETE'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL'])
def remove_subject_from_section(skid, section_id, subject_id):
    """
    Remove a subject from a specific class or its sections
    """
    try:
        success = ClassService.remove_subject_from_section(skid, section_id, subject_id)
        if not success:
            return jsonify({'message': 'Failed to remove subject: Enrollment record not found', 'status': 'error', 'code': 404}), 404
            
        return jsonify({
            'message': 'Subject removed from section successfully',
            'data': success,
            'status': 'success',
            'code': 200
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to remove subject: {str(e)}', 'status': 'error', 'code': 500}), 500
