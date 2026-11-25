"""
Leave management: students (applied by the student or a parent) and staff apply; approvers decide.

Who decides:
  - student leave: the class teacher of the student's section, the Institution Admin, or anyone whose role has
    the "approve_leave" tick box;
  - staff leave: the Institution Admin or anyone with "approve_leave".
  Nobody decides their own request.
Approved student leave shows as "Leave" on Mark Attendance; a day already marked Absent becomes Leave, and no
absence notification goes out for a day on approved leave (push_events.students_marked_absent).
"""
from datetime import date, datetime, timedelta

from sqlalchemy import func, or_

from app.models.tenant.Class import Class
from app.models.tenant.InstitutionUsers import InstitutionUsers
from app.models.tenant.LeaveRequest import LeaveRequest
from app.models.tenant.Sections import Section
from app.models.tenant.Student import Student
from app.models.tenant.StudentParent import StudentParent
from app.utils.db_manager import switch_to_institution_db
from app.utils.enrollment import current_enrollment, current_year_id

STUDENT, STAFF = 'STUDENT', 'STAFF'
PENDING, APPROVED, REJECTED, CANCELLED = 'PENDING', 'APPROVED', 'REJECTED', 'CANCELLED'
LEAVE_TYPES = {
    STUDENT: {'SICK': 'Sick', 'FAMILY': 'Family', 'OTHER': 'Other'},
    STAFF: {'CASUAL': 'Casual', 'SICK': 'Sick', 'OTHER': 'Other'},
}
STAFF_APPLICANT_ROLES = ('PRINCIPAL', 'TEACHER', 'CLERK', 'BUS_STAFF')
APPROVE_PERMISSION = 'approve_leave'
DAYS_BACK = 7            # leave can be applied up to a week back (illness reported late)
MAX_DAYS = 60            # one request covers at most this many days
REASON_MAX = 1000


class LeaveError(ValueError):
    def __init__(self, message, code=400):
        super().__init__(message)
        self.code = code


def _role(user):
    return user.role.value if hasattr(user.role, 'value') else str(user.role)


def _parse_day(value, label):
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        raise LeaveError(f'{label} is not a valid date')


def ensure_table(session):
    LeaveRequest.__table__.create(bind=session.connection(), checkfirst=True)


# ---------------------------------------------------------------- who may decide

def has_full_approval(user):
    """Institution Admin, or a role with the "approve_leave" tick box: decides every request."""
    if _role(user) == 'INSTITUTION_ADMIN':
        return True
    from app.utils.role_permissions import user_permissions
    try:
        return APPROVE_PERMISSION in user_permissions(user)
    except Exception:
        return False


def class_teacher_sections(session, user):
    """Sections this user is the class teacher of."""
    if not user.institution_user_id:
        return set()
    return {r[0] for r in session.query(Section.id).filter(Section.teacher_id == int(user.institution_user_id)).all()}


def _student_section(session, student_id):
    enrollment = current_enrollment(session, student_id)
    if enrollment and enrollment.section_id:
        return enrollment.section_id
    student = session.query(Student).filter_by(user_id=int(student_id)).first()
    return student.section_id if student else None


def _can_decide(session, user, leave, full=None, my_sections=None):
    if user.institution_user_id and int(leave.user_id) == int(user.institution_user_id):
        return False  # never one's own leave
    if user.institution_user_id and int(leave.applied_by) == int(user.institution_user_id):
        return False
    full = has_full_approval(user) if full is None else full
    if full:
        return True
    if leave.applicant_type != STUDENT:
        return False
    sections = class_teacher_sections(session, user) if my_sections is None else my_sections
    return leave.section_id in sections or _student_section(session, leave.user_id) in sections


def can_review(session, user):
    """Does this user see the Leave requests page with anything on it?"""
    return has_full_approval(user) or bool(class_teacher_sections(session, user))


def approver_user_ids(session, leave):
    """institution_users ids to notify about a new request (never the applicant)."""
    from app.models.tenant.Roles import Role
    ids = set()
    if leave.applicant_type == STUDENT and leave.section_id:
        section = session.query(Section).filter_by(id=leave.section_id).first()
        if section and section.teacher_id:
            ids.add(section.teacher_id)
    if not ids:  # staff leave, or a section without a class teacher: the people who approve everything
        roles = session.query(Role).filter(Role.is_active.isnot(False)).all()
        role_ids = [r.id for r in roles
                    if (r.role_code == 'INSTITUTION_ADMIN') or APPROVE_PERMISSION in (r.permissions or [])]
        if role_ids:
            ids |= {r[0] for r in session.query(InstitutionUsers.id).filter(
                InstitutionUsers.role_id.in_(role_ids), InstitutionUsers.is_active.isnot(False)).all()}
    ids.discard(leave.user_id)
    ids.discard(leave.applied_by)
    return ids


