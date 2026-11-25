"""
Holiday calendar: weekly off days (per academic year) and holidays (everyone / students only / staff only,
possibly tentative).

Off days are used by:
  - staff leave: weekly offs and staff holidays inside a leave aren't counted (leave_balance.chargeable_dates);
  - staff attendance: off days aren't "Not marked", and the register shows them;
  - student and staff attendance pages: a banner / calendar label on holidays (marking is still allowed).

When a holiday that applies to staff is added, moved, shortened or removed, approved staff leave overlapping
the old or new dates is recounted: fewer counted days drop unpaid days first; extra days are paid while the
balance lasts, the rest unpaid. Other leave isn't touched.
"""
import calendar as cal
from datetime import date, datetime, timedelta

from sqlalchemy import or_

from app.models.tenant.AcademicYear import AcademicYear
from app.models.tenant.Holiday import Holiday, CalendarSetting
from app.utils.db_manager import switch_to_institution_db
from app.utils.enrollment import current_year_id

AUDIENCES = ('ALL', 'STUDENTS', 'STAFF')
ALT_SATURDAYS = {'NONE': (), '2_4': (2, 4), '1_3': (1, 3)}
DEFAULT_SETTINGS = {'weekly_off_days': [6], 'alternate_saturdays': 'NONE'}
NAME_MAX, NOTE_MAX, MAX_RANGE_DAYS = 120, 255, 120
WEEKDAYS = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')


class CalendarError(ValueError):
    def __init__(self, message, code=400):
        super().__init__(message)
        self.code = code


def ensure_tables(session):
    bind = session.connection()
    Holiday.__table__.create(bind=bind, checkfirst=True)
    CalendarSetting.__table__.create(bind=bind, checkfirst=True)


def _parse_day(value, label):
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        raise CalendarError(f'{label} is not a valid date')


# ---------------------------------------------------------------- weekly offs

def _years(session):
    return session.query(AcademicYear).order_by(AcademicYear.start_date).all()


def _year_for(years, day):
    for y in years:
        if y.start_date <= day <= y.end_date:
            return y
    return None


def settings_for_year(session, year_id, years=None):
    """{'weekly_off_days': [...], 'alternate_saturdays': ..., 'inherited_from': name or None}"""
    ensure_tables(session)
    row = session.query(CalendarSetting).filter_by(academic_year_id=year_id).first() if year_id else None
    if row:
        return {'weekly_off_days': list(row.weekly_off_days or []), 'alternate_saturdays': row.alternate_saturdays or 'NONE',
                'inherited_from': None}
    years = years if years is not None else _years(session)
    year = next((y for y in years if y.id == year_id), None)
    if year:
        rows = {r.academic_year_id: r for r in session.query(CalendarSetting).all()}
        for y in reversed(years):
            if y.start_date < year.start_date and y.id in rows:
                r = rows[y.id]
                return {'weekly_off_days': list(r.weekly_off_days or []), 'alternate_saturdays': r.alternate_saturdays or 'NONE',
                        'inherited_from': y.year_name}
    return {**DEFAULT_SETTINGS, 'inherited_from': None}


def _weekly_off_label(day, settings):
    if day.weekday() in settings['weekly_off_days']:
        return f'Weekly off ({WEEKDAYS[day.weekday()]})'
    nth = (day.day - 1) // 7 + 1
    if day.weekday() == 5 and nth in ALT_SATURDAYS.get(settings['alternate_saturdays'], ()):
        return f"Weekly off ({ {1: '1st', 2: '2nd', 3: '3rd', 4: '4th'}[nth] } Saturday)"
    return None


