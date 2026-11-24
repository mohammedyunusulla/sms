from flask import Blueprint, request, jsonify
from app.services.teacher_dashboard_service import TeacherDashboardService
from app.decorators import log_actions, login_required
from datetime import datetime

teacher_dashboard_bp = Blueprint('teacherDashboard', __name__)



@teacher_dashboard_bp.route('/students/teacher/count/<skid>/<teacher_id>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN', 'TEACHER'], self_service=True)
def get_teacher_student_count(skid, teacher_id):
    """
    Get total count of students assigned to a teacher

    Query params:
    - skid: Institution ID (required)
    - teacher_id: Teacher user ID (required)

    Returns total count of unique students across all sections taught by the teacher
    """
    try:
        if not skid or not teacher_id:
            return jsonify({
                'message': 'skid and teacher_id are required',
                'status': 'error',
                'code': 400
            }), 400

        student_count = TeacherDashboardService.get_assigned_students_count(
            skid=skid,
            teacher_id=teacher_id
        )

        return jsonify({
            'message': 'Student count fetched successfully',
            'data': {'count': student_count},
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
            'message': f'Failed to fetch student count: {str(e)}',
            'status': 'error',
            'code': 500
        }), 500


@teacher_dashboard_bp.route('/attendance/absentees/count/<skid>/<academic_year_id>/<date>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN', 'TEACHER'], self_service=True)
def get_today_absentees_count(skid, academic_year_id, date):
    """
    Get today's student absentees count and preview

    Query params:
    - skid: Institution ID (required)
    - academic_year_id: Academic year ID (required)
    - date: Date in YYYY-MM-DD format (required)

    Returns:
    - count: Total number of absentees
    - preview: List of max 3 absentee students
    """
    try:
        if not skid or not academic_year_id or not date:
            return jsonify({
                'message': 'skid, academic_year_id, and date are required',
                'status': 'error',
                'code': 400
            }), 400

        # Validate date format
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            return jsonify({
                'message': 'Invalid date format. Use YYYY-MM-DD',
                'status': 'error',
                'code': 400
            }), 400

        # Teachers: only their own sections (teacher id from the login, never the URL); admins: whole institution
        from app.utils.teaching_scope import current_teacher_id
        absentees_data = TeacherDashboardService.get_today_absentees(
            skid=skid,
            academic_year_id=academic_year_id,
            date=date,
            teacher_id=current_teacher_id()
        )

        return jsonify({
            'message': 'Absentees data fetched successfully',
            'data': absentees_data,
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
            'message': f'Failed to fetch absentees data: {str(e)}',
            'status': 'error',
            'code': 500
        }), 500


# Full Week Timetable
@teacher_dashboard_bp.route('/timetable/teacher/week/<skid>/<teacher_id>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN', 'TEACHER'], self_service=True)
def get_teacher_week_timetable(skid, teacher_id):
    """
    Get teacher's full week timetable (Monday-Saturday)

    Query params:
    - skid: Institution ID (required)
    - teacher_id: Teacher user ID (required)
    - start_date: Week start date in YYYY-MM-DD format (optional, defaults to current week's Monday)

    Returns:
    - Timetable organized by day with all periods for the week
    """
    try:
        if not skid or not teacher_id:
            return jsonify({
                'message': 'skid and teacher_id are required',
                'status': 'error',
                'code': 400
            }), 400

        start_date = request.args.get('start_date')

        # Validate date format if provided
        if start_date:
            try:
                datetime.strptime(start_date, '%Y-%m-%d')
            except ValueError:
                return jsonify({
                    'message': 'Invalid start_date format. Use YYYY-MM-DD',
                    'status': 'error',
                    'code': 400
                }), 400

        week_timetable = TeacherDashboardService.get_teacher_week_timetable(
            skid=skid,
            teacher_id=teacher_id,
            start_date=start_date
        )

        return jsonify({
            'message': 'Week timetable fetched successfully',
            'data': week_timetable,
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
            'message': f'Failed to fetch week timetable: {str(e)}',
            'status': 'error',
            'code': 500
        }), 500


# Specific Day Timetable
@teacher_dashboard_bp.route('/timetable/teacher/<skid>/<teacher_id>/<date>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN', 'TEACHER'], self_service=True)
def get_teacher_timetable(skid, teacher_id, date):
    """
    Get teacher timetable for a specific day

    Query params:
    - skid: Institution ID (required)
    - teacher_id: Teacher user ID (required)
    - date: Date in YYYY-MM-DD format (required)

    Returns periods for the specified day with status (current, upcoming, completed)
    """
    try:
        if not skid or not teacher_id or not date:
            return jsonify({
                'message': 'skid, teacher_id, and date are required',
                'status': 'error',
                'code': 400
            }), 400

        # Validate date format
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            return jsonify({
                'message': 'Invalid date format. Use YYYY-MM-DD',
                'status': 'error',
                'code': 400
            }), 400

        timetable_data = TeacherDashboardService.get_teacher_timetable_by_day(
            skid=skid,
            teacher_id=teacher_id,
            date=date
        )

        return jsonify({
            'message': 'Timetable fetched successfully',
            'data': timetable_data,
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
            'message': f'Failed to fetch timetable: {str(e)}',
            'status': 'error',
            'code': 500
        }), 500
