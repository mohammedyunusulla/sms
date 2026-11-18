# ============================================================
# app/services/room_service.py
from app import db
from app.models.tenant import Room
from app.utils.db_manager import switch_to_school_db


class RoomService:

    @staticmethod
    def create_room(data, skid):
        """
        Create a new room in tenant database
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Check if room name already exists
                existing_room = tenant_session.query(Room).filter_by(
                    room_name=data['room_name']
                ).first()

                if existing_room:
                    raise ValueError(f"Room '{data['room_name']}' already exists")

                # Create new room with all fields
                new_room = Room(
                    room_name=data['room_name'],
                    room_type=data['room_type'],
                    building=data.get('building'),
                    floor=data.get('floor'),
                    seating_layout=data.get('seating_layout'),
                    capacity=data['capacity'],
                    has_projector=data.get('has_projector', False),
                    has_ac=data.get('has_ac', False),
                    has_computers=data.get('has_computers', False),
                    is_active=data.get('is_active', True),
                    notes=data.get('notes'),
                )

                tenant_session.add(new_room)
                tenant_session.commit()
                tenant_session.refresh(new_room)
                return new_room.to_dict()

        except Exception as e:
            raise Exception(f"Failed to create room: {str(e)}")

    @staticmethod
    def update_room(room_id, data, skid):
        """
        Update an existing room in tenant database
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                room = tenant_session.query(Room).filter_by(id=room_id).first()

                if not room:
                    raise ValueError("Room not found")

                # Check if room name already exists (only if being changed)
                if data.get('room_name') and data['room_name'] != room.room_name:
                    existing_room = tenant_session.query(Room).filter(
                        Room.room_name == data['room_name'],
                        Room.id != room_id
                    ).first()

                    if existing_room:
                        raise ValueError(f"Room '{data['room_name']}' already exists")

                # Update room fields
                room.room_name = data.get('room_name', room.room_name)
                room.room_type = data.get('room_type', room.room_type)
                room.building = data.get('building', room.building)
                room.floor = data.get('floor', room.floor)
                if 'seating_layout' in data:
                    room.seating_layout = data['seating_layout']
                room.capacity = data.get('capacity', room.capacity)
                room.has_projector = data.get('has_projector', room.has_projector)
                room.has_ac = data.get('has_ac', room.has_ac)
                room.has_computers = data.get('has_computers', room.has_computers)
                room.is_active = data.get('is_active', room.is_active)
                room.notes = data.get('notes', room.notes)

                tenant_session.commit()
                tenant_session.refresh(room)

                return room.to_dict()

        except Exception as e:
            raise Exception(f"Failed to update room: {str(e)}")

    @staticmethod
    def delete_room(room_id, skid):
        """
        Delete a room from tenant database
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                room = tenant_session.query(Room).filter_by(id=room_id).first()

                if not room:
                    raise ValueError("Room not found")

                tenant_session.delete(room)
                tenant_session.commit()

                return True

        except Exception as e:
            raise Exception(f"Failed to delete room: {str(e)}")

    @staticmethod
    def get_room_by_id(room_id, skid):
        """
        Get a specific room by ID
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                room = tenant_session.query(Room).filter_by(id=room_id).first()

                if not room:
                    raise ValueError("Room not found")

                return room.to_dict()

        except Exception as e:
            raise Exception(f"Failed to retrieve room: {str(e)}")

    @staticmethod
    def get_all_rooms(skid, filters=None):
        """
        Get all rooms with optional filters
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                query = tenant_session.query(Room)

                if filters:
                    if filters.get('room_type'):
                        query = query.filter(Room.room_type == filters['room_type'])
                    if filters.get('building'):
                        query = query.filter(Room.building == filters['building'])
                    if filters.get('is_active') is not None:
                        is_active = filters['is_active']
                        if isinstance(is_active, str):
                            is_active = is_active.lower() == 'true'
                        query = query.filter(Room.is_active == is_active)

                rooms = query.order_by(Room.building, Room.floor, Room.room_name).all()
                return [room.to_dict() for room in rooms]

        except Exception as e:
            raise Exception(f"Failed to retrieve rooms: {str(e)}")

    @staticmethod
    def get_available_rooms(skid, room_type=None):
        """
        Get rooms where is_active=True and status='available'
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                query = tenant_session.query(Room).filter(
                    Room.is_active == True
                )

                if room_type:
                    query = query.filter(Room.room_type == room_type)

                rooms = query.order_by(Room.building, Room.floor, Room.room_name).all()
                return [room.to_dict() for room in rooms]

        except Exception as e:
            raise Exception(f"Failed to retrieve available rooms: {str(e)}")
