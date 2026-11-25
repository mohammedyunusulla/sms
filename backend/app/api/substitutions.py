"""
Substitute teacher planner (/api/substitutions): the Institution Admin or anyone with "manage_timetable".
"""
from flask import Blueprint, request, jsonify

from app.decorators.auth import login_required
from app.services.substitution_service import SubstitutionService, SubstitutionError

substitutions_bp = Blueprint('substitutions', __name__)

MANAGERS = ['SUPER_ADMIN', 'INSTITUTION_ADMIN', 'PRINCIPAL']


def _run(fn, *args, ok=200):
    try:
        return jsonify({'status': 'success', 'data': fn(*args)}), ok
    except SubstitutionError as e:
        return jsonify({'status': 'error', 'message': str(e)}), e.code
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


def _actor():
    return getattr(request.current_user, 'institution_user_id', None)


def _body():
    return request.get_json(silent=True) or {}


@substitutions_bp.route('/day/<skid>', methods=['GET'])
@login_required(MANAGERS, permission='manage_timetable')
def day(skid):
    """Periods needing cover on ?date=, with suggestions."""
    return _run(SubstitutionService.day, skid, request.args.get('date'))


@substitutions_bp.route('/teacher-periods/<skid>', methods=['GET'])
@login_required(MANAGERS, permission='manage_timetable')
def teacher_periods(skid):
    return _run(SubstitutionService.teacher_periods, skid, request.args.get('date'), request.args.get('teacher_id', type=int))


@substitutions_bp.route('/assign/<skid>', methods=['POST'])
@login_required(MANAGERS, permission='manage_timetable')
def assign(skid):
    b = _body()
    return _run(SubstitutionService.assign, skid, _actor(), b.get('date'), b.get('entry_id'), b.get('substitute_id'), b.get('note'))


@substitutions_bp.route('/assign-all/<skid>', methods=['POST'])
@login_required(MANAGERS, permission='manage_timetable')
def assign_all(skid):
    return _run(SubstitutionService.assign_all, skid, _actor(), _body().get('date'))


@substitutions_bp.route('/remove/<skid>', methods=['POST'])
@login_required(MANAGERS, permission='manage_timetable')
def remove(skid):
    b = _body()
    return _run(SubstitutionService.remove, skid, b.get('date'), b.get('entry_id'))


@substitutions_bp.route('/mark/<skid>', methods=['POST'])
@login_required(MANAGERS, permission='manage_timetable')
def mark(skid):
    """Mark periods of a present teacher as needing cover (exam duty, meetings)."""
    b = _body()
    return _run(SubstitutionService.mark_manual, skid, _actor(), b.get('date'), b.get('entry_ids'), b.get('note'))


@substitutions_bp.route('/unmark/<skid>', methods=['POST'])
@login_required(MANAGERS, permission='manage_timetable')
def unmark(skid):
    b = _body()
    return _run(SubstitutionService.unmark, skid, b.get('date'), b.get('entry_id'))


@substitutions_bp.route('/today/<skid>', methods=['GET'])
@login_required(MANAGERS, permission='manage_timetable')
def today(skid):
    """Dashboard strip: periods still needing a substitute today."""
    return _run(SubstitutionService.uncovered_today, skid)
