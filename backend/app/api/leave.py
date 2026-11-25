"""
Leave requests (/api/leave). Every route is for the signed-in user's own requests or decisions; who may see or
decide what is checked in LeaveService (class teacher of the section, Institution Admin, or the "approve_leave"
tick box), so the routes are decided by role / self-service.
"""
from flask import Blueprint, request, jsonify

from app.decorators.auth import login_required
from app.services.leave_service import LeaveService, LeaveError

leave_bp = Blueprint('leave', __name__)

APPLICANT_ROLES = ['PRINCIPAL', 'TEACHER', 'CLERK', 'BUS_STAFF', 'STUDENT', 'PARENT']
STAFF_ROLES = ['INSTITUTION_ADMIN', 'PRINCIPAL', 'TEACHER', 'CLERK', 'BUS_STAFF']


def _run(fn, *args, ok=200):
    try:
        return jsonify({'status': 'success', 'data': fn(*args)}), ok
    except LeaveError as e:
        return jsonify({'status': 'error', 'message': str(e)}), e.code
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@leave_bp.route('/my/<skid>', methods=['GET'])
@login_required(APPLICANT_ROLES, self_service=True)
def my_requests(skid):
    """Own requests (student / staff), or a parent's child's (?student_id=)."""
    return _run(LeaveService.my_requests, skid, request.current_user, request.args.get('student_id', type=int))


@leave_bp.route('/apply/<skid>', methods=['POST'])
@login_required(APPLICANT_ROLES, self_service=True)
def apply(skid):
    return _run(LeaveService.apply, skid, request.current_user, request.get_json(silent=True), ok=201)


@leave_bp.route('/cancel/<skid>/<int:leave_id>', methods=['POST'])
@login_required(APPLICANT_ROLES, self_service=True)
def cancel(skid, leave_id):
    return _run(LeaveService.cancel, skid, request.current_user, leave_id)


@leave_bp.route('/requests/<skid>', methods=['GET'])
@login_required(STAFF_ROLES, self_service=True)
def review_list(skid):
    """Requests the signed-in approver can decide (all, or their class-teacher sections)."""
    filters = {k: request.args.get(k) for k in ('status', 'applicant_type', 'section_id', 'from_date', 'to_date', 'search')}
    return _run(LeaveService.review_list, skid, request.current_user, filters)


@leave_bp.route('/pending-count/<skid>', methods=['GET'])
@login_required(STAFF_ROLES, self_service=True)
def pending_count(skid):
    return _run(LeaveService.pending_count, skid, request.current_user)


@leave_bp.route('/decide/<skid>/<int:leave_id>', methods=['POST'])
@login_required(STAFF_ROLES, self_service=True)
def decide(skid, leave_id):
    body = request.get_json(silent=True) or {}
    return _run(LeaveService.decide, skid, request.current_user, leave_id, body.get('decision'), body.get('note'))


@leave_bp.route('/policy/<skid>', methods=['GET'])
@login_required(STAFF_ROLES, self_service=True)
def get_policy(skid):
    """Paid staff leave per type for the current academic year (None = no limit)."""
    return _run(LeaveService.get_policy, skid)


@leave_bp.route('/policy/<skid>', methods=['PUT'])
@login_required(STAFF_ROLES, self_service=True)
def save_policy(skid):
    """{"types": [{"type": "CASUAL", "paid_days": 12}, ...]} - Institution Admin / "approve_leave" only (checked in the service)."""
    body = request.get_json(silent=True) or {}
    return _run(LeaveService.save_policy, skid, request.current_user, body.get('types'))


@leave_bp.route('/on-leave/<skid>', methods=['GET'])
@login_required(STAFF_ROLES, permission=('manage_attendance', 'view_attendance'))
def on_leave(skid):
    """Students of a section with approved leave on a day (Mark Attendance shows them as Leave)."""
    section_id = request.args.get('section_id', type=int)
    day = request.args.get('date')
    if not section_id or not day:
        return jsonify({'status': 'error', 'message': 'section_id and date are required'}), 400
    from app.services.leave_service import _parse_day
    try:
        parsed = _parse_day(day, 'Date')
    except LeaveError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    on_leave = LeaveService.students_on_leave(skid, section_id, parsed)
    return jsonify({'status': 'success', 'data': {str(k): v for k, v in on_leave.items()}}), 200