# ---------------------------------------------------------------- shaping

def _names(session, ids):
    ids = {int(i) for i in ids if i is not None}
    if not ids:
        return {}
    rows = session.query(InstitutionUsers.id, InstitutionUsers.first_name, InstitutionUsers.last_name).filter(
        InstitutionUsers.id.in_(ids)).all()
    return {r[0]: f"{r[1] or ''} {r[2] or ''}".strip() for r in rows}


def _section_labels(session, section_ids):
    ids = {int(i) for i in section_ids if i is not None}
    if not ids:
        return {}
    rows = session.query(Section.id, Section.section_name, Class.class_name).join(
        Class, Class.id == Section.class_id).filter(Section.id.in_(ids)).all()
    return {r[0]: f"{r[2]} - {r[1]}" for r in rows}


def _iso_utc(value):
    return value.isoformat() + 'Z' if value else None


def _shape(session, leaves, user=None):
    leaves = list(leaves)
    names = _names(session, [x for l in leaves for x in (l.user_id, l.applied_by, l.decided_by)])
    sections = _section_labels(session, [l.section_id for l in leaves])
    full = has_full_approval(user) if user else False
    my_sections = class_teacher_sections(session, user) if user else set()
    me = int(user.institution_user_id) if user and user.institution_user_id else None
    today = date.today()
    out = []
    for l in leaves:
        out.append({
            'id': l.id,
            'applicant_type': l.applicant_type,
            'user_id': l.user_id,
            'name': names.get(l.user_id, ''),
            'applied_by': l.applied_by,
            'applied_by_name': names.get(l.applied_by, ''),
            'applied_by_self': l.applied_by == l.user_id,
            'section_id': l.section_id,
            'class_section': sections.get(l.section_id),
            'from_date': l.from_date.isoformat(),
            'to_date': l.to_date.isoformat(),
            'days': (l.to_date - l.from_date).days + 1,
            'leave_type': l.leave_type,
            'leave_type_label': LEAVE_TYPES.get(l.applicant_type, {}).get(l.leave_type, l.leave_type.title()),
            'reason': l.reason,
            'status': l.status,
            'decided_by_name': names.get(l.decided_by) if l.decided_by else None,
            'decided_at': _iso_utc(l.decided_at),
            'decision_note': l.decision_note,
            'created_at': _iso_utc(l.created_at),
            'can_decide': bool(user) and l.status == PENDING and _can_decide(session, user, l, full, my_sections),
            'can_cancel': me is not None and l.applied_by == me and _cancellable(l, today),
        })
    return out


def _cancellable(leave, today):
    return leave.status == PENDING or (leave.status == APPROVED and leave.from_date > today)


# ---------------------------------------------------------------- service

