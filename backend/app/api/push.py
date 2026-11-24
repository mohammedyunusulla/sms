"""Push notifications: turn them on/off for this device. Any signed-in user, for themselves only."""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import get_jwt

from app.decorators.auth import login_required
from app.services import push_service

push_bp = Blueprint('push', __name__)


def _endpoint():
    return str((request.get_json(silent=True) or {}).get('endpoint') or '').strip()


@push_bp.route('/config', methods=['GET'])
@login_required(self_service=True)
def config():
    """Whether the server can send notifications, and the key the browser needs to subscribe."""
    return jsonify({'enabled': push_service.is_configured(), 'public_key': push_service.public_key() or None}), 200


@push_bp.route('/subscribe', methods=['POST'])
@login_required(self_service=True)
def subscribe():
    if not push_service.is_configured():
        return jsonify({'message': "Notifications aren't set up on this server yet"}), 503
    body = request.get_json(silent=True) or {}
    try:
        push_service.subscribe(request.current_user, get_jwt().get('session_token'), body.get('subscription'),
                               request.headers.get('User-Agent'))
    except ValueError as e:
        return jsonify({'message': str(e)}), 400
    return jsonify({'message': 'Notifications turned on for this device'}), 200


@push_bp.route('/unsubscribe', methods=['POST'])
@login_required(self_service=True)
def unsubscribe():
    push_service.unsubscribe(request.current_user, _endpoint())
    return jsonify({'message': 'Notifications turned off for this device'}), 200


@push_bp.route('/status', methods=['POST'])
@login_required(self_service=True)
def status():
    """Is this device (endpoint) registered for the signed-in user? The browser alone can't tell after a user switch."""
    return jsonify({'subscribed': push_service.is_subscribed(request.current_user, _endpoint())}), 200


@push_bp.route('/test', methods=['POST'])
@login_required(self_service=True)
def test():
    """Send a test notification to the signed-in user's own devices."""
    if not push_service.is_configured():
        return jsonify({'message': "Notifications aren't set up on this server yet"}), 503
    push_service.notify([request.current_user.id], "EduSpyre notifications are on 🔔",
                        "You'll get alerts here for announcements, homework, results and attendance.",
                        url='/dashboard', tag='eduspyre-test')
    current_app.logger.info(f"Test push queued for user {request.current_user.id}")
    return jsonify({'message': 'Test notification sent'}), 200
