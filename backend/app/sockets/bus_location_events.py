from flask import current_app
from flask_socketio import emit, join_room, leave_room
from flask_jwt_extended import decode_token
from app import socketio
from app.services.bus_location_service import BusLocationService


def _get_user_from_token(token):
    """
    Decode the JWT and return the active user, or None.
    Mirrors the REST checks: the session must not be logged out and the account must be active.
    """
    try:
        decoded = decode_token(token)
        user_id = decoded.get('sub')
        session_token = decoded.get('session_token')
        if not user_id or not session_token:
            return None
        from app.models.main.UserSession import UserSession
        if UserSession.get_active_session(session_token) is None:
            return None  # logged out / revoked session
        from app.models.main.User import User
        user = User.get_by_id(user_id)
        if not user or not user.is_active:
            return None
        return user
    except Exception:
        return None


def _ws_user():
    from flask import request
    return request.environ.get('ws_user')


def _role(user):
    return user.role.value if hasattr(user.role, 'value') else str(user.role)


def _same_institution(user, skid):
    """Super admins may watch any institution; everyone else only their own."""
    return _role(user) == 'SUPER_ADMIN' or str(skid) == str(user.skid)


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
    user = _ws_user()
    if not user:
        return
    skid = data.get('skid')
    bus_staff_user_id = data.get('bus_staff_user_id')
    if not skid or not bus_staff_user_id:
        return
    if not _same_institution(user, skid):
        current_app.logger.warning(f"WS cross-institution join blocked: user {user.id} (skid={user.skid}) -> {skid}")
        emit('error', {'message': 'Access denied: you can only track buses of your own institution'})
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
    user = _ws_user()
    if not user:
        return
    if _role(user) != 'BUS_STAFF':
        emit('error', {'message': 'Only bus staff can send bus locations'})
        return

    # The institution always comes from the user's own record, never from the client.
    skid = user.skid
    if data.get('skid') and str(data.get('skid')) != str(skid):
        current_app.logger.warning(f"WS cross-institution location update blocked: user {user.id} (skid={skid}) -> {data.get('skid')}")
        emit('error', {'message': 'Access denied: you can only update buses of your own institution'})
        return
    lat = data.get('latitude')
    lng = data.get('longitude')
    if not skid or lat is None or lng is None:
        return

    bus_staff_user_id = user.institution_user_id

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
    user = _ws_user()
    if not user:
        return
    if _role(user) != 'BUS_STAFF':
        emit('error', {'message': 'Only bus staff can stop bus tracking'})
        return

    skid = user.skid
    if data.get('skid') and str(data.get('skid')) != str(skid):
        current_app.logger.warning(f"WS cross-institution stop blocked: user {user.id} (skid={skid}) -> {data.get('skid')}")
        emit('error', {'message': 'Access denied: you can only update buses of your own institution'})
        return
    if not skid:
        return

    bus_staff_user_id = user.institution_user_id

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
            BusLocationService.stop_tracking(user.skid, user.institution_user_id)
            room = f"bus_{user.skid}_{user.institution_user_id}"
            emit('bus_stopped', {
                'bus_staff_user_id': user.institution_user_id,
            }, to=room)
        except Exception:
            pass