class LeaveService:

    @staticmethod
    def leave_types():
        return {k: [{'value': v, 'label': lbl} for v, lbl in types.items()] for k, types in LEAVE_TYPES.items()}

    @staticmethod
    def _resolve_person(session, user, student_id):
        """(applicant_type, user_id) the request is for, after checking the caller may apply for them."""
        role = _role(user)
        me = user.institution_user_id
        if not me:
            raise LeaveError('Only institution accounts can apply for leave', 403)
        if role == 'STUDENT':
            return STUDENT, int(me)
        if role == 'PARENT':
            if not student_id:
                raise LeaveError('Choose the child the leave is for')
            linked = session.query(StudentParent).filter_by(
                parent_user_id=int(me), student_user_id=int(student_id)).first()
            if not linked:
                raise LeaveError("You can only apply for your own child's leave", 403)
            return STUDENT, int(student_id)
        if role in STAFF_APPLICANT_ROLES:
            return STAFF, int(me)
        raise LeaveError('Your account type cannot apply for leave here', 403)

    @staticmethod
    def my_requests(skid, user, student_id=None):
        with switch_to_institution_db(skid) as session:
            ensure_table(session)
            applicant_type, person = LeaveService._resolve_person(session, user, student_id)
            leaves = session.query(LeaveRequest).filter(LeaveRequest.user_id == person).order_by(
                LeaveRequest.from_date.desc(), LeaveRequest.id.desc()).limit(200).all()
            return {'applicant_type': applicant_type, 'leave_types': LeaveService.leave_types()[applicant_type],
                    'days_back': DAYS_BACK, 'max_days': MAX_DAYS, 'requests': _shape(session, leaves, user)}

    @staticmethod
    def apply(skid, user, data):
        data = data or {}
        with switch_to_institution_db(skid) as session:
            ensure_table(session)
            applicant_type, person = LeaveService._resolve_person(session, user, data.get('student_id'))
            start = _parse_day(data.get('from_date'), 'From date')
            end = _parse_day(data.get('to_date') or data.get('from_date'), 'To date')
            today = date.today()
            if end < start:
                raise LeaveError('The end date is before the start date')
            if start < today - timedelta(days=DAYS_BACK):
                raise LeaveError(f'Leave can be applied at most {DAYS_BACK} days back')
            if (end - start).days + 1 > MAX_DAYS:
                raise LeaveError(f'One request can cover at most {MAX_DAYS} days')
            leave_type = str(data.get('leave_type') or '').strip().upper()
            if leave_type not in LEAVE_TYPES[applicant_type]:
                raise LeaveError('Choose a leave type')
            reason = str(data.get('reason') or '').strip()
            if not reason:
                raise LeaveError('Please give a reason')
            if len(reason) > REASON_MAX:
                raise LeaveError(f'The reason can be at most {REASON_MAX} characters')
            overlap = session.query(LeaveRequest).filter(
                LeaveRequest.user_id == person,
                LeaveRequest.status.in_([PENDING, APPROVED]),
                LeaveRequest.from_date <= end, LeaveRequest.to_date >= start,
            ).first()
            if overlap:
                raise LeaveError(
                    f"There is already a {overlap.status.lower()} leave request for "
                    f"{overlap.from_date.strftime('%d %b')} - {overlap.to_date.strftime('%d %b')} that overlaps these dates", 409)

            leave = LeaveRequest(
                applicant_type=applicant_type, user_id=person, applied_by=int(user.institution_user_id),
                section_id=_student_section(session, person) if applicant_type == STUDENT else None,
                academic_year_id=current_year_id(session),
                from_date=start, to_date=end, leave_type=leave_type, reason=reason, status=PENDING,
            )
            session.add(leave)
            session.commit()

            from app.services import push_events
            push_events.leave_requested(skid, session, leave)
            return _shape(session, [leave], user)[0]

    @staticmethod
    def cancel(skid, user, leave_id):
        with switch_to_institution_db(skid) as session:
            ensure_table(session)
            leave = session.query(LeaveRequest).filter_by(id=int(leave_id)).first()
            if not leave:
                raise LeaveError('Leave request not found', 404)
            if not user.institution_user_id or leave.applied_by != int(user.institution_user_id):
                raise LeaveError('Only the person who applied can cancel this request', 403)
            if not _cancellable(leave, date.today()):
                raise LeaveError('This request can no longer be cancelled')
            leave.status = CANCELLED
            session.commit()
            return _shape(session, [leave], user)[0]

    @staticmethod
    def review_list(skid, user, filters=None):
        """Requests this user can see as an approver: everything (full approval) or their class-teacher sections."""
        filters = filters or {}
        with switch_to_institution_db(skid) as session:
            ensure_table(session)
            full = has_full_approval(user)
            my_sections = class_teacher_sections(session, user)
            if not full and not my_sections:
                return {'can_review': False, 'full_access': False, 'requests': [], 'pending': 0}
            query = session.query(LeaveRequest)
            if not full:
                query = query.filter(LeaveRequest.applicant_type == STUDENT,
                                     LeaveRequest.section_id.in_(my_sections))
            if filters.get('applicant_type') in (STUDENT, STAFF):
                query = query.filter(LeaveRequest.applicant_type == filters['applicant_type'])
            if filters.get('section_id'):
                query = query.filter(LeaveRequest.section_id == int(filters['section_id']))
            pending = query.filter(LeaveRequest.status == PENDING).count()
            status = str(filters.get('status') or '').upper()
            if status in (PENDING, APPROVED, REJECTED, CANCELLED):
                query = query.filter(LeaveRequest.status == status)
            if filters.get('from_date'):
                query = query.filter(LeaveRequest.to_date >= _parse_day(filters['from_date'], 'From date'))
            if filters.get('to_date'):
                query = query.filter(LeaveRequest.from_date <= _parse_day(filters['to_date'], 'To date'))
            if filters.get('search'):
                like = f"%{str(filters['search']).strip().lower()}%"
                ids = [r[0] for r in session.query(InstitutionUsers.id).filter(or_(
                    func.lower(InstitutionUsers.first_name).like(like),
                    func.lower(InstitutionUsers.last_name).like(like),
                    func.lower(func.concat(InstitutionUsers.first_name, ' ', InstitutionUsers.last_name)).like(like),
                )).all()]
                query = query.filter(LeaveRequest.user_id.in_(ids or [-1]))
            leaves = query.order_by(
                (LeaveRequest.status == PENDING).desc(), LeaveRequest.from_date.desc(), LeaveRequest.id.desc()
            ).limit(300).all()
            return {'can_review': True, 'full_access': full, 'pending': pending,
                    'requests': _shape(session, leaves, user)}

    @staticmethod
    def pending_count(skid, user):
        with switch_to_institution_db(skid) as session:
            ensure_table(session)
            full = has_full_approval(user)
            my_sections = class_teacher_sections(session, user)
            if not full and not my_sections:
                return 0
            query = session.query(LeaveRequest).filter(LeaveRequest.status == PENDING)
            if not full:
                query = query.filter(LeaveRequest.applicant_type == STUDENT, LeaveRequest.section_id.in_(my_sections))
            me = user.institution_user_id
            if me:
                query = query.filter(LeaveRequest.user_id != int(me), LeaveRequest.applied_by != int(me))
            return query.count()

    @staticmethod
    def decide(skid, user, leave_id, decision, note=None):
        decision = str(decision or '').strip().upper()
        if decision not in ('APPROVE', 'REJECT'):
            raise LeaveError('Decision must be approve or reject')
        note = (str(note).strip() if note else '') or None
        if note and len(note) > REASON_MAX:
            raise LeaveError(f'The note can be at most {REASON_MAX} characters')
        with switch_to_institution_db(skid) as session:
            ensure_table(session)
            leave = session.query(LeaveRequest).filter_by(id=int(leave_id)).first()
            if not leave:
                raise LeaveError('Leave request not found', 404)
            if not _can_decide(session, user, leave):
                raise LeaveError("You can't decide this leave request", 403)
            if leave.status != PENDING:
                raise LeaveError(f'This request is already {leave.status.lower()}', 409)
            leave.status = APPROVED if decision == 'APPROVE' else REJECTED
            leave.decided_by = int(user.institution_user_id) if user.institution_user_id else None
            leave.decided_at = datetime.utcnow()
            leave.decision_note = note
            if leave.status == APPROVED and leave.applicant_type == STUDENT:
                _absent_to_leave(session, leave, leave.decided_by)
            session.commit()

            from app.services import push_events
            push_events.leave_decided(skid, session, leave)
            return _shape(session, [leave], user)[0]

    @staticmethod
    def students_on_leave(skid, section_id, day):
        """{student_id: leave_type_label} with approved leave on that day, in the section."""
        with switch_to_institution_db(skid) as session:
            ensure_table(session)
            from app.models.tenant.StudentEnrollment import StudentEnrollment
            in_section = {r[0] for r in session.query(StudentEnrollment.student_id).filter(
                StudentEnrollment.section_id == int(section_id)).all()}
            if not in_section:
                return {}
            on_leave = approved_student_leave(session, in_section, day)
            return {sid: LEAVE_TYPES[STUDENT].get(t, t.title()) for sid, t in on_leave.items()}


