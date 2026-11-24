from datetime import datetime, date, timezone, timedelta
from sqlalchemy import cast, Date
from app.models.tenant.BusLocation import BusLocation
from app.models.tenant.BusScan import BusScan
from app.models.tenant.InstitutionUsers import InstitutionUsers
from app.utils.db_manager import switch_to_institution_db

IST = timezone(timedelta(hours=5, minutes=30))


def _ist_now():
    return datetime.now(IST).replace(tzinfo=None)


class BusLocationService:

    @staticmethod
    def upsert_location(skid, bus_staff_user_id, lat, lng, heading=None, speed=None):
        """Insert or update the single location row for a bus staff member."""
        with switch_to_institution_db(skid) as session:
            row = session.query(BusLocation).filter_by(
                bus_staff_user_id=bus_staff_user_id
            ).first()

            if row:
                row.latitude = lat
                row.longitude = lng
                row.heading = heading
                row.speed = speed
                row.is_active = True
                row.updated_at = _ist_now()
            else:
                row = BusLocation(
                    bus_staff_user_id=bus_staff_user_id,
                    latitude=lat,
                    longitude=lng,
                    heading=heading,
                    speed=speed,
                    is_active=True,
                    updated_at=_ist_now(),
                )
                session.add(row)

            session.flush()
            return {
                'bus_staff_user_id': row.bus_staff_user_id,
                'latitude': row.latitude,
                'longitude': row.longitude,
                'heading': row.heading,
                'speed': row.speed,
                'is_active': row.is_active,
                'updated_at': row.updated_at.isoformat() if row.updated_at else None,
            }

    @staticmethod
    def stop_tracking(skid, bus_staff_user_id):
        """Mark a bus staff as no longer broadcasting."""
        with switch_to_institution_db(skid) as session:
            row = session.query(BusLocation).filter_by(
                bus_staff_user_id=bus_staff_user_id
            ).first()
            if row:
                row.is_active = False
                row.updated_at = _ist_now()
        return {'status': 'stopped'}

    @staticmethod
    def get_live_location(skid, bus_staff_user_id):
        """Get the last known location for a bus staff member."""
        with switch_to_institution_db(skid) as session:
            row = session.query(BusLocation).filter_by(
                bus_staff_user_id=bus_staff_user_id
            ).first()
            if not row:
                return None

            staff = session.query(InstitutionUsers).filter_by(id=bus_staff_user_id).first()
            return {
                'bus_staff_user_id': row.bus_staff_user_id,
                'staff_name': staff.full_name if staff else None,
                'latitude': row.latitude,
                'longitude': row.longitude,
                'heading': row.heading,
                'speed': row.speed,
                'is_active': row.is_active,
                'updated_at': row.updated_at.isoformat() if row.updated_at else None,
            }

    @staticmethod
    def get_child_bus_location(skid, student_user_id):
        """
        Find which bus staff scanned this student today,
        then return that staff's live location.
        """
        today = date.today()
        with switch_to_institution_db(skid) as session:
            # Find today's most recent scan for this student
            scan = (
                session.query(BusScan)
                .filter(
                    BusScan.student_user_id == student_user_id,
                    cast(BusScan.scanned_at, Date) == today,
                )
                .order_by(BusScan.scanned_at.desc())
                .first()
            )

            if not scan or not scan.scanned_by_user_id:
                return {'is_active': False, 'message': 'No bus scan recorded for today'}

            bus_staff_id = scan.scanned_by_user_id

            row = session.query(BusLocation).filter_by(
                bus_staff_user_id=bus_staff_id,
                is_active=True,
            ).first()

            staff = session.query(InstitutionUsers).filter_by(id=bus_staff_id).first()

            if not row:
                return {
                    'is_active': False,
                    'bus_staff_user_id': bus_staff_id,
                    'staff_name': staff.full_name if staff else None,
                    'message': 'Bus is not currently sharing location',
                }

            return {
                'is_active': True,
                'bus_staff_user_id': row.bus_staff_user_id,
                'staff_name': staff.full_name if staff else None,
                'latitude': row.latitude,
                'longitude': row.longitude,
                'heading': row.heading,
                'speed': row.speed,
                'updated_at': row.updated_at.isoformat() if row.updated_at else None,
            }
