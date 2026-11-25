"""
Staff attendance (/api/staff-attendance): mark a day and see the monthly register (Institution Admin or the
"manage_staff_attendance" tick box); every staff member sees their own month; loss of pay on a pending salary.
"""
from flask import Blueprint, request, jsonify

from app.decorators.auth import login_required
from app.services.staff_attendance_service import StaffAttendanceService, StaffAttendanceError, apply_loss_of_pay

staff_attendance_bp = Blueprint('staff_attendance', __name__)

MANAGERS = ['SUPER_ADMIN', 'INSTITUTION_ADMIN', 'PRINCIPAL']
STAFF = ['PRINCIPAL', 'TEACHER', 'CLERK', 'BUS_STAFF']


def _run(fn, *args, ok=200):
    try:
        return jsonify({'status': 'success', 'data': fn(*args)}), ok
    except StaffAttendanceError as e:
        return jsonify({'status': 'error', 'message': str(e)}), e.code
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@staff_attendance_bp.route('/day/<skid>', methods=['GET'])
@login_required(MANAGERS, permission='manage_staff_attendance')
def get_day(skid):
    return _run(StaffAttendanceService.get_day, skid, request.args.get('date'))


@staff_attendance_bp.route('/day/<skid>', methods=['POST'])
@login_required(MANAGERS, permission='manage_staff_attendance')
def save_day(skid):
    body = request.get_json(silent=True) or {}
    actor = getattr(request.current_user, 'institution_user_id', None)
    return _run(StaffAttendanceService.save_day, skid, body.get('date'), body.get('records'), actor)


@staff_attendance_bp.route('/register/<skid>', methods=['GET'])
@login_required(MANAGERS, permission='manage_staff_attendance')
def register(skid):
    return _run(StaffAttendanceService.register, skid, request.args.get('year'), request.args.get('month'))


@staff_attendance_bp.route('/my/<skid>', methods=['GET'])
@login_required(STAFF, self_service=True)
def my_month(skid):
    return _run(StaffAttendanceService.my_month, skid, request.current_user,
                request.args.get('year'), request.args.get('month'))


@staff_attendance_bp.route('/loss-of-pay/<skid>/<int:payment_id>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN'], permission='manage_salaries')
def loss_of_pay(skid, payment_id):
    """{"apply": true} adds the suggested loss of pay to a pending salary payment; false removes it."""
    body = request.get_json(silent=True) or {}
    return _run(apply_loss_of_pay, skid, payment_id, bool(body.get('apply', True)))
