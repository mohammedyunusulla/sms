# exam_routes.py

from flask import Blueprint, request, jsonify
from app.decorators import login_required
from app.services.exam_service import ExamService

exam_bp = Blueprint('exams', __name__)

# CREATE EXAM TYPE
@exam_bp.route('/create/exam-type/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
def create_exam_type(skid):
    """
    Create a new exam type
    Payload: {
        "exam_name": "First Term Exam",
        "exam_code": "FTE",
        "exam_category": "Formative",
        "sequence_order": 1
    }
    """
    try:
        data = request.get_json()
        
        # Validation
        if not data.get('exam_name'):
            raise ValueError("Exam name is required")
        if not data.get('exam_code'):
            raise ValueError("Exam code is required")
            
        new_exam_type = ExamService.create_exam_type(data, skid)
        return jsonify({
            'message': 'Exam type created successfully',
            'data': new_exam_type,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to create exam type: {str(e)}', 'status': 'error', 'code': 500}), 500


# FETCH ALL EXAM TYPES
@exam_bp.route('/fetch/exam-types/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER', 'STUDENT', 'PARENT'])
def fetch_exam_types(skid):
    """Fetch all exam types for the school"""
    try:
        exam_types = ExamService.get_all_exam_types(skid)
        return jsonify({
            'data': exam_types,
            'status': 'success',
            'code': 200
        }), 200
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500


# FETCH SINGLE EXAM TYPE BY ID
@exam_bp.route('/<int:exam_id>/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'TEACHER'])
def fetch_exam_type_by_id(exam_id, skid):
    """Fetch a single exam type by ID"""
    try:
        exam_type = ExamService.get_exam_type_by_id(exam_id, skid)
        if not exam_type:
            return jsonify({
                'message': 'Exam type not found',
                'status': 'error',
                'code': 404
            }), 404
        return jsonify({
            'data': exam_type,
            'status': 'success',
            'code': 200
        }), 200
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500


# UPDATE EXAM TYPE
@exam_bp.route('/update/exam-type/<skid>/<int:exam_id>', methods=['PUT'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
def update_exam_type(skid, exam_id):
    """Update an existing exam type"""
    try:
        data = request.get_json()
        updated_exam = ExamService.update_exam_type(exam_id, data, skid)
        return jsonify({
            'message': 'Exam type updated successfully',
            'data': updated_exam,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500


# DELETE EXAM TYPE
@exam_bp.route('/delete/<int:exam_id>/<skid>', methods=['DELETE'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
def delete_exam_type(exam_id, skid):
    """Delete an exam type"""
    try:
        ExamService.delete_exam_type(exam_id, skid)
        return jsonify({
            'message': 'Exam type deleted successfully',
            'status': 'success',
            'code': 200
        }), 200
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500


# --------------------------------------------( EXAM - SUBJECT CONFIG APIS )---------------------------------------------

# CREATE EXAM SUBJECT CONFIGURATION
@exam_bp.route('/create/exam-config/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
def create_exam_config(skid):
    """
    Create exam subject configuration
    Payload: {
        "exam_type_id": 1,
        "class_id": 5,
        "section_id": 2,  // Optional
        "subject_id": 10,
        "has_internal_external": true,
        "internal_max_marks": 40,
        "external_max_marks": 60,
        "total_max_marks": 100,
        "min_passing_marks": 35,
        "weightage_percentage": 100.0
    }
    """
    try:
        data = request.get_json()
        
        # Validation
        required_fields = ['exam_type_id', 'class_id', 'subject_id', 'total_max_marks', 'min_passing_marks']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"{field} is required")
        
        new_config = ExamService.create_exam_config(data, skid)
        return jsonify({
            'message': 'Configuration created successfully',
            'data': new_config,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to create configuration: {str(e)}', 'status': 'error', 'code': 500}), 500


# FETCH EXAM CONFIGURATIONS
@exam_bp.route('/fetch/exam-configs/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'TEACHER'])
def fetch_exam_configs(skid):
    """
    Fetch exam configurations with filters
    Query params: exam_type_id, class_id, section_id (optional), subject_id (optional)
    """
    try:
        filters = {
            'exam_type_id': request.args.get('exam_type_id', type=int),
            'class_id': request.args.get('class_id', type=int),
            'section_id': request.args.get('section_id', type=int),
            'subject_id': request.args.get('subject_id', type=int)
        }

        configs = ExamService.get_exam_configs(filters, skid)
        return jsonify({
            'data': configs,
            'status': 'success',
            'code': 200
        }), 200
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500


# FETCH SINGLE EXAM CONFIGURATION BY ID
@exam_bp.route('/exam-config/<int:config_id>/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'TEACHER'])
def fetch_exam_config_by_id(config_id, skid):
    """Fetch a single exam configuration by ID"""
    try:
        config = ExamService.get_exam_config_by_id(config_id, skid)
        if not config:
            return jsonify({
                'message': 'Configuration not found',
                'status': 'error',
                'code': 404
            }), 404
        return jsonify({
            'data': config,
            'status': 'success',
            'code': 200
        }), 200
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500


# UPDATE EXAM CONFIGURATION
@exam_bp.route('/update/exam-config/<skid>/<int:config_id>', methods=['PUT'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
def update_exam_config(skid, config_id):
    """Update an existing exam configuration"""
    try:
        data = request.get_json()
        updated_config = ExamService.update_exam_config(config_id, data, skid)
        return jsonify({
            'message': 'Configuration updated successfully',
            'data': updated_config,
            'status': 'success',
            'code': 200
        }), 200
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500


# DELETE EXAM CONFIGURATION
@exam_bp.route('/delete/exam-config/<skid>/<int:config_id>', methods=['DELETE'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
def delete_exam_config(skid, config_id):
    """Delete an exam configuration"""
    try:
        ExamService.delete_exam_config(config_id, skid)
        return jsonify({
            'message': 'Configuration deleted successfully',
            'status': 'success',
            'code': 200
        }), 200
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500


# BULK COPY CONFIGURATIONS
@exam_bp.route('/bulk-copy/exam-configs/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
def bulk_copy_configs(skid):
    """
    Bulk copy configurations from one exam/class to another
    Payload: {
        "from_exam_type_id": 1,
        "from_class_id": 5,
        "to_exam_type_id": 2,
        "to_class_id": 5,
        "to_section_id": 2  // Optional
    }
    """
    try:
        data = request.get_json()
        result = ExamService.bulk_copy_configurations(data, skid)
        return jsonify({
            'message': f'Copied {result["copied_count"]} configurations successfully',
            'data': result,
            'status': 'success',
            'code': 200
        }), 200
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500


# --------------------------------------------( EXAM TIMETABLE APIS )---------------------------------------------


# CREATE EXAM TIMETABLE ENTRY
@exam_bp.route('/create/exam-timetable/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
def create_exam_timetable(skid):
    """
    Create an exam timetable entry
    Payload: {
        "exam_type_id": 1,
        "class_id": 5,
        "section_id": 2,         // Optional
        "subject_id": 10,
        "exam_date": "2026-04-15",
        "start_time": "09:00",
        "end_time": "12:00",
        "duration_minutes": 180,  // Optional - auto-calculated
        "notes": "Bring calculator" // Optional
    }
    """
    try:
        data = request.get_json()

        required_fields = ['academic_year_id', 'exam_type_id', 'class_id', 'subject_id', 'exam_date', 'start_time', 'end_time']
        for field in required_fields:
            if field not in data or not data[field]:
                raise ValueError(f"{field} is required")

        entry = ExamService.create_exam_timetable(data, skid)
        return jsonify({
            'message': 'Exam timetable entry created successfully',
            'data': entry,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to create exam timetable: {str(e)}', 'status': 'error', 'code': 500}), 500


# FETCH EXAM TIMETABLE ENTRIES
@exam_bp.route('/fetch/exam-timetables/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'TEACHER'])
def fetch_exam_timetables(skid):
    """
    Fetch exam timetable entries with filters
    Query params: exam_type_id, class_id, section_id (all optional)
    """
    try:
        filters = {
            'academic_year_id': request.args.get('academic_year_id', type=int),
            'exam_type_id': request.args.get('exam_type_id', type=int),
            'class_id': request.args.get('class_id', type=int),
            'section_id': request.args.get('section_id', type=int)
        }

        entries = ExamService.get_exam_timetables(filters, skid)
        return jsonify({
            'data': entries,
            'status': 'success',
            'code': 200
        }), 200
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500


# FETCH SINGLE EXAM TIMETABLE ENTRY
@exam_bp.route('/exam-timetable/<int:entry_id>/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'TEACHER'])
def fetch_exam_timetable_by_id(entry_id, skid):
    """Fetch a single exam timetable entry by ID"""
    try:
        entry = ExamService.get_exam_timetable_by_id(entry_id, skid)
        if not entry:
            return jsonify({
                'message': 'Exam timetable entry not found',
                'status': 'error',
                'code': 404
            }), 404
        return jsonify({
            'data': entry,
            'status': 'success',
            'code': 200
        }), 200
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500


# UPDATE EXAM TIMETABLE ENTRY
@exam_bp.route('/update/exam-timetable/<skid>/<int:entry_id>', methods=['PUT'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
def update_exam_timetable(skid, entry_id):
    """Update an exam timetable entry"""
    try:
        data = request.get_json()
        updated = ExamService.update_exam_timetable(entry_id, data, skid)
        return jsonify({
            'message': 'Exam timetable entry updated successfully',
            'data': updated,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500


# DELETE EXAM TIMETABLE ENTRY
@exam_bp.route('/delete/exam-timetable/<skid>/<int:entry_id>', methods=['DELETE'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
def delete_exam_timetable(skid, entry_id):
    """Delete an exam timetable entry"""
    try:
        ExamService.delete_exam_timetable(entry_id, skid)
        return jsonify({
            'message': 'Exam timetable entry deleted successfully',
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500



# BULK DELETE EXAM TIMETABLE ENTRIES
@exam_bp.route('/bulk-delete/exam-timetables/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
def bulk_delete_exam_timetables(skid):
    """Bulk delete exam timetable entries"""
    try:
        data = request.get_json()
        ids = data.get('ids', [])
        if not ids:
            raise ValueError("No entry IDs provided")

        result = ExamService.bulk_delete_exam_timetables(ids, skid)
        return jsonify({
            'message': f'Deleted {result["deleted_count"]} entries successfully',
            'data': result,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500


# INVIGILATOR SCHEDULE (exam slots where teacher is assigned as invigilator)
@exam_bp.route('/invigilator-schedule/<skid>/<int:teacher_id>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER'])
def get_invigilator_schedule(skid, teacher_id):
    """
    Get all exam seating configs where the given teacher is the invigilator.
    Query params: exam_type_id (required), academic_year_id (optional)
    """
    try:
        exam_type_id = request.args.get('exam_type_id', type=int)
        if not exam_type_id:
            raise ValueError("exam_type_id is required")

        academic_year_id = request.args.get('academic_year_id', type=int)
        entries = ExamService.get_invigilator_schedule(skid, teacher_id, exam_type_id, academic_year_id)
        return jsonify({
            'data': entries,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to get invigilator schedule: {str(e)}', 'status': 'error', 'code': 500}), 500


# STUDENT EXAM TIMETABLE (exam schedule + room/seat/invigilator from seating arrangement)
@exam_bp.route('/student-exam-timetable/<skid>/<int:student_id>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER', 'STUDENT', 'PARENT'])
def get_student_exam_timetable(skid, student_id):
    """
    Get a student's exam timetable with room, seat, and invigilator details
    from the seating arrangement.
    Query params: exam_type_id (required), academic_year_id (optional)
    """
    try:
        exam_type_id = request.args.get('exam_type_id', type=int)
        if not exam_type_id:
            raise ValueError("exam_type_id is required")

        academic_year_id = request.args.get('academic_year_id', type=int)
        entries = ExamService.get_student_exam_timetable(skid, student_id, exam_type_id, academic_year_id)
        return jsonify({
            'data': entries,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to get student exam timetable: {str(e)}', 'status': 'error', 'code': 500}), 500

