from flask import Blueprint, request, jsonify
from app.services.teacher_service import TeacherService
from app.decorators import log_actions, login_required
from app.decorators.auth import student_access_required
from app.models.main.User import UserRole
from app.services.timeTable_service import TimetableService
from datetime import datetime

timeTable_bp = Blueprint('timeTable', __name__)

@timeTable_bp.route('/generate/time-slots', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
@log_actions('GENERATE_TIME_SLOTS')
def generate_time_slots():
    """Generate time slots based on configuration"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No data provided'}), 400
        
        time_slots = TimetableService.generate_time_slots({
            'school_start_time': data.get('school_start_time', '09:00'),
            'lunch_start_time': data.get('lunch_start_time', '12:30'),
            'lunch_duration': data.get('lunch_duration', 30),
            'period_duration': data.get('period_duration', 45),
            'total_periods': data.get('total_periods', 7)
        })
        print(time_slots)
        
        return jsonify({
            'code': 200,
            'status': 'success',
            'message': 'Time slots generated successfully',
            'data': time_slots
        }), 200
        
    except Exception as e:
        print(f"Error generating time slots: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'message': 'Internal server error',
            'data': None
        }), 500
        
@timeTable_bp.route('/check-teacher-conflict', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
@log_actions('CHECK_TEACHER_CONFLICT')
def check_teacher_conflict():
    """Check if a teacher has scheduling conflicts for a specific time slot"""
    try:
        data = request.get_json()
        
        required_fields = ['skid', 'teacher_id', 'day', 'start_time', 'end_time', 'academic_year_id', 'semester']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'code': 400,
                    'status': 'error',
                    'message': f'Missing required field: {field}',
                    'data': None
                }), 400
        
        conflicts = TimetableService.check_teacher_conflicts(
            skid=data['skid'],
            teacher_id=data['teacher_id'],
            day=data['day'],
            start_time=data['start_time'],
            end_time=data['end_time'],
            academic_year_id=data['academic_year_id'],
            semester=data['semester'],
            exclude_timetable_id=data.get('exclude_timetable_id')
        )
        
        return jsonify({
            'code': 200,
            'status': 'success',
            'message': 'Conflict check completed',
            'data': conflicts
        }), 200
        
    except Exception as e:
        # logger.error(f"Error checking teacher conflict: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'message': 'Internal server error',
            'data': None
        }), 500


@timeTable_bp.route('/create', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
def create_timetable():
    """Create or update a timetable with draft support"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['skid', 'class_id', 'section_id', 'academic_year_id', 'semester']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'code': 400,
                    'status': 'error',
                    'message': f'Missing required field: {field}',
                    'data': None
                }), 400
        
        # Check if saving as draft
        is_draft = data.get('is_draft', False)
        
        # Transform entries data to match expected format
        entries = {}
        for entry_key, entry_data in data.get('entries', {}).items():
            entries[entry_key] = {
                'subject_id': entry_data['subject']['id'] if isinstance(entry_data['subject'], dict) else entry_data['subject'],
                'teacher_id': entry_data.get('teacher_id') or (
                    entry_data['teacher']['id'] if isinstance(entry_data.get('teacher'), dict) 
                    else entry_data.get('teacher')
                ),
                'room': entry_data.get('room', ''),
                'type': entry_data.get('type', 'Regular')
            }
        
        timetable_data = {
            'skid': data['skid'],
            'class_id': data['class_id'],
            'section_id': data['section_id'],
            'academic_year_id': data['academic_year_id'],
            'semester': data['semester'],
            'period_duration': data.get('period_duration', 45),
            'school_start_time': data.get('school_start_time', '09:00'),
            'lunch_start_time': data.get('lunch_start_time', '12:30'),
            'lunch_duration': data.get('lunch_duration', 30),
            'total_periods': data.get('total_periods', 7),
            'entries': entries
        }
        
        result = TimetableService.create_or_update_timetable(
            data['skid'], timetable_data, is_draft=is_draft
        )
        
        if result['success']:
            return jsonify({
                'code': 201,
                'status': 'success',
                'message': result['message'],
                'data': {
                    'timetable_id': result['timetable_id'],
                    'entries_created': result['entries_created'],
                    'is_draft': result.get('is_draft', False)
                }
            }), 201
        else:
            return jsonify({
                'code': 400,
                'status': 'error',
                'message': result['message'],
                'data': result.get('conflicts', None)
            }), 400
        
    except Exception as e:
        print(f"Error in create_timetable: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'message': 'Internal server error',
            'data': None
        }), 500

