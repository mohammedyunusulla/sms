from app.utils.validators import to_date
from flask import Blueprint, request, jsonify
from app.services.attendance_service import AttendanceService
from app.decorators import log_actions, login_required
from app.decorators.auth import student_access_required
from app.utils.db_manager import switch_to_school_db
from app.utils.teaching_scope import current_teacher_id, forbidden, is_class_teacher, student_section_id


def _class_teacher_guard(skid, records, default_section_id=None):
    """Teachers may only mark attendance for their own class-teacher section(s), and only its students."""
    teacher_id = current_teacher_id()
    if teacher_id is None:
        return None
    with switch_to_school_db(skid) as session:
        for r in records or []:
            # record/bulk sends section_id per record; update/bulk sends it once at the top level
            section_id = r.get('section_id', default_section_id)
            if section_id is None or not is_class_teacher(session, teacher_id, section_id):
                return forbidden('Only the class teacher can mark attendance for this section')
            if str(student_section_id(session, r.get('student_id'))) != str(section_id):
                return forbidden('A student in this attendance list is not in the selected section')
    return None
from app.models.main.User import UserRole
from datetime import datetime

attendance_bp = Blueprint('attendance', __name__)

@attendance_bp.route('/record/bulk/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'TEACHER'], permission='manage_attendance')
@log_actions('RECORD-ATTENDANCE')
def record_attendance_bulk(skid):
    """
    Record the attendance for the selected class and section - students
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'message': 'No data provided'}), 400
        if not skid:
            raise ValueError("School ID (skid) is required")
            
        denied = _class_teacher_guard(skid, data.get('records'), data.get('section_id'))
        if denied:
            return denied
        attendance = AttendanceService.record_attendance_bulk(data, skid, getattr(request.current_user, 'school_user_id', None))
        
        return jsonify({
            'message': 'Attendance recorded successfully',
            'data': attendance,
            'status': 'success',
            'code': 200
        }), 200
        
    except ValueError as e:
        return jsonify({'message': str(e)}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to record attendance: {str(e)}'}), 500


@attendance_bp.route('/update/bulk/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'TEACHER'], permission='manage_attendance')
@log_actions('UPDATE-ATTENDANCE-BULK')
def update_attendance_bulk(skid):
    """
    Update attendance records in bulk for a specific date
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('records'):
            return jsonify({
                'message': 'No data provided',
                'status': 'error',
                'code': 400
            }), 400
        
        if not skid:
            raise ValueError("School ID (skid) is required")
        
        denied = _class_teacher_guard(skid, data.get('records'), data.get('section_id'))
        if denied:
            return denied
        updated_records = AttendanceService.update_attendance_bulk(data, skid, getattr(request.current_user, 'school_user_id', None))
        
        return jsonify({
            'message': 'Attendance updated successfully',
            'data': updated_records,
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
            'message': f'Failed to update attendance: {str(e)}',
            'status': 'error',
            'code': 500
        }), 500


@attendance_bp.route('/<skid>/<section_id>/<date>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'TEACHER'], permission=('view_attendance', 'manage_attendance'))
def get_attendance(skid, section_id, date):
    """
    Get attendance records for a specific section and date
    """
    try:
        if not skid or not section_id or not date:
            raise ValueError("School ID, Section ID, and Date are required")
        to_date(date, "Date")  # plain message instead of Python's parser text (QA D25)

        attendance = AttendanceService.get_attendance(skid, section_id, date)
        
        return jsonify({
            'message': 'Attendance fetched successfully',
            'data': attendance,
            'status': 'success',
            'code': 200
        }), 200
        
    except ValueError as e:
        return jsonify({'message': str(e)}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to fetch attendance: {str(e)}'}), 500


@attendance_bp.route('/view/<skid>/<academic_year_id>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'TEACHER'], permission=('view_attendance', 'manage_attendance'))
@log_actions('VIEW-SINGLE-DAY-ATTENDANCE')
def view_single_day_attendance(skid, academic_year_id):
    """
    View attendance for a specific date
    
    Query Parameters:
        - class_id (required): Class ID
        - section_id (required): Section ID
        - date (required): Date in YYYY-MM-DD format
    
    Returns:
        JSON response with attendance records and statistics
    """
    try:
        class_id = request.args.get('class_id', type=int)
        section_id = request.args.get('section_id', type=int)
        date_str = request.args.get('date')
        
        # Validate required parameters
        if not all([class_id, section_id, date_str]):
            return jsonify({
                'message': 'class_id, section_id and date are required',
                'status': 'error',
                'code': 400
            }), 400
        
        # Parse date
        try:
            attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'message': 'Invalid date format. Use YYYY-MM-DD',
                'status': 'error',
                'code': 400
            }), 400
        
        # Fetch attendance data from service
        result = AttendanceService.get_single_day_attendance(
            skid, academic_year_id, class_id, section_id, attendance_date
        )
        
        return jsonify({
            'message': 'Attendance fetched successfully',
            'data': result,
            'status': 'success',
            'code': 200
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Failed to fetch attendance: {str(e)}',
            'status': 'error',
            'code': 500
        }), 500


@attendance_bp.route('/monthly/<skid>/<academic_year_id>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'TEACHER'], permission=('view_attendance', 'manage_attendance'))
@log_actions('VIEW-MONTHLY-ATTENDANCE')
def view_monthly_attendance(skid, academic_year_id):
    """
    View monthly attendance summary
    
    Query Parameters:
        - class_id (required): Class ID
        - section_id (required): Section ID
        - start_date (required): Start date in YYYY-MM-DD format
        - end_date (required): End date in YYYY-MM-DD format
    
    Returns:
        JSON response with monthly attendance summary for all students
    """
    try:
        class_id = request.args.get('class_id', type=int)
        section_id = request.args.get('section_id', type=int)
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        # Validate required parameters
        if not all([class_id, section_id, start_date_str, end_date_str]):
            return jsonify({
                'message': 'class_id, section_id, start_date and end_date are required',
                'status': 'error',
                'code': 400
            }), 400
        
        # Parse dates
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'message': 'Invalid date format. Use YYYY-MM-DD',
                'status': 'error',
                'code': 400
            }), 400
        
        # Validate date range
        if start_date > end_date:
            return jsonify({
                'message': 'start_date cannot be after end_date',
                'status': 'error',
                'code': 400
            }), 400
        
        # Fetch monthly attendance from service
        monthly_summary = AttendanceService.get_monthly_attendance(
            skid, academic_year_id, class_id, section_id, start_date, end_date
        )
        
        return jsonify({
            'message': 'Monthly attendance fetched successfully',
            'data': monthly_summary,
            'count': len(monthly_summary),
            'status': 'success',
            'code': 200
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Failed to fetch monthly attendance: {str(e)}',
            'status': 'error',
            'code': 500
        }), 500


@attendance_bp.route('/range/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'TEACHER'], permission=('view_attendance', 'manage_attendance'))
@log_actions('VIEW-DATE-RANGE-ATTENDANCE')
def view_date_range_attendance(skid):
    """
    View attendance for a date range (grouped by date)
    
    Query Parameters:
        - class_id (required): Class ID
        - section_id (required): Section ID
        - start_date (required): Start date in YYYY-MM-DD format
        - end_date (required): End date in YYYY-MM-DD format
    
    Returns:
        JSON response with attendance records grouped by date
    """
    try:
        class_id = request.args.get('class_id', type=int)
        section_id = request.args.get('section_id', type=int)
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        # Validate required parameters
        if not all([class_id, section_id, start_date_str, end_date_str]):
            return jsonify({
                'message': 'class_id, section_id, start_date and end_date are required',
                'status': 'error',
                'code': 400
            }), 400
        
        # Parse dates
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'message': 'Invalid date format. Use YYYY-MM-DD',
                'status': 'error',
                'code': 400
            }), 400
        
        # Fetch date range attendance
        result = AttendanceService.get_date_range_attendance(
            skid, class_id, section_id, start_date, end_date
        )
        
        return jsonify({
            'message': 'Date range attendance fetched successfully',
            'data': result,
            'count': len(result),
            'status': 'success',
            'code': 200
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Failed to fetch date range attendance: {str(e)}',
            'status': 'error',
            'code': 500
        }), 500