def off_days(session, start, end, audience='ALL'):
    """
    {date: {'label', 'kind': 'HOLIDAY'|'WEEKLY_OFF', 'tentative', 'holiday_id'}} between start and end.
    audience STAFF / STUDENTS: holidays for everyone plus that group's; ALL: every holiday.
    A holiday wins over a weekly off on the same day.
    """
    ensure_tables(session)
    years = _years(session)
    settings_cache = {}
    out = {}
    day = start
    while day <= end:
        year = _year_for(years, day)
        key = year.id if year else None
        if key not in settings_cache:
            settings_cache[key] = settings_for_year(session, key, years) if key else DEFAULT_SETTINGS
        label = _weekly_off_label(day, settings_cache[key])
        if label:
            out[day] = {'label': label, 'kind': 'WEEKLY_OFF', 'tentative': False, 'holiday_id': None}
        day += timedelta(days=1)
    query = session.query(Holiday).filter(Holiday.start_date <= end, Holiday.end_date >= start)
    if audience in ('STAFF', 'STUDENTS'):
        query = query.filter(Holiday.applies_to.in_(('ALL', audience)))
    for h in query.order_by(Holiday.start_date).all():
        day = max(h.start_date, start)
        while day <= min(h.end_date, end):
            out[day] = {'label': h.name + (' (tentative)' if h.is_tentative else ''), 'kind': 'HOLIDAY',
                        'tentative': bool(h.is_tentative), 'holiday_id': h.id}
            day += timedelta(days=1)
    return out


def working_dates(session, start, end, audience='STAFF'):
    """Days from start to end that aren't weekly offs or holidays for the audience."""
    offs = off_days(session, start, end, audience)
    out, day = [], start
    while day <= end:
        if day not in offs:
            out.append(day)
        day += timedelta(days=1)
    return out


# ---------------------------------------------------------------- shaping

def _range_text(start, end):
    if start == end:
        return start.strftime('%a %d %b')
    return f"{start.strftime('%d %b')} - {end.strftime('%d %b')}"


def _shape(h):
    return {
        'id': h.id, 'name': h.name, 'start_date': h.start_date.isoformat(), 'end_date': h.end_date.isoformat(),
        'days': (h.end_date - h.start_date).days + 1, 'applies_to': h.applies_to, 'is_tentative': bool(h.is_tentative),
        'note': h.note, 'academic_year_id': h.academic_year_id,
    }


def _clean(data, existing=None):
    data = data or {}
    name = str(data.get('name', existing.name if existing else '') or '').strip()
    if not name:
        raise CalendarError('Give the holiday a name')
    if len(name) > NAME_MAX:
        raise CalendarError(f'The name can be at most {NAME_MAX} characters')
    start = _parse_day(data['start_date'], 'Start date') if 'start_date' in data else (existing.start_date if existing else None)
    if start is None:
        raise CalendarError('Choose the date')
    end_raw = data.get('end_date') if 'end_date' in data else (existing.end_date if existing else None)
    end = _parse_day(end_raw, 'End date') if isinstance(end_raw, str) and end_raw else (end_raw or start)
    if end < start:
        raise CalendarError('The end date is before the start date')
    if (end - start).days + 1 > MAX_RANGE_DAYS:
        raise CalendarError(f'One holiday can cover at most {MAX_RANGE_DAYS} days')
    applies_to = str(data.get('applies_to', existing.applies_to if existing else 'ALL') or 'ALL').upper()
    if applies_to not in AUDIENCES:
        raise CalendarError('Choose who the holiday is for: everyone, students or staff')
    tentative = bool(data.get('is_tentative', existing.is_tentative if existing else False))
    note = str(data.get('note', existing.note if existing else '') or '').strip() or None
    if note and len(note) > NOTE_MAX:
        raise CalendarError(f'The note can be at most {NOTE_MAX} characters')
    return {'name': name, 'start_date': start, 'end_date': end, 'applies_to': applies_to, 'is_tentative': tentative, 'note': note}


def _year_id_for(session, day):
    year = _year_for(_years(session), day)
    return year.id if year else current_year_id(session)


# ---------------------------------------------------------------- recount staff leave

