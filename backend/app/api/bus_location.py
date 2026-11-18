from flask import Blueprint, request, jsonify
from app.decorators.auth import login_required
from app.services.bus_location_service import BusLocationService

bus_location_bp = Blueprint('bus_location', __name__)


@bus_location_bp.route('/update/<skid>', methods=['POST'])
@login_required(allowed_roles=['BUS_STAFF'])
def update_location(skid):
    """REST fallback: bus staff pushes GPS coords when WebSocket is unavailable."""
    data = request.get_json() or {}
    lat = data.get('latitude')
    lng = data.get('longitude')
    if lat is None or lng is None:
        return jsonify({'message': 'latitude and longitude are required'}), 400

    result = BusLocationService.upsert_location(
        skid,
        request.current_user.school_user_id,
        lat, lng,
        heading=data.get('heading'),
        speed=data.get('speed'),
    )
    return jsonify({'message': 'Location updated', 'data': result}), 200


@bus_location_bp.route('/stop/<skid>', methods=['POST'])
@login_required(allowed_roles=['BUS_STAFF'])
def stop_tracking(skid):
    """Bus staff stops broadcasting."""
    result = BusLocationService.stop_tracking(skid, request.current_user.school_user_id)
    return jsonify(result), 200


@bus_location_bp.route('/live/<skid>/<int:bus_staff_user_id>', methods=['GET'])
@login_required(allowed_roles=['SCHOOL_ADMIN', 'PRINCIPAL', 'PARENT', 'BUS_STAFF'])
def get_live(skid, bus_staff_user_id):
    """Get last known position for a specific bus staff."""
    result = BusLocationService.get_live_location(skid, bus_staff_user_id)
    if not result:
        return jsonify({'message': 'No location data found'}), 404
    return jsonify({'data': result}), 200


@bus_location_bp.route('/my-child-bus/<skid>/<int:student_user_id>', methods=['GET'])
@login_required(allowed_roles=['PARENT'])
def get_child_bus(skid, student_user_id):
    """Parent endpoint: get the bus location for their child."""
    result = BusLocationService.get_child_bus_location(skid, student_user_id)
    return jsonify({'data': result}), 200
