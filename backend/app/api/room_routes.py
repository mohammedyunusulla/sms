# app/api/room_routes.py
from flask import Blueprint, request, jsonify
from app.services.room_service import RoomService
from app.decorators import login_required

room_bp = Blueprint('rooms', __name__)

# CREATE ROOM
@room_bp.route('/create/room/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
def create_room(skid):
    try:
        data = request.get_json()

        if not skid:
            raise ValueError("School ID (skid) is required")

        # Validate required fields
        if not data.get('room_name'):
            raise ValueError("Room name is required")
        if not data.get('room_type'):
            raise ValueError("Room type is required")
        if not data.get('capacity'):
            raise ValueError("Capacity is required")

        new_room = RoomService.create_room(data, skid)
        return jsonify({
            'message': 'Room created successfully',
            'data': new_room,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to create room: {str(e)}', 'status': 'error', 'code': 500}), 500

# UPDATE ROOM
@room_bp.route('/update/room/<skid>/<int:room_id>', methods=['PUT'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
def update_room(skid, room_id):
    try:
        data = request.get_json()

        if not skid:
            raise ValueError("School ID (skid) is required")

        updated_room = RoomService.update_room(room_id, data, skid)
        return jsonify({
            'message': 'Room updated successfully',
            'data': updated_room,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to update room: {str(e)}', 'status': 'error', 'code': 500}), 500

# DELETE ROOM
@room_bp.route('/delete/room/<skid>/<int:room_id>', methods=['DELETE'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
def delete_room(skid, room_id):
    try:
        if not skid:
            raise ValueError("School ID (skid) is required")

        RoomService.delete_room(room_id, skid)
        return jsonify({
            'message': 'Room deleted successfully',
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to delete room: {str(e)}', 'status': 'error', 'code': 500}), 500

# LIST ALL ROOMS
@room_bp.route('/list/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'TEACHER'])
def get_all_rooms(skid):
    try:
        if not skid:
            raise ValueError("School ID (skid) is required")

        # Build filters from query params
        filters = {}
        if request.args.get('room_type'):
            filters['room_type'] = request.args.get('room_type')
        if request.args.get('building'):
            filters['building'] = request.args.get('building')
        if request.args.get('is_active') is not None:
            filters['is_active'] = request.args.get('is_active')

        rooms = RoomService.get_all_rooms(skid, filters if filters else None)
        return jsonify({
            'message': 'Rooms retrieved successfully',
            'data': rooms,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to retrieve rooms: {str(e)}', 'status': 'error', 'code': 500}), 500

# GET ROOM BY ID
@room_bp.route('/<int:room_id>/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'TEACHER'])
def get_room_by_id(room_id, skid):
    try:
        if not skid:
            raise ValueError("School ID (skid) is required")

        room = RoomService.get_room_by_id(room_id, skid)
        return jsonify({
            'message': 'Room retrieved successfully',
            'data': room,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to retrieve room: {str(e)}', 'status': 'error', 'code': 500}), 500

# GET AVAILABLE ROOMS
@room_bp.route('/available/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'TEACHER'])
def get_available_rooms(skid):
    try:
        if not skid:
            raise ValueError("School ID (skid) is required")

        room_type = request.args.get('room_type')
        rooms = RoomService.get_available_rooms(skid, room_type)
        return jsonify({
            'message': 'Available rooms retrieved successfully',
            'data': rooms,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to retrieve available rooms: {str(e)}', 'status': 'error', 'code': 500}), 500
