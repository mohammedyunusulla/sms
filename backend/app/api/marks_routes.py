# marks_routes.py

from flask import Blueprint, request, jsonify
from app.decorators import login_required
from app.services.marks_service import MarksService

marks_bp = Blueprint('marks', __name__)


# FETCH STUDENTS WITH EXISTING MARKS
@marks_bp.route('/fetch-students/<skid>/<academic_year_id>', methods=['POST'])
@login_required(['TEACHER', 'CLASS_TEACHER', 'SCHOOL_ADMIN'])
def fetch_students_for_marks_entry(skid, academic_year_id):
    """
    Fetch students list with existing marks
    Payload: {
        "exam_config_id": 1,
        "section_id": 2
    }
    """
    try:
        data = request.get_json()
        students = MarksService.get_students_with_marks(data, skid, academic_year_id)
        return jsonify({
            'data': students,
            'status': 'success',
            'code': 200
        }), 200
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500


# ENTER/UPDATE MARKS
@marks_bp.route('/entry/<skid>/<academic_year_id>', methods=['POST'])
@login_required(['TEACHER', 'CLASS_TEACHER', 'SCHOOL_ADMIN'])
def enter_marks(skid, academic_year_id):
    """
    Bulk marks entry/update
    Payload: {
        "exam_config_id": 1,
        "marks_data": [
            {
                "student_id": 1,
                "internal_marks": 35,
                "external_marks": 55,
                "total_marks": 90,
                "is_absent": false,
                "remarks": "Good"
            }
        ],
        "is_draft": false
    }
    """
    try:
        data = request.get_json()
        
        result = MarksService.bulk_enter_marks(
            data['exam_config_id'],
            data['marks_data'],
            data['teacher_id'],
            data.get('is_draft', False),
            skid,
            academic_year_id
        )
        
        return jsonify({
            'message': 'Marks saved successfully' if not data.get('is_draft') else 'Draft saved',
            'data': result,
            'status': 'success',
            'code': 200
        }), 200
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500
