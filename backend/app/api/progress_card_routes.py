from flask import Blueprint, request, jsonify
from app.decorators import login_required
from app.decorators.auth import student_access_required
from app.services.progress_card_service import ProgressCardService
from app.services.exam_results_service import RESULT_LIMITED_ROLES, published_exam_ids, current_year_id
from app.utils.db_manager import switch_to_school_db


def _results_limited():
    """Students and parents only see published results."""
    role = request.current_user.role
    return (role.value if hasattr(role, 'value') else str(role)) in RESULT_LIMITED_ROLES

progress_card_bp = Blueprint('progress-card', __name__)


@progress_card_bp.route('/my-class/<skid>/<teacher_id>', methods=['GET'])
@login_required(['TEACHER'], self_service=True)
def get_my_class(skid, teacher_id):
    """Get class assigned to logged-in class teacher"""
    try:
        class_info = ProgressCardService.get_teacher_class(teacher_id, skid)
        return jsonify({
            'data': class_info,
            'status': 'success',
            'code': 200
        }), 200
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500


# GET CLASS PROGRESS
@progress_card_bp.route('/class-progress/<skid>/<academic_year_id>/<int:exam_id>', methods=['GET'])
@login_required(['TEACHER', 'SCHOOL_ADMIN'], permission=('view_marks', 'manage_marks'))
def get_class_progress(skid, academic_year_id, exam_id):
    """
    Get complete class progress for an exam
    Query params: class_id, section_id
    """
    try:
        class_id = request.args.get('class_id', type=int)
        section_id = request.args.get('section_id', type=int)
        
        progress = ProgressCardService.get_class_progress(
            exam_id, class_id, section_id, skid, academic_year_id
        )
        
        return jsonify({
            'data': progress,
            'status': 'success',
            'code': 200
        }), 200
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500


# Class progress Excel export is built in the browser from the class-progress data (Class Progress page);
# the old /export/class route called a method that never existed and always returned 500.


# BULK GENERATE REPORT CARDS
@progress_card_bp.route('/bulk-generate/<skid>', methods=['POST'])
@login_required(['TEACHER', 'SCHOOL_ADMIN'], permission=('view_marks', 'manage_marks'))
def bulk_generate_report_cards(skid):
    """
    Bulk generate report cards for all students in a class
    Payload: {
        "exam_type_id": 1,
        "class_id": 5,
        "section_id": 2
    }
    """
    try:
        data = request.get_json() or {}
        result = ProgressCardService.bulk_generate_report_cards(data, skid)
        return jsonify({
            'message': f'Generated {result["count"]} report cards',
            'data': result,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500


# VIEW INDIVIDUAL PROGRESS CARD
@progress_card_bp.route('/view/<skid>/<int:student_id>/<int:exam_id>', methods=['GET'])
@login_required(['TEACHER', 'TEACHER', 'SCHOOL_ADMIN', 'STUDENT', 'PARENT'], permission=('view_marks', 'manage_marks'), own_roles=('STUDENT', 'PARENT'))
@student_access_required('student_id')
def view_progress_card(skid, student_id, exam_id):
    """View individual student's progress card"""
    try:
        if _results_limited():
            with switch_to_school_db(skid) as tenant_session:
                year_id = current_year_id(tenant_session)
                published = year_id is not None and exam_id in published_exam_ids(tenant_session, year_id)
            if not published:
                return jsonify({'message': "This exam's results haven't been published yet", 'status': 'error', 'code': 403}), 403
        progress_card = ProgressCardService.calculate_progress_card(
            student_id, exam_id, skid
        )
        return jsonify({
            'data': progress_card,
            'status': 'success',
            'code': 200
        }), 200
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500


# VIEW ANNUAL PROGRESS REPORT
@progress_card_bp.route('/annual/<skid>/<int:student_id>', methods=['GET'])
@login_required(['TEACHER', 'SCHOOL_ADMIN', 'STUDENT', 'PARENT'], permission=('view_marks', 'manage_marks'), own_roles=('STUDENT', 'PARENT'))
@student_access_required('student_id')
def view_annual_report(skid, student_id):
    """View student's annual progress report (all exams)"""
    try:
        academic_year_id = request.args.get('academic_year_id')

        if not academic_year_id:
            return jsonify({
                'message': 'academic_year_id is required',
                'status': 'error',
                'code': 400
            }), 400

        annual_report = ProgressCardService.get_student_annual_report(
            student_id, academic_year_id, skid
        )
        if _results_limited():
            # only exams the school has published for this year
            with switch_to_school_db(skid) as tenant_session:
                published = published_exam_ids(tenant_session, academic_year_id)
            annual_report['exam_results'] = [
                r for r in annual_report.get('exam_results', []) if int(r.get('exam_id')) in published
            ]

        return jsonify({
            'data': annual_report,
            'status': 'success',
            'code': 200
        }), 200
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500
