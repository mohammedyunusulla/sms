from flask import Blueprint, request, jsonify
from app.services.assignment_service import AssignmentService
from app.decorators import log_actions, login_required

assignment_bp = Blueprint('assignment', __name__)


@assignment_bp.route('/teacher-classes/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER'])
def get_teacher_class_subjects(skid):
    """Get the class/section/subject combos assigned to the logged-in teacher."""
    try:
        teacher_id = request.args.get('teacher_id')
        if not teacher_id:
            return jsonify({'message': 'teacher_id is required', 'status': 'error', 'code': 400}), 400

        data = AssignmentService.get_teacher_class_subjects(skid, int(teacher_id))
        return jsonify({
            'message': 'Teacher class-subjects fetched successfully',
            'data': data,
            'status': 'success',
            'code': 200
        }), 200

    except Exception as e:
        return jsonify({'message': f'Failed to fetch teacher class-subjects: {str(e)}', 'status': 'error', 'code': 500}), 500


@assignment_bp.route('/create/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER'])
@log_actions('CREATE-ASSIGNMENT')
def create_assignment(skid):
    """Create a new assignment."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No data provided', 'status': 'error', 'code': 400}), 400

        required_fields = ['teacher_id', 'class_id', 'section_id', 'subject_id', 'academic_year_id', 'assignment_date']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'message': f'{field} is required', 'status': 'error', 'code': 400}), 400

        # At least one of assignment_text or assignment_drawing is required
        if not data.get('assignment_text') and not data.get('assignment_drawing'):
            return jsonify({'message': 'Either assignment_text or assignment_drawing is required', 'status': 'error', 'code': 400}), 400

        result = AssignmentService.create_assignment(data, skid)
        return jsonify({
            'message': 'Assignment created successfully',
            'data': result,
            'status': 'success',
            'code': 200
        }), 200

    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to create assignment: {str(e)}', 'status': 'error', 'code': 500}), 500


@assignment_bp.route('/update/<int:assignment_id>/<skid>', methods=['PUT'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER'])
@log_actions('UPDATE-ASSIGNMENT')
def update_assignment(assignment_id, skid):
    """Update an existing assignment."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No data provided', 'status': 'error', 'code': 400}), 400

        result = AssignmentService.update_assignment(skid, assignment_id, data)
        return jsonify({
            'message': 'Assignment updated successfully',
            'data': result,
            'status': 'success',
            'code': 200
        }), 200

    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to update assignment: {str(e)}', 'status': 'error', 'code': 500}), 500


@assignment_bp.route('/list/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER'])
def list_assignments(skid):
    """List assignments by date for a teacher."""
    try:
        teacher_id = request.args.get('teacher_id')
        date = request.args.get('date')
        academic_year_id = request.args.get('academic_year_id')

        if not teacher_id or not date or not academic_year_id:
            return jsonify({
                'message': 'teacher_id, date, and academic_year_id are required',
                'status': 'error',
                'code': 400
            }), 400

        data = AssignmentService.get_assignments_by_date(skid, int(teacher_id), date, int(academic_year_id))
        return jsonify({
            'message': 'Assignments fetched successfully',
            'data': data,
            'count': len(data),
            'status': 'success',
            'code': 200
        }), 200

    except Exception as e:
        return jsonify({'message': f'Failed to fetch assignments: {str(e)}', 'status': 'error', 'code': 500}), 500


@assignment_bp.route('/<int:assignment_id>/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER'])
def get_assignment(assignment_id, skid):
    """Get assignment details with student list and submission status."""
    try:
        data = AssignmentService.get_assignment_with_students(skid, assignment_id)
        return jsonify({
            'message': 'Assignment details fetched successfully',
            'data': data,
            'status': 'success',
            'code': 200
        }), 200

    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 404}), 404
    except Exception as e:
        return jsonify({'message': f'Failed to fetch assignment: {str(e)}', 'status': 'error', 'code': 500}), 500


@assignment_bp.route('/<int:assignment_id>/submissions/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER'])
@log_actions('UPDATE-ASSIGNMENT-SUBMISSIONS')
def update_submissions(assignment_id, skid):
    """Bulk update student submission status and remarks for an assignment."""
    try:
        data = request.get_json()
        if not data or not data.get('submissions'):
            return jsonify({'message': 'submissions array is required', 'status': 'error', 'code': 400}), 400

        reviewer_id = data.get('reviewer_id')
        if not reviewer_id:
            return jsonify({'message': 'reviewer_id is required', 'status': 'error', 'code': 400}), 400

        result = AssignmentService.update_submissions(skid, assignment_id, data['submissions'], reviewer_id)
        return jsonify({
            'message': result['message'],
            'status': 'success',
            'code': 200
        }), 200

    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to update submissions: {str(e)}', 'status': 'error', 'code': 500}), 500


@assignment_bp.route('/student/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER', 'STUDENT', 'PARENT'])
def get_student_assignments(skid):
    """Get assignments for a student based on their class/section."""
    try:
        student_id = request.args.get('student_id')
        academic_year_id = request.args.get('academic_year_id')
        date = request.args.get('date')  # optional

        if not student_id or not academic_year_id:
            return jsonify({
                'message': 'student_id and academic_year_id are required',
                'status': 'error',
                'code': 400
            }), 400

        data = AssignmentService.get_student_assignments(skid, int(student_id), int(academic_year_id), date)
        return jsonify({
            'message': 'Student assignments fetched successfully',
            'data': data,
            'count': len(data),
            'status': 'success',
            'code': 200
        }), 200

    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to fetch student assignments: {str(e)}', 'status': 'error', 'code': 500}), 500


@assignment_bp.route('/<int:assignment_id>/<skid>', methods=['DELETE'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER'])
@log_actions('DELETE-ASSIGNMENT')
def delete_assignment(assignment_id, skid):
    """Soft delete an assignment."""
    try:
        result = AssignmentService.delete_assignment(skid, assignment_id)
        return jsonify({
            'message': result['message'],
            'status': 'success',
            'code': 200
        }), 200

    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 404}), 404
    except Exception as e:
        return jsonify({'message': f'Failed to delete assignment: {str(e)}', 'status': 'error', 'code': 500}), 500
