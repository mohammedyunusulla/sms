# marks_routes.py

from flask import Blueprint, request, jsonify
from app.decorators import login_required
from app.services.marks_service import MarksService
from app.utils.db_manager import switch_to_school_db
from app.utils.teaching_scope import current_teacher_id, forbidden, teaches, student_section_id
from app.models.tenant.ExamModels import ExamSubjectConfig

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

        own_id = current_teacher_id()
        if own_id is not None:
            data['teacher_id'] = own_id  # never trust a teacher_id sent by a teacher
            with switch_to_school_db(skid) as session:
                config = session.query(ExamSubjectConfig).filter_by(id=data.get('exam_config_id')).first()
                if not config:
                    return jsonify({'message': 'Exam configuration not found', 'status': 'error', 'code': 404}), 404
                sections = {student_section_id(session, m.get('student_id')) for m in data.get('marks_data', [])}
                if config.section_id:
                    sections.add(config.section_id)
                if any(sec is None or not teaches(session, own_id, sec, config.subject_id) for sec in sections):
                    return forbidden('You can only enter marks for subjects you teach in that section')

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
    except ValueError as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500
