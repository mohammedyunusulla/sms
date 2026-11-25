"""Calendar page (/api/calendar): holidays, weekly offs, exams and leave for a date range, per person."""
from flask import Blueprint, request, jsonify

from app.decorators.auth import login_required
from app.services.calendar_service import calendar_events, CalendarError

calendar_bp = Blueprint('calendar', __name__)

EVERYONE = ['INSTITUTION_ADMIN', 'PRINCIPAL', 'TEACHER', 'CLERK', 'BUS_STAFF', 'STUDENT', 'PARENT']


@calendar_bp.route('/events/<skid>', methods=['GET'])
@login_required(EVERYONE, self_service=True)
def events(skid):
    """?from=YYYY-MM-DD&to=YYYY-MM-DD (at most two months); parents may add &student_id= for one child."""
    try:
        data = calendar_events(skid, request.current_user, request.args.get('from'), request.args.get('to'),
                               request.args.get('student_id', type=int))
        return jsonify({'status': 'success', 'data': data}), 200
    except CalendarError as e:
        return jsonify({'status': 'error', 'message': str(e)}), e.code
