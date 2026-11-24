import json
from datetime import datetime, date, timezone, timedelta
from sqlalchemy import func, cast, Date, or_
from app.models.tenant.BusScan import BusScan, BusScanType
from app.models.tenant.InstitutionUsers import InstitutionUsers
from app.models.tenant.Student import Student
from app.models.tenant.Roles import Role
from app.utils.db_manager import switch_to_institution_db


def _enrich_records(session, records):
    """Add student_name and staff_name to a list of BusScan dicts."""
    # Collect all user IDs we need names for
    student_ids = {r['student_user_id'] for r in records if r.get('student_user_id')}
    staff_ids = {r['scanned_by_user_id'] for r in records if r.get('scanned_by_user_id')}
    all_ids = student_ids | staff_ids

    if not all_ids:
        for r in records:
            r['student_name'] = None
            r['staff_name'] = None
        return records

    users = session.query(InstitutionUsers).filter(InstitutionUsers.id.in_(all_ids)).all()
    name_map = {u.id: u.full_name for u in users}

    for r in records:
        r['student_name'] = name_map.get(r.get('student_user_id'))
        r['staff_name'] = name_map.get(r.get('scanned_by_user_id'))
    return records


class BusScanService:

    @staticmethod
    def record_scan(skid, data):
        """
        Record a bus check-in or check-out scan.

        Expected data keys:
            student_user_id  (int)  – institution_users.id of the student
            scan_type        (str)  – 'CHECK_IN' or 'CHECK_OUT'
            scanned_by       (int)  – institution_users.id of bus staff
            academic_year_id (int, optional)
            location         (str, optional)
        """
        with switch_to_institution_db(skid) as session:
            try:
                student_id = int(data['student_user_id'])
            except (TypeError, ValueError):
                raise ValueError("Invalid student")
            # Only active students can be scanned (a teacher's or anyone else's id used to be accepted)
            student = (
                session.query(Student, InstitutionUsers)
                .join(InstitutionUsers, InstitutionUsers.id == Student.user_id)
                .filter(Student.user_id == student_id)
                .first()
            )
            if not student or not student[1].is_active:
                raise ValueError("This isn't an active student of this institution")

            # Check-ins and check-outs must alternate (a student could be checked out twice)
            now = datetime.now(timezone(timedelta(hours=5, minutes=30))).replace(tzinfo=None)
            last = (
                session.query(BusScan)
                .filter(BusScan.student_user_id == student_id, cast(BusScan.scanned_at, Date) == now.date())
                .order_by(BusScan.scanned_at.desc(), BusScan.id.desc())
                .first()
            )
            last_type = last.scan_type.value if last and hasattr(last.scan_type, 'value') else (last.scan_type if last else None)
            name = student[1].full_name
            if data['scan_type'] == 'CHECK_IN' and last_type == 'CHECK_IN':
                raise ValueError(f"{name} is already on the bus (checked in at {last.scanned_at.strftime('%H:%M')})")
            if data['scan_type'] == 'CHECK_OUT' and last_type != 'CHECK_IN':
                raise ValueError(f"{name} hasn't boarded the bus" + (" since the last check-out" if last_type == 'CHECK_OUT' else " today"))

            record = BusScan(
                student_user_id=student_id,
                scan_type=BusScanType(data['scan_type']),
                scanned_by_user_id=data.get('scanned_by'),
                academic_year_id=data.get('academic_year_id'),
                location=data.get('location'),
                scanned_at=now,
            )
            session.add(record)
            session.commit()
            return record.to_dict()

    @staticmethod
    def get_today_records(skid, academic_year_id=None, for_date=None):
        """Return all bus scan records for a given date (defaults to today), enriched with student and staff names."""
        target_date = for_date if for_date else date.today()
        with switch_to_institution_db(skid) as session:
            query = session.query(BusScan).filter(
                cast(BusScan.scanned_at, Date) == target_date
            )
            if academic_year_id:
                query = query.filter(BusScan.academic_year_id == academic_year_id)
            records = [r.to_dict() for r in query.order_by(BusScan.scanned_at.desc()).all()]
            return _enrich_records(session, records)

    @staticmethod
    def get_student_history(skid, student_user_id, limit=50):
        """Return recent bus scan history for a specific student."""
        with switch_to_institution_db(skid) as session:
            rows = (
                session.query(BusScan)
                .filter(BusScan.student_user_id == student_user_id)
                .order_by(BusScan.scanned_at.desc())
                .limit(limit)
                .all()
            )
            records = [r.to_dict() for r in rows]
            return _enrich_records(session, records)

    @staticmethod
    def get_current_bus_status(skid, academic_year_id=None):
        """
        For each student, return their last scan today (CHECK_IN or CHECK_OUT),
        enriched with student and staff names.
        """
        today = date.today()
        with switch_to_institution_db(skid) as session:
            subq = (
                session.query(
                    BusScan.student_user_id,
                    func.max(BusScan.scanned_at).label('latest')
                )
                .filter(cast(BusScan.scanned_at, Date) == today)
            )
            if academic_year_id:
                subq = subq.filter(BusScan.academic_year_id == academic_year_id)
            subq = subq.group_by(BusScan.student_user_id).subquery()

            rows = (
                session.query(BusScan)
                .join(subq, (BusScan.student_user_id == subq.c.student_user_id) &
                      (BusScan.scanned_at == subq.c.latest))
                .all()
            )
            records = [r.to_dict() for r in rows]
            return _enrich_records(session, records)

    @staticmethod
    def lookup_student_by_qr(skid, qr_data):
        """
        Resolve QR code payload to a student_user_id.
        QR payload JSON: {"student_id": <institution_users.id>, "institution": "<skid>"}
        Returns student_user_id (int) or raises ValueError.
        """
        try:
            payload = json.loads(qr_data)
        except (json.JSONDecodeError, TypeError):
            raise ValueError("Invalid QR code: this isn't a student card")
        if not isinstance(payload, dict):
            raise ValueError("Invalid QR code: this isn't a student card")

        if payload.get('institution') != skid:
            raise ValueError("This QR code belongs to another institution")

        student_id = payload.get('student_id')
        if not student_id:
            raise ValueError("Invalid QR code: no student on it")
        try:
            return int(student_id)
        except (TypeError, ValueError):
            raise ValueError("Invalid QR code: no student on it")


def search_students_for_bus(skid, query):
    """
    Search active students by name, roll number, or admission number.
    Returns list of { id, full_name, roll_no, admission_number } for the manual scan UI.
    """
    q = f"%{query}%"
    with switch_to_institution_db(skid) as session:
        rows = (
            session.query(InstitutionUsers, Student.roll_no, Student.admission_number)
            .outerjoin(Student, Student.user_id == InstitutionUsers.id)
            .join(Role, Role.id == InstitutionUsers.role_id)
            .filter(
                InstitutionUsers.is_active == True,
                Role.role_code == 'STUDENT',
                or_(
                    InstitutionUsers.first_name.ilike(q),
                    InstitutionUsers.last_name.ilike(q),
                    func.concat(InstitutionUsers.first_name, ' ', InstitutionUsers.last_name).ilike(q),
                    Student.roll_no.ilike(q),
                    Student.admission_number.ilike(q),
                )
            )
            .limit(10)
            .all()
        )
        return [
            {
                'id': su.id,
                'full_name': su.full_name,
                'roll_no': roll or '',
                'admission_number': adm or '',
            }
            for su, roll, adm in rows
        ]
