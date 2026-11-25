"""
Events (Annual Day, parent-teacher meetings, sports meets...): shown on the Calendar, optional push.

Who sees an event:
  - staff see every event (to know what's going on);
  - students / parents see events for everyone, for students & parents, and for their (child's) section.
Who manages events:
  - the Institution Admin and the "manage_events" tick box: any event;
  - class teachers: events for their own section(s) only, and only events they created.
"""
import re
from datetime import date, time

from app.models.tenant.Class import Class
from app.models.tenant.Event import Event
from app.models.tenant.Sections import Section
from app.utils.db_manager import switch_to_institution_db

TYPES = {'GENERAL': 'Event', 'PTM': 'Parent-teacher meeting', 'SPORTS': 'Sports', 'CULTURAL': 'Cultural',
         'MEETING': 'Meeting', 'OTHER': 'Other'}
AUDIENCES = {'ALL': 'Everyone', 'STAFF': 'All staff', 'STUDENTS': 'Students & parents', 'SECTIONS': 'Specific classes'}
MANAGE_PERMISSION = 'manage_events'
TITLE_MAX, LOCATION_MAX, DESCRIPTION_MAX, MAX_DAYS = 150, 150, 2000, 31
FAMILY = ('STUDENT', 'PARENT')


class EventError(ValueError):
    def __init__(self, message, code=400):
        super().__init__(message)
        self.code = code


def ensure_table(session):
    Event.__table__.create(bind=session.connection(), checkfirst=True)


def _role(user):
    return user.role.value if hasattr(user.role, 'value') else str(user.role)


def can_manage_all(user):
    if _role(user) == 'INSTITUTION_ADMIN':
        return True
    if _role(user) in FAMILY:
        return False
    from app.utils.role_permissions import user_permissions
    try:
        return MANAGE_PERMISSION in user_permissions(user)
    except Exception:
        return False


def own_sections(session, user):
    """Sections this user is the class teacher of."""
    if not user.institution_user_id or _role(user) in FAMILY:
        return set()
    return {r[0] for r in session.query(Section.id).filter(Section.teacher_id == int(user.institution_user_id)).all()}


def can_edit(user, event, full, sections):
    if full:
        return True
    return (event.audience == 'SECTIONS' and bool(event.section_ids) and set(event.section_ids) <= sections
            and event.created_by == user.institution_user_id)


def _natural(text):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', str(text or ''))]


def section_labels(session, ids=None):
    query = session.query(Section.id, Section.section_name, Class.class_name).join(Class, Class.id == Section.class_id)
    if ids is not None:
        query = query.filter(Section.id.in_(list(ids) or [-1]))
    return {r[0]: f'{r[2]} - {r[1]}' for r in query.order_by(Class.class_name, Section.section_name).all()}


def _parse_time(value, label):
    if value in (None, ''):
        return None
    try:
        return time.fromisoformat(str(value)[:5])
    except ValueError:
        raise EventError(f'{label} is not a valid time')


def _parse_day(value, label):
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        raise EventError(f'{label} is not a valid date')


def shape(event, labels=None, user=None, full=False, sections=frozenset()):
    names = [labels.get(s, '') for s in (event.section_ids or [])] if labels else []
    audience = AUDIENCES.get(event.audience, event.audience)
    if event.audience == 'SECTIONS' and names:
        audience = ', '.join(n for n in names if n) or audience
    t = ''
    if event.start_time:
        t = event.start_time.strftime('%H:%M') + (f"-{event.end_time.strftime('%H:%M')}" if event.end_time else '')
    return {
        'id': event.id, 'title': event.title, 'event_type': event.event_type, 'event_type_label': TYPES.get(event.event_type, 'Event'),
        'start_date': event.start_date.isoformat(), 'end_date': event.end_date.isoformat(),
        'start_time': event.start_time.strftime('%H:%M') if event.start_time else None,
        'end_time': event.end_time.strftime('%H:%M') if event.end_time else None,
        'time': t or None, 'location': event.location, 'description': event.description,
        'audience': event.audience, 'audience_label': audience, 'section_ids': event.section_ids or [],
        'status': event.status, 'can_edit': bool(user) and can_edit(user, event, full, sections),
    }


