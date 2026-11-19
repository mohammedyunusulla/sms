from flask import Blueprint, request, jsonify
from app.decorators import login_required
from app.decorators.auth import student_access_required
from app.services.progress_card_service import ProgressCardService

progress_card_bp = Blueprint('progress-card', __name__)


@progress_card_bp.route('/my-class/<skid>/<teacher_id>', methods=['GET'])
@login_required(['TEACHER'])
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
@login_required(['TEACHER', 'SCHOOL_ADMIN'])
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


# EXPORT CLASS REPORT
@progress_card_bp.route('/export/class/<skid>/<int:exam_id>', methods=['GET'])
@login_required(['TEACHER', 'SCHOOL_ADMIN'])
def export_class_report(skid, exam_id):
    """Export class progress as Excel"""
    try:
        class_id = request.args.get('class_id', type=int)
        section_id = request.args.get('section_id', type=int)
        
        excel_file = ProgressCardService.export_class_report(
            exam_id, class_id, section_id, skid
        )
        
        return send_file(
            excel_file,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'Class_Progress_{class_id}_{section_id}.xlsx'
        )
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500


# BULK GENERATE REPORT CARDS
@progress_card_bp.route('/bulk-generate/<skid>', methods=['POST'])
@login_required(['TEACHER', 'SCHOOL_ADMIN'])
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
        data = request.get_json()
        result = ProgressCardService.bulk_generate_report_cards(data, skid)
        return jsonify({
            'message': f'Generated {result["count"]} report cards',
            'data': result,
            'status': 'success',
            'code': 200
        }), 200
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500


# VIEW INDIVIDUAL PROGRESS CARD
@progress_card_bp.route('/view/<skid>/<int:student_id>/<int:exam_id>', methods=['GET'])
@login_required(['TEACHER', 'TEACHER', 'SCHOOL_ADMIN', 'STUDENT', 'PARENT'])
@student_access_required('student_id')
def view_progress_card(skid, student_id, exam_id):
    """View individual student's progress card"""
    try:
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
@login_required(['TEACHER', 'SCHOOL_ADMIN', 'STUDENT', 'PARENT'])
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

        return jsonify({
            'data': annual_report,
            'status': 'success',
            'code': 200
        }), 200
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500