@timeTable_bp.route('/save-draft', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
@log_actions('SAVE_TIMETABLE_DRAFT')
def save_draft():
    """Save timetable as draft without validation"""
    try:
        data = request.get_json()
        
        # Transform entries data
        entries = {}
        for entry_key, entry_data in data.get('entries', {}).items():
            entries[entry_key] = {
                'subject_id': entry_data['subject']['id'] if isinstance(entry_data['subject'], dict) else entry_data['subject'],
                'teacher_id': entry_data.get('teacher_id') or (
                    entry_data['teacher']['id'] if isinstance(entry_data.get('teacher'), dict) 
                    else entry_data.get('teacher')
                ),
                'room': entry_data.get('room', ''),
                'type': entry_data.get('type', 'Regular')
            }
        
        timetable_data = {
            'skid': data['skid'],
            'class_id': data['class_id'],
            'section_id': data['section_id'],
            'academic_year_id': data['academic_year_id'],
            'semester': data['semester'],
            'period_duration': data.get('period_duration', 45),
            'school_start_time': data.get('school_start_time', '09:00'),
            'lunch_start_time': data.get('lunch_start_time', '12:30'),
            'lunch_duration': data.get('lunch_duration', 30),
            'total_periods': data.get('total_periods', 7),
            'entries': entries
        }
        
        # Save as draft (skip validation)
        result = TimetableService.create_or_update_timetable(
            data['skid'], timetable_data, is_draft=True
        )
        
        if result['success']:
            return jsonify({
                'code': 201,
                'status': 'success',
                'message': 'Timetable saved as draft successfully',
                'data': {
                    'timetable_id': result['timetable_id'],
                    'entries_created': result['entries_created'],
                    'is_draft': True
                }
            }), 201
        else:
            return jsonify({
                'code': 400,
                'status': 'error',
                'message': result['message'],
                'data': None
            }), 400
        
    except Exception as e:
        print(f"Error saving draft: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'message': 'Internal server error',
            'data': None
        }), 500

@timeTable_bp.route('/publish-draft', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
@log_actions('PUBLISH_TIMETABLE_DRAFT')
def publish_draft():
    """Convert draft timetable to final published version"""
    try:
        data = request.get_json()
        
        required_fields = ['skid', 'timetable_id']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'code': 400,
                    'status': 'error',
                    'message': f'Missing required field: {field}',
                    'data': None
                }), 400
        
        result = TimetableService.publish_draft_timetable(
            data['skid'], data['timetable_id']
        )
        
        if result['success']:
            return jsonify({
                'code': 200,
                'status': 'success',
                'message': result['message'],
                'data': None
            }), 200
        else:
            return jsonify({
                'code': 400,
                'status': 'error',
                'message': result['message'],
                'data': result.get('conflicts', None)
            }), 400
        
    except Exception as e:
        print(f"Error publishing draft: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'message': 'Internal server error',
            'data': None
        }), 500
        
@timeTable_bp.route('/view/<skid>/<int:timetable_id>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'TEACHER'])
@log_actions('VIEW_TIMETABLE')
def get_timetable_by_id(skid, timetable_id):
    """Get timetable by ID"""
    try:
        timetable = TimetableService.get_timetable_by_id(skid, timetable_id)
        
        if timetable:
            return jsonify({
                'code': 200,
                'status': 'success',
                'message': 'Timetable fetched successfully',
                'data': timetable
            }), 200
        else:
            return jsonify({
                'code': 404,
                'status': 'error',
                'message': 'Timetable not found',
                'data': None
            }), 404
            
    except Exception as e:
        print(f"Error fetching timetable: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'message': str(e),
            'data': None
        }), 500