def approved_student_leave(session, student_ids, day):
    """{student_id: leave_type} for students with approved leave covering this day."""
    ids = [int(s) for s in (student_ids or []) if s is not None]
    if not ids:
        return {}
    try:
        rows = session.query(LeaveRequest.user_id, LeaveRequest.leave_type).filter(
            LeaveRequest.applicant_type == STUDENT, LeaveRequest.status == APPROVED,
            LeaveRequest.user_id.in_(ids), LeaveRequest.from_date <= day, LeaveRequest.to_date >= day,
        ).all()
    except Exception:  # table not there yet in an institution the start-up update couldn't reach
        session.rollback()
        return {}
    return {r[0]: r[1] for r in rows}


def _absent_to_leave(session, leave, actor_id):
    """Days of the leave already marked Absent become Leave (a day marked Present / Late stays as it is)."""
    from app.models.tenant.Attendance import Attendance
    records = session.query(Attendance).filter(
        Attendance.student_user_id == leave.user_id,
        Attendance.date >= leave.from_date, Attendance.date <= leave.to_date,
        func.upper(Attendance.status) == 'ABSENT',
    ).all()
    for record in records:
        record.status = 'LEAVE'
        record.remarks = (record.remarks or '').strip() or 'Approved leave'
        record.updated_by = actor_id
        record.updated_at = datetime.utcnow()
    return len(records)