def recount_staff_leave(session, ranges, holiday_name):
    """
    Approved staff leave overlapping any of the (start, end) ranges: recount its days and adjust the paid /
    unpaid split. Returns how many leave requests changed.
    """
    from app.models.tenant.LeaveRequest import LeaveRequest
    from app.services import leave_balance
    conds = [(LeaveRequest.from_date <= e) & (LeaveRequest.to_date >= s) for s, e in ranges]
    if not conds:
        return 0
    leaves = session.query(LeaveRequest).filter(
        LeaveRequest.applicant_type == 'STAFF', LeaveRequest.status == 'APPROVED', or_(*conds),
    ).order_by(LeaveRequest.from_date, LeaveRequest.id).all()
    changed = 0
    for leave in leaves:
        paid, unpaid = int(leave.paid_days or 0), int(leave.unpaid_days or 0)
        new_total = len(leave_balance.chargeable_dates(session, leave.from_date, leave.to_date))
        diff = new_total - (paid + unpaid)
        if diff == 0:
            continue
        if diff < 0:
            cut = min(unpaid, -diff)
            unpaid -= cut
            paid -= (-diff - cut)
        else:
            policy, _ = leave_balance.policy_for_year(session, leave.academic_year_id)
            quota = policy.get(leave.leave_type)
            if quota is None:
                paid += diff
            else:
                used_elsewhere = leave_balance.used_paid_days(session, leave.user_id, leave.academic_year_id,
                                                              leave.leave_type, exclude_id=leave.id)
                add = max(0, min(diff, quota - used_elsewhere - paid))
                paid += add
                unpaid += diff - add
        leave.paid_days, leave.unpaid_days = max(0, paid), max(0, unpaid)
        leave.recount_note = f'Recounted after the {holiday_name} holiday changed'
        changed += 1
    return changed


# ---------------------------------------------------------------- service