def visible_events(session, user, start, end, family_sections=None):
    """Events overlapping start..end this user may see (staff: all; family: everyone / students / their sections)."""
    ensure_table(session)
    rows = session.query(Event).filter(Event.start_date <= end, Event.end_date >= start).order_by(Event.start_date).all()
    if _role(user) in FAMILY:
        mine = set(family_sections or ())
        rows = [e for e in rows if e.audience in ('ALL', 'STUDENTS')
                or (e.audience == 'SECTIONS' and mine & set(e.section_ids or []))]
    return rows


class EventService:

    @staticmethod
    def options(skid, user):
        """What the event form offers this user: can they target everyone, and which sections."""
        with switch_to_institution_db(skid) as session:
            ensure_table(session)
            full = can_manage_all(user)
            sections = own_sections(session, user)
            query = session.query(Section.id, Section.section_name, Class.id, Class.class_name).join(Class, Class.id == Section.class_id)
            if not full:
                query = query.filter(Section.id.in_(list(sections) or [-1]))
            # natural order: Grade 6 ... Grade 10 (not Grade 10, Grade 6)
            rows = sorted(query.all(), key=lambda r: (_natural(r[3]), _natural(r[1])))
            return {
                'can_create': full or bool(sections), 'can_manage_all': full,
                'types': [{'value': k, 'label': v} for k, v in TYPES.items()],
                'audiences': [{'value': k, 'label': v} for k, v in AUDIENCES.items() if full or k == 'SECTIONS'],
                # the form picks a class first, then that class's sections
                'sections': [{'id': r[0], 'label': f'{r[3]} - {r[1]}', 'section_name': r[1], 'class_id': r[2], 'class_name': r[3]}
                             for r in rows],
            }

    @staticmethod
    def _clean(session, user, data, existing=None):
        data = data or {}
        full = can_manage_all(user)
        mine = own_sections(session, user)
        get = lambda k, d=None: data.get(k, getattr(existing, k, d) if existing else d)
        title = str(get('title', '') or '').strip()
        if not title:
            raise EventError('Give the event a title')
        if len(title) > TITLE_MAX:
            raise EventError(f'The title can be at most {TITLE_MAX} characters')
        event_type = str(get('event_type', 'GENERAL') or 'GENERAL').upper()
        if event_type not in TYPES:
            raise EventError('Choose an event type')
        start = _parse_day(data['start_date'], 'Start date') if 'start_date' in data else (existing.start_date if existing else None)
        if start is None:
            raise EventError('Choose the date')
        end_raw = data.get('end_date') if 'end_date' in data else (existing.end_date if existing else None)
        end = _parse_day(end_raw, 'End date') if isinstance(end_raw, str) and end_raw else (end_raw or start)
        if end < start:
            raise EventError('The end date is before the start date')
        if (end - start).days + 1 > MAX_DAYS:
            raise EventError(f'One event can cover at most {MAX_DAYS} days')
        st = _parse_time(data['start_time'], 'Start time') if 'start_time' in data else (existing.start_time if existing else None)
        et = _parse_time(data['end_time'], 'End time') if 'end_time' in data else (existing.end_time if existing else None)
        if et and not st:
            raise EventError('Add a start time, or leave both times empty for an all-day event')
        if st and et and start == end and et <= st:
            raise EventError('The end time is before the start time')
        location = str(get('location', '') or '').strip() or None
        if location and len(location) > LOCATION_MAX:
            raise EventError(f'The location can be at most {LOCATION_MAX} characters')
        description = str(get('description', '') or '').strip() or None
        if description and len(description) > DESCRIPTION_MAX:
            raise EventError(f'The details can be at most {DESCRIPTION_MAX} characters')
        audience = str(get('audience', 'ALL') or 'ALL').upper()
        if audience not in AUDIENCES:
            raise EventError('Choose who the event is for')
        section_ids = None
        if audience == 'SECTIONS':
            raw = data.get('section_ids') if 'section_ids' in data else (existing.section_ids if existing else None)
            try:
                section_ids = sorted({int(s) for s in (raw or [])})
            except (TypeError, ValueError):
                raise EventError('Choose the classes')
            if not section_ids:
                raise EventError('Choose at least one class / section')
            known = set(section_labels(session, section_ids))
            if set(section_ids) - known:
                raise EventError('Some of the chosen sections no longer exist')
        if not full:
            if audience != 'SECTIONS' or not set(section_ids or []) <= mine:
                raise EventError('You can only create events for your own class', 403)
        return {'title': title, 'event_type': event_type, 'start_date': start, 'end_date': end, 'start_time': st,
                'end_time': et, 'location': location, 'description': description, 'audience': audience,
                'section_ids': section_ids}

    @staticmethod
    def _get_editable(session, user, event_id):
        e = session.query(Event).filter_by(id=int(event_id)).first()
        if not e:
            raise EventError('Event not found', 404)
        if not can_edit(user, e, can_manage_all(user), own_sections(session, user)):
            raise EventError("You can't change this event", 403)
        return e

    @staticmethod
    def _result(session, user, e):
        full, mine = can_manage_all(user), own_sections(session, user)
        return shape(e, section_labels(session, e.section_ids or []), user, full, mine)

    @staticmethod
    def create(skid, user, data):
        from app.utils.enrollment import current_year_id
        with switch_to_institution_db(skid) as session:
            ensure_table(session)
            e = Event(**EventService._clean(session, user, data), status='ACTIVE', academic_year_id=current_year_id(session),
                      created_by=user.institution_user_id, updated_by=user.institution_user_id)
            session.add(e)
            session.commit()
            if (data or {}).get('notify'):
                from app.services import push_events
                push_events.event_announced(skid, session, e, 'added')
            return EventService._result(session, user, e)

    @staticmethod
    def update(skid, user, event_id, data):
        with switch_to_institution_db(skid) as session:
            ensure_table(session)
            e = EventService._get_editable(session, user, event_id)
            for k, v in EventService._clean(session, user, data, existing=e).items():
                setattr(e, k, v)
            if (data or {}).get('reinstate') and e.status == 'CANCELLED':
                e.status = 'ACTIVE'
            e.updated_by = user.institution_user_id
            session.commit()
            if (data or {}).get('notify'):
                from app.services import push_events
                push_events.event_announced(skid, session, e, 'updated')
            return EventService._result(session, user, e)

    @staticmethod
    def cancel(skid, user, event_id, notify=False):
        with switch_to_institution_db(skid) as session:
            ensure_table(session)
            e = EventService._get_editable(session, user, event_id)
            if e.status == 'CANCELLED':
                raise EventError('This event is already cancelled', 409)
            e.status, e.updated_by = 'CANCELLED', user.institution_user_id
            session.commit()
            if notify:
                from app.services import push_events
                push_events.event_announced(skid, session, e, 'cancelled')
            return EventService._result(session, user, e)

    @staticmethod
    def delete(skid, user, event_id):
        with switch_to_institution_db(skid) as session:
            ensure_table(session)
            e = EventService._get_editable(session, user, event_id)
            session.delete(e)
            session.commit()
            return {'deleted': True}


def event_recipients(session, skid, event):
    """Login accounts (main users.id) to notify about this event."""
    from app.services import push_service as push
    from app.services.push_events import STAFF_ROLES
    if event.audience == 'ALL':
        return push.main_user_ids_for(skid)
    if event.audience == 'STAFF':
        return push.main_user_ids_for(skid, roles=STAFF_ROLES)
    if event.audience == 'STUDENTS':
        return push.main_user_ids_for(skid, roles=('STUDENT', 'PARENT'))
    students = push.students_in_sections(session, event.section_ids or [])
    teachers = {r[0] for r in session.query(Section.teacher_id).filter(
        Section.id.in_(event.section_ids or [-1]), Section.teacher_id.isnot(None)).all()}
    return push.main_user_ids_for(skid, students | push.parents_of(session, students) | teachers)