@attendance_bp.route('/student/<skid>/<int:student_id>', methods=['GET'])
# students too (their own only): student_access_required limits students to themselves, parents to their children
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'TEACHER', 'PARENT', 'STUDENT'], permission=('view_attendance', 'manage_attendance'), own_roles=('STUDENT', 'PARENT'))
@student_access_required('student_id')
@log_actions('VIEW-STUDENT-ATTENDANCE')
def view_student_attendance(skid, student_id):
    """
    View attendance for a specific student
    
    Query Parameters:
        - start_date (optional): Start date in YYYY-MM-DD format
        - end_date (optional): End date in YYYY-MM-DD format
    
    Returns:
        JSON response with student attendance records and statistics
    """
    try:
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        start_date = None
        end_date = None
        
        # Parse dates if provided
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'message': 'Invalid start_date format. Use YYYY-MM-DD',
                    'status': 'error',
                    'code': 400
                }), 400
        
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'message': 'Invalid end_date format. Use YYYY-MM-DD',
                    'status': 'error',
                    'code': 400
                }), 400
        
        # Fetch student attendance
        result = AttendanceService.get_attendance_by_student(
            skid, student_id, start_date, end_date
        )
        
        return jsonify({
            'message': 'Student attendance fetched successfully',
            'data': result,
            'status': 'success',
            'code': 200
        }), 200
        
    except ValueError as e:
        return jsonify({
            'message': str(e),
            'status': 'error',
            'code': 404
        }), 404
    except Exception as e:
        return jsonify({
            'message': f'Failed to fetch student attendance: {str(e)}',
            'status': 'error',
            'code': 500
        }), 500