class CalendarService:

    @staticmethod
    def list_year(skid, user, year_id=None):
        with switch_to_institution_db(skid) as session:
            ensure_tables(session)
            year_id = int(year_id) if year_id else current_year_id(session)
            year = session.query(AcademicYear).filter_by(id=year_id).first() if year_id else None
            query = session.query(Holiday)
            if year:
                query = query.filter(Holiday.end_date >= year.start_date, Holiday.start_date <= year.end_date)
            role = user.role.value if hasattr(user.role, 'value') else str(user.role)
            if role in ('STUDENT', 'PARENT'):
                query = query.filter(Holiday.applies_to.in_(('ALL', 'STUDENTS')))
            holidays = query.order_by(Holiday.start_date).all()
            settings = settings_for_year(session, year_id)
            return {
                'academic_year_id': year_id, 'year_name': year.year_name if year else None,
                'year_start': year.start_date.isoformat() if year else None,
                'year_end': year.end_date.isoformat() if year else None,
                'settings': settings, 'holidays': [_shape(h) for h in holidays],
            }

    @staticmethod
    def create(skid, actor_id, data):
        with switch_to_institution_db(skid) as session:
            ensure_tables(session)
            clean = _clean(data)
            h = Holiday(**clean, academic_year_id=_year_id_for(session, clean['start_date']), created_by=actor_id, updated_by=actor_id)
            session.add(h)
            session.flush()
            recounted = recount_staff_leave(session, [(h.start_date, h.end_date)], h.name) if h.applies_to != 'STUDENTS' else 0
            session.commit()
            if (data or {}).get('notify'):
                from app.services import push_events
                push_events.holiday_announced(skid, session, h, 'added')
            return {'holiday': _shape(h), 'recounted_leave': recounted}

    @staticmethod
    def update(skid, actor_id, holiday_id, data):
        with switch_to_institution_db(skid) as session:
            ensure_tables(session)
            h = session.query(Holiday).filter_by(id=int(holiday_id)).first()
            if not h:
                raise CalendarError('Holiday not found', 404)
            before = (h.start_date, h.end_date, h.applies_to, bool(h.is_tentative))
            clean = _clean(data, existing=h)
            for k, v in clean.items():
                setattr(h, k, v)
            h.academic_year_id = _year_id_for(session, h.start_date)
            h.updated_by = actor_id
            session.flush()
            moved = (h.start_date, h.end_date) != before[:2]
            staff_before, staff_after = before[2] != 'STUDENTS', h.applies_to != 'STUDENTS'
            recounted = 0
            if moved or staff_before != staff_after:
                ranges = ([(before[0], before[1])] if staff_before else []) + ([(h.start_date, h.end_date)] if staff_after else [])
                recounted = recount_staff_leave(session, ranges, h.name)
            session.commit()
            if (data or {}).get('notify'):
                kind = 'moved' if moved else 'confirmed' if before[3] and not h.is_tentative else 'updated'
                from app.services import push_events
                push_events.holiday_announced(skid, session, h, kind)
            return {'holiday': _shape(h), 'recounted_leave': recounted}

    @staticmethod
    def delete(skid, holiday_id):
        with switch_to_institution_db(skid) as session:
            ensure_tables(session)
            h = session.query(Holiday).filter_by(id=int(holiday_id)).first()
            if not h:
                raise CalendarError('Holiday not found', 404)
            name, rng, staff = h.name, (h.start_date, h.end_date), h.applies_to != 'STUDENTS'
            session.delete(h)
            session.flush()
            recounted = recount_staff_leave(session, [rng], name) if staff else 0
            session.commit()
            return {'deleted': True, 'recounted_leave': recounted}

    @staticmethod
    def save_settings(skid, actor_id, data):
        data = data or {}
        days = data.get('weekly_off_days')
        if not isinstance(days, list) or any(not isinstance(d, int) or d < 0 or d > 6 for d in days):
            raise CalendarError('Weekly off days must be weekdays (0 = Monday ... 6 = Sunday)')
        days = sorted(set(days))
        if len(days) >= 7:
            raise CalendarError('At least one day of the week must be a working day')
        alt = str(data.get('alternate_saturdays') or 'NONE').upper()
        if alt not in ALT_SATURDAYS:
            raise CalendarError('Alternate Saturdays must be none, 2nd & 4th, or 1st & 3rd')
        if alt != 'NONE' and 5 in days:
            alt = 'NONE'  # every Saturday is already off
        with switch_to_institution_db(skid) as session:
            ensure_tables(session)
            year_id = current_year_id(session)
            if not year_id:
                raise CalendarError('There is no current academic year')
            year = session.query(AcademicYear).filter_by(id=year_id).first()
            row = session.query(CalendarSetting).filter_by(academic_year_id=year_id).first()
            if not row:
                row = CalendarSetting(academic_year_id=year_id)
                session.add(row)
            row.weekly_off_days, row.alternate_saturdays, row.updated_by = days, alt, actor_id
            session.flush()
            recounted = recount_staff_leave(session, [(year.start_date, year.end_date)], 'weekly off') if year else 0
            session.commit()
            return {'settings': settings_for_year(session, year_id), 'recounted_leave': recounted}

    @staticmethod
    def off_days(skid, user, start, end, audience):
        start, end = _parse_day(start, 'From'), _parse_day(end, 'To')
        if end < start or (end - start).days > 400:
            raise CalendarError('Choose a range of at most a year')
        role = user.role.value if hasattr(user.role, 'value') else str(user.role)
        audience = str(audience or '').upper()
        if role in ('STUDENT', 'PARENT') or audience not in AUDIENCES:
            audience = 'STUDENTS' if role in ('STUDENT', 'PARENT') else 'STAFF'
        with switch_to_institution_db(skid) as session:
            offs = off_days(session, start, end, audience)
            return [{'date': d.isoformat(), **v} for d, v in sorted(offs.items())]

    @staticmethod
    def tentative_soon(skid, days=3):
        with switch_to_institution_db(skid) as session:
            ensure_tables(session)
            today = date.today()
            rows = session.query(Holiday).filter(
                Holiday.is_tentative.is_(True), Holiday.start_date >= today,
                Holiday.start_date <= today + timedelta(days=days)).order_by(Holiday.start_date).all()
            return [_shape(h) for h in rows]