@timeTable_bp.route('/list/<skid>/<academic_year_id>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'TEACHER'])
def list_timetables(skid, academic_year_id):
    """Get all timetables for a school"""
    try:
        print("coming here")
        semester = request.args.get('semester')
        
        timetables = TimetableService.get_all_timetables_by_school(
            skid, academic_year_id, semester
        )
        
        return jsonify({
            'code': 200,
            'status': 'success',
            'message': 'Timetables fetched successfully',
            'data': timetables
        }), 200
        
    except Exception as e:
        print(f"Error in list_timetables: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'message': 'Internal server error',
            'data': None
        }), 500

@timeTable_bp.route('/drafts/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
def list_draft_timetables(skid):
    """Get all draft timetables for a school"""
    try:
        academic_year_id = request.args.get('academic_year_id')
        semester = request.args.get('semester')
        
        drafts = TimetableService.get_draft_timetables(skid, academic_year_id, semester)
        
        return jsonify({
            'code': 200,
            'status': 'success',
            'message': 'Draft timetables fetched successfully',
            'data': drafts
        }), 200
        
    except Exception as e:
        print(f"Error in list_draft_timetables: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'message': 'Internal server error',
            'data': None
        }), 500

@timeTable_bp.route('/teacher-schedule/<int:teacher_id>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
def get_teacher_schedule(teacher_id):
    """Get teacher's complete schedule"""
    try:
        academic_year_id = request.args.get('academic_year_id')
        semester = request.args.get('semester')
        
        if not academic_year_id or not semester:
            return jsonify({
                'code': 400,
                'status': 'error',
                'message': 'Missing required parameters: academic_year_id, semester',
                'data': None
            }), 400
        
        schedule = TimetableService.get_teacher_schedule(teacher_id, academic_year_id, semester)
        
        return jsonify({
            'code': 200,
            'status': 'success',
            'message': 'Teacher schedule fetched successfully',
            'data': schedule
        }), 200
        
    except Exception as e:
        print(f"Error in get_teacher_schedule: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'message': 'Internal server error',
            'data': None
        }), 500

@timeTable_bp.route('/delete/<int:timetable_id>', methods=['DELETE'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
def delete_timetable(timetable_id):
    """Delete a timetable"""
    try:
        skid = request.args.get('skid')
        
        if not skid:
            return jsonify({
                'code': 400,
                'status': 'error',
                'message': 'Missing required parameter: skid',
                'data': None
            }), 400
        
        result = TimetableService.delete_timetable(timetable_id, skid)
        
        if result['success']:
            return jsonify({
                'code': 200,
                'status': 'success',
                'message': result['message'],
                'data': None
            }), 200
        else:
            return jsonify({
                'code': 404,
                'status': 'error',
                'message': result['message'],
                'data': None
            }), 404
        
    except Exception as e:
        print(f"Error in delete_timetable: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'message': 'Internal server error',
            'data': None
        }), 500

@timeTable_bp.route('/student/<skid>/<student_id>/<date>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER', 'STUDENT', 'PARENT'])
@student_access_required('student_id')
def get_student_timetable(skid, student_id, date):
    """
    Get student's class timetable for a specific day.

    URL params:
    - skid: School ID (required)
    - student_id: Student's school_user_id (required)
    - date: Date in YYYY-MM-DD format (required)

    Returns periods for the student's section on the given day with teacher names.
    """
    try:
        if not skid or not student_id or not date:
            return jsonify({
                'message': 'skid, student_id, and date are required',
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

        timetable_data = TimetableService.get_student_timetable_by_day(
            skid=skid,
            student_id=student_id,
            date=date
        )

        return jsonify({
            'message': 'Student timetable fetched successfully',
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
            'message': f'Failed to fetch student timetable: {str(e)}',
            'status': 'error',
            'code': 500
        }), 500


@timeTable_bp.route('/validate-conflicts', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
def validate_conflicts():
    """Validate timetable for conflicts"""
    try:
        data = request.get_json()
        
        result = TimetableService.validate_timetable_conflicts(data['skid'], data)
        
        return jsonify({
            'code': 200,
            'status': 'success',
            'message': 'Validation completed',
            'data': result
        }), 200
        
    except Exception as e:
        print(f"Error in validate_conflicts: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'message': 'Internal server error',
            'data': None
        }), 500