"""
Holiday calendar (/api/holidays): everyone in the institution can see holidays and off days; adding /
changing them and the weekly offs needs the Institution Admin or the "manage_holidays" tick box.
"""
from flask import Blueprint, request, jsonify

from app.decorators.auth import login_required
from app.services.calendar_service import CalendarService, CalendarError

holidays_bp = Blueprint('holidays', __name__)

EVERYONE = ['INSTITUTION_ADMIN', 'PRINCIPAL', 'TEACHER', 'CLERK', 'BUS_STAFF', 'STUDENT', 'PARENT']
MANAGERS = ['SUPER_ADMIN', 'INSTITUTION_ADMIN', 'PRINCIPAL']


def _run(fn, *args, ok=200):
    try:
        return jsonify({'status': 'success', 'data': fn(*args)}), ok
    except CalendarError as e:
        return jsonify({'status': 'error', 'message': str(e)}), e.code
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


def _actor():
    return getattr(request.current_user, 'institution_user_id', None)


@holidays_bp.route('/list/<skid>', methods=['GET'])
@login_required(EVERYONE, self_service=True)
def list_year(skid):
    """Holidays and weekly offs of an academic year (default: current). Students / parents don't see staff-only holidays."""
    return _run(CalendarService.list_year, skid, request.current_user, request.args.get('academic_year_id'))


@holidays_bp.route('/off-days/<skid>', methods=['GET'])
@login_required(EVERYONE, self_service=True)
def off_days(skid):
    """Weekly offs and holidays between from / to (?audience=STAFF|STUDENTS; students / parents always get STUDENTS)."""
    return _run(CalendarService.off_days, skid, request.current_user, request.args.get('from'),
                request.args.get('to'), request.args.get('audience'))


@holidays_bp.route('/<skid>', methods=['POST'])
@login_required(MANAGERS, permission='manage_holidays')
def create(skid):
    return _run(CalendarService.create, skid, _actor(), request.get_json(silent=True), ok=201)


@holidays_bp.route('/<skid>/<int:holiday_id>', methods=['PUT'])
@login_required(MANAGERS, permission='manage_holidays')
def update(skid, holiday_id):
    """Edit, confirm ({"is_tentative": false}) or move a holiday; {"notify": true} sends a push."""
    return _run(CalendarService.update, skid, _actor(), holiday_id, request.get_json(silent=True))


@holidays_bp.route('/<skid>/<int:holiday_id>', methods=['DELETE'])
@login_required(MANAGERS, permission='manage_holidays')
def delete(skid, holiday_id):
    return _run(CalendarService.delete, skid, holiday_id)


@holidays_bp.route('/settings/<skid>', methods=['PUT'])
@login_required(MANAGERS, permission='manage_holidays')
def save_settings(skid):
    """{"weekly_off_days": [6], "alternate_saturdays": "NONE" | "2_4" | "1_3"} for the current academic year."""
    return _run(CalendarService.save_settings, skid, _actor(), request.get_json(silent=True))


@holidays_bp.route('/tentative-soon/<skid>', methods=['GET'])
@login_required(MANAGERS, permission='manage_holidays')
def tentative_soon(skid):
    """Tentative holidays in the next 3 days (dashboard reminder to confirm or move them)."""
    return _run(CalendarService.tentative_soon, skid)