# ---------------------------------------------------------------- calendar events (the Calendar page)

def _role_of(user):
    return user.role.value if hasattr(user.role, 'value') else str(user.role)


def _exam_events(session, start, end, role, placements):
    """Students / parents: their class's exams, one per paper. Staff: one item per exam per day (n papers)."""
    from app.models.tenant.ExamModels import ExamTimetable, ExamType
    from app.models.tenant.Subject import Subject
    from app.models.tenant.Class import Class
    rows = (session.query(ExamTimetable, ExamType.exam_name, Subject.subject_name, Class.class_name)
            .join(ExamType, ExamType.id == ExamTimetable.exam_type_id)
            .join(Subject, Subject.id == ExamTimetable.subject_id)
            .join(Class, Class.id == ExamTimetable.class_id)
            .filter(ExamTimetable.exam_date >= start, ExamTimetable.exam_date <= end)
            .order_by(ExamTimetable.exam_date, ExamTimetable.start_time).all())
    out = []
    if role in ('STUDENT', 'PARENT'):
        for t, exam, subject, class_name in rows:
            for who, (class_id, section_id) in placements.items():
                if t.class_id == class_id and (t.section_id is None or t.section_id == section_id):
                    out.append({'type': 'EXAM', 'date_from': t.exam_date.isoformat(), 'date_to': t.exam_date.isoformat(),
                                'title': f'{exam}: {subject}' + (f' ({who})' if role == 'PARENT' and who else ''),
                                'time': f"{t.start_time.strftime('%H:%M')}-{t.end_time.strftime('%H:%M')}"})
        return out
    grouped = {}
    for t, exam, subject, class_name in rows:
        g = grouped.setdefault((t.exam_date, exam), {'papers': 0, 'classes': set()})
        g['papers'] += 1
        g['classes'].add(class_name)
    for (day, exam), g in grouped.items():
        out.append({'type': 'EXAM', 'date_from': day.isoformat(), 'date_to': day.isoformat(),
                    'title': f"{exam} ({g['papers']} paper{'s' if g['papers'] != 1 else ''})",
                    'detail': ', '.join(sorted(g['classes']))})
    return out


def _leave_events(session, user, role, start, end, child_ids):
    """Own leave (child's for parents), pending and approved; approvers also see who else is on approved leave."""
    from app.models.tenant.LeaveRequest import LeaveRequest
    from app.services.leave_service import has_full_approval, class_teacher_sections, _names, LEAVE_TYPES
    me = int(user.institution_user_id) if user.institution_user_id else None
    overlap = (LeaveRequest.from_date <= end) & (LeaveRequest.to_date >= start)
    own_ids = list(child_ids) if role == 'PARENT' else ([me] if me else [])
    rows = session.query(LeaveRequest).filter(overlap, LeaveRequest.user_id.in_(own_ids or [-1]),
                                              LeaveRequest.status.in_(('PENDING', 'APPROVED'))).all()
    others = []
    if role not in ('STUDENT', 'PARENT'):
        query = session.query(LeaveRequest).filter(overlap, LeaveRequest.status == 'APPROVED',
                                                   LeaveRequest.user_id != (me or -1))
        if has_full_approval(user):
            others = query.filter(LeaveRequest.applicant_type == 'STAFF').all()
        sections = class_teacher_sections(session, user)
        if sections:
            others += query.filter(LeaveRequest.applicant_type == 'STUDENT', LeaveRequest.section_id.in_(sections)).all()
    names = _names(session, [x.user_id for x in rows + others])
    out = []
    for x in rows:
        label = LEAVE_TYPES.get(x.applicant_type, {}).get(x.leave_type, x.leave_type.title())
        whose = (names.get(x.user_id, '').split(' ')[0] + ': ') if role == 'PARENT' else ''
        out.append({'type': 'LEAVE', 'id': x.id, 'date_from': x.from_date.isoformat(), 'date_to': x.to_date.isoformat(),
                    'title': f'{whose}{label} leave' + (' (pending)' if x.status == 'PENDING' else ''),
                    'status': x.status, 'mine': True})
    for x in others:
        out.append({'type': 'LEAVE', 'id': x.id, 'date_from': x.from_date.isoformat(), 'date_to': x.to_date.isoformat(),
                    'title': f"{names.get(x.user_id, 'Someone')} on leave", 'status': x.status, 'mine': False,
                    'detail': 'Staff' if x.applicant_type == 'STAFF' else 'Student'})
    return out


