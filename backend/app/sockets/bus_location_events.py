from flask import current_app
from flask_socketio import emit, join_room, leave_room
from flask_jwt_extended import decode_token
from app import socketio
from app.services.bus_location_service import BusLocationService


def _get_user_from_token(token):
    """Decode JWT and return user ID + user object, or None."""
    try:
        decoded = decode_token(token)
        user_id = decoded.get('sub')
        if not user_id:
            return None
        from app.models.main.User import User
        return User.get_by_id(user_id)
    except Exception:
        return None


@socketio.on('connect')
def handle_connect(auth=None):
    """Authenticate WebSocket connections via JWT token."""
    token = None
    if auth and isinstance(auth, dict):
        token = auth.get('token')
    if not token:
        return False  # reject connection

    user = _get_user_from_token(token)
    if not user:
        return False
    # Store user info in the session for later use
    from flask import request
    request.environ['ws_user'] = user
    return True


@socketio.on('join_bus_room')
def handle_join_room(data):
    """Parent joins a bus staff's room to receive location updates."""
    skid = data.get('skid')
    bus_staff_user_id = data.get('bus_staff_user_id')
    if not skid or not bus_staff_user_id:
        return
    room = f"bus_{skid}_{bus_staff_user_id}"
    join_room(room)
    emit('room_joined', {'room': room})


@socketio.on('leave_bus_room')
def handle_leave_room(data):
    """Parent leaves a bus room."""
    skid = data.get('skid')
    bus_staff_user_id = data.get('bus_staff_user_id')
    if not skid or not bus_staff_user_id:
        return
    room = f"bus_{skid}_{bus_staff_user_id}"
    leave_room(room)


@socketio.on('bus_location_update')
def handle_location_update(data):
    """Bus staff sends GPS update → persist + broadcast to parents in the room."""
    from flask import request
    user = request.environ.get('ws_user')
    if not user:
        return

    skid = data.get('skid')
    lat = data.get('latitude')
    lng = data.get('longitude')
    if not skid or lat is None or lng is None:
        return

    bus_staff_user_id = user.school_user_id

    # Persist (overwrite single row)
    try:
        BusLocationService.upsert_location(
            skid, bus_staff_user_id, lat, lng,
            heading=data.get('heading'),
            speed=data.get('speed'),
        )
    except Exception as e:
        current_app.logger.error(f"Bus location persist error: {e}")

    # Broadcast to all parents watching this bus
    room = f"bus_{skid}_{bus_staff_user_id}"
    emit('bus_location_update', {
        'bus_staff_user_id': bus_staff_user_id,
        'latitude': lat,
        'longitude': lng,
        'heading': data.get('heading'),
        'speed': data.get('speed'),
    }, to=room, include_self=False)


@socketio.on('bus_stop_tracking')
def handle_stop_tracking(data):
    """Bus staff stops broadcasting → mark inactive + notify parents."""
    from flask import request
    user = request.environ.get('ws_user')
    if not user:
        return

    skid = data.get('skid')
    if not skid:
        return

    bus_staff_user_id = user.school_user_id

    try:
        BusLocationService.stop_tracking(skid, bus_staff_user_id)
    except Exception as e:
        current_app.logger.error(f"Bus location stop error: {e}")

    room = f"bus_{skid}_{bus_staff_user_id}"
    emit('bus_stopped', {
        'bus_staff_user_id': bus_staff_user_id,
    }, to=room, include_self=False)


@socketio.on('disconnect')
def handle_disconnect():
    """If bus staff disconnects unexpectedly, mark inactive."""
    from flask import request
    user = request.environ.get('ws_user')
    if not user or not hasattr(user, 'role'):
        return
    if user.role.value == 'BUS_STAFF' and user.skid:
        try:
            BusLocationService.stop_tracking(user.skid, user.school_user_id)
            room = f"bus_{user.skid}_{user.school_user_id}"
            emit('bus_stopped', {
                'bus_staff_user_id': user.school_user_id,
            }, to=room)
        except Exception:
            pass
