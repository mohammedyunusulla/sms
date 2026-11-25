"""
Events (/api/events). Managing is checked in EventService: the Institution Admin and the "manage_events"
tick box manage any event; class teachers manage events for their own section(s). Viewing is through the
Calendar feed (/api/calendar/events).
"""
from flask import Blueprint, request, jsonify

from app.decorators.auth import login_required
from app.services.event_service import EventService, EventError

events_bp = Blueprint('events', __name__)

STAFF = ['INSTITUTION_ADMIN', 'PRINCIPAL', 'TEACHER', 'CLERK', 'BUS_STAFF']


def _run(fn, *args, ok=200):
    try:
        return jsonify({'status': 'success', 'data': fn(*args)}), ok
    except EventError as e:
        return jsonify({'status': 'error', 'message': str(e)}), e.code
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@events_bp.route('/options/<skid>', methods=['GET'])
@login_required(STAFF, self_service=True)
def options(skid):
    """What the event form offers this user (types, audiences, sections they may target)."""
    return _run(EventService.options, skid, request.current_user)


@events_bp.route('/<skid>', methods=['POST'])
@login_required(STAFF, self_service=True)
def create(skid):
    return _run(EventService.create, skid, request.current_user, request.get_json(silent=True), ok=201)


@events_bp.route('/<skid>/<int:event_id>', methods=['PUT'])
@login_required(STAFF, self_service=True)
def update(skid, event_id):
    """Edit an event; {"reinstate": true} brings a cancelled one back; {"notify": true} sends a push."""
    return _run(EventService.update, skid, request.current_user, event_id, request.get_json(silent=True))


@events_bp.route('/<skid>/<int:event_id>/cancel', methods=['POST'])
@login_required(STAFF, self_service=True)
def cancel(skid, event_id):
    body = request.get_json(silent=True) or {}
    return _run(EventService.cancel, skid, request.current_user, event_id, bool(body.get('notify')))


@events_bp.route('/<skid>/<int:event_id>', methods=['DELETE'])
@login_required(STAFF, self_service=True)
def delete(skid, event_id):
    return _run(EventService.delete, skid, request.current_user, event_id)