def _event_items(session, user, start, end, family_sections):
    from app.services import event_service as ev
    rows = ev.visible_events(session, user, start, end, family_sections)
    if not rows:
        return []
    labels = ev.section_labels(session, {s for e in rows for s in (e.section_ids or [])})
    full, mine = ev.can_manage_all(user), ev.own_sections(session, user)
    return [{'type': 'EVENT', **ev.shape(e, labels, user, full, mine), 'date_from': e.start_date.isoformat(),
             'date_to': e.end_date.isoformat()} for e in rows]


def calendar_events(skid, user, start, end, student_id=None):
    """Everything for the Calendar page between start and end, limited to what this person may see."""
    from app.models.tenant.StudentParent import StudentParent
    from app.utils.enrollment import current_enrollment
    from app.services.leave_service import _names
    start, end = _parse_day(start, 'From'), _parse_day(end, 'To')
    if end < start or (end - start).days > 62:
        raise CalendarError('Choose a range of at most two months')
    role = _role_of(user)
    family = role in ('STUDENT', 'PARENT')
    with switch_to_institution_db(skid) as session:
        ensure_tables(session)
        events = []
        holidays = session.query(Holiday).filter(Holiday.start_date <= end, Holiday.end_date >= start)
        if family:
            holidays = holidays.filter(Holiday.applies_to.in_(('ALL', 'STUDENTS')))
        for h in holidays.order_by(Holiday.start_date).all():
            events.append({'type': 'HOLIDAY', **_shape(h), 'date_from': h.start_date.isoformat(),
                           'date_to': h.end_date.isoformat(), 'title': h.name})
        for day, o in off_days(session, start, end, 'STUDENTS' if family else 'STAFF').items():
            if o['kind'] == 'WEEKLY_OFF':
                events.append({'type': 'WEEKLY_OFF', 'date_from': day.isoformat(), 'date_to': day.isoformat(), 'title': o['label']})

        child_ids, placements = [], {}
        me = int(user.institution_user_id) if user.institution_user_id else None

        def placement(student_id):
            """(class_id, section_id): this year's enrollment, else the student's profile placement."""
            from app.models.tenant.Student import Student
            e = current_enrollment(session, student_id)
            if e and e.class_id:
                return e.class_id, e.section_id
            st = session.query(Student).filter_by(user_id=int(student_id)).first()
            return (st.class_id, st.section_id) if st and st.class_id else None

        if role == 'STUDENT' and me:
            p = placement(me)
            if p:
                placements[None] = p
        elif role == 'PARENT' and me:
            child_ids = [r[0] for r in session.query(StudentParent.student_user_id).filter_by(parent_user_id=me).all()]
            if student_id:
                if int(student_id) not in child_ids:
                    raise CalendarError("You can only see your own child's calendar", 403)
                child_ids = [int(student_id)]
            first_names = {k: v.split(' ')[0] for k, v in _names(session, child_ids).items()}
            for cid in child_ids:
                p = placement(cid)
                if p:
                    placements[first_names.get(cid)] = p
        try:
            events += _exam_events(session, start, end, role, placements)
        except Exception:
            session.rollback()  # an institution without exam tables yet: no exams to show
        events += _leave_events(session, user, role, start, end, child_ids)
        events += _event_items(session, user, start, end, {p[1] for p in placements.values() if p and p[1]})
        return {'from': start.isoformat(), 'to': end.isoformat(), 'events': events}
