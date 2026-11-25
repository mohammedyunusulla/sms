"""
Substitute teacher planner.

Periods needing cover on a date come from the live timetables (published, this year's, latest per section)
for that weekday, for teachers who are:
  - on approved staff leave that day (LEAVE),
  - marked Absent / Leave in staff attendance (ABSENT / LEAVE),
  - marked Half day (HALF_DAY: listed as "may need cover", the admin chooses),
  - or added by hand (MANUAL, e.g. exam duty).
Weekly offs and staff holidays need no cover.

Suggestions for a period: teachers who are present, have no class overlapping that time and aren't already
covering one; ranked by same subject, already teaching that section, then fewest covers that day.
Arranged by the Institution Admin or anyone with "manage_timetable".
"""
from datetime import date

from app.models.tenant.Class import Class
from app.models.tenant.InstitutionUsers import InstitutionUsers
from app.models.tenant.Sections import Section
from app.models.tenant.Subject import Subject
from app.models.tenant.Substitution import Substitution
from app.models.tenant.Teacher import Teacher
from app.models.tenant.TimeTable import Timetable
from app.models.tenant.TimeTableEntry import TimetableEntry
from app.utils.db_manager import switch_to_institution_db

REASON_LABEL = {'LEAVE': 'On leave', 'ABSENT': 'Absent', 'HALF_DAY': 'Half day', 'MANUAL': 'Busy'}
NOTE_MAX = 255


class SubstitutionError(ValueError):
    def __init__(self, message, code=400):
        super().__init__(message)
        self.code = code


def ensure_table(session):
    Substitution.__table__.create(bind=session.connection(), checkfirst=True)


def _parse_day(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        raise SubstitutionError('Choose a valid date')


def _names(session, ids):
    ids = {int(i) for i in ids if i}
    if not ids:
        return {}
    return {r[0]: f'{r[1] or ""} {r[2] or ""}'.strip() for r in session.query(
        InstitutionUsers.id, InstitutionUsers.first_name, InstitutionUsers.last_name).filter(InstitutionUsers.id.in_(ids)).all()}


def _day_entries(session, day):
    """Live timetable periods on that weekday: [(entry, class_name, section_name, section_id, subject_name)]."""
    from app.services.timeTable_service import live_timetable_ids
    live = live_timetable_ids(session, day)
    if not live:
        return []
    return (session.query(TimetableEntry, Class.class_name, Section.section_name, Section.id, Subject.subject_name)
            .join(Timetable, Timetable.id == TimetableEntry.timetable_id)
            .join(Class, Class.id == Timetable.class_id)
            .join(Section, Section.id == Timetable.section_id)
            .join(Subject, Subject.id == TimetableEntry.subject_id)
            .filter(Timetable.id.in_(live), TimetableEntry.day_of_week == day.strftime('%A'),
                    TimetableEntry.is_active.is_(True))
            .order_by(TimetableEntry.start_time, Class.class_name, Section.section_name).all())


def absent_teachers(session, day):
    """{teacher_id: reason} for the day: approved leave, or staff attendance Absent / Leave / Half day."""
    from app.models.tenant.LeaveRequest import LeaveRequest
    from app.models.tenant.StaffAttendance import StaffAttendance
    out = {}
    for (uid,) in session.query(LeaveRequest.user_id).filter(
            LeaveRequest.applicant_type == 'STAFF', LeaveRequest.status == 'APPROVED',
            LeaveRequest.from_date <= day, LeaveRequest.to_date >= day).all():
        out[uid] = 'LEAVE'
    try:
        for uid, status in session.query(StaffAttendance.user_id, StaffAttendance.status).filter(StaffAttendance.date == day).all():
            if status in ('ABSENT', 'LEAVE'):
                out[uid] = out.get(uid) or ('ABSENT' if status == 'ABSENT' else 'LEAVE')
            elif status == 'HALF_DAY' and uid not in out:
                out[uid] = 'HALF_DAY'
            elif status in ('PRESENT', 'LATE') and out.get(uid) == 'LEAVE':
                out.pop(uid)  # came in after all
    except Exception:
        session.rollback()
    return out


def _overlaps(a_start, a_end, b_start, b_end):
    return a_start < b_end and b_start < a_end


def _off_day(session, day):
    from app.services.calendar_service import off_days
    return off_days(session, day, day, 'STAFF').get(day)


class SubstitutionService:

    @staticmethod
    def _context(session, day):
        rows = _day_entries(session, day)
        subs = {s.timetable_entry_id: s for s in session.query(Substitution).filter(Substitution.date == day).all()}
        absent = absent_teachers(session, day)
        return rows, subs, absent

    @staticmethod
    def _busy(rows, subs, teacher_id, start, end, skip_entry=None):
        """Is the teacher teaching or covering anything overlapping start..end?"""
        for entry, *_ in rows:
            if entry.id == skip_entry:
                continue
            sub = subs.get(entry.id)
            own_covered = sub and sub.substitute_teacher_id and entry.teacher_id == teacher_id
            if entry.teacher_id == teacher_id and not own_covered and _overlaps(entry.start_time, entry.end_time, start, end):
                return True
            if sub and sub.substitute_teacher_id == teacher_id and _overlaps(entry.start_time, entry.end_time, start, end):
                return True
        return False

    @staticmethod
    def _suggest(session, rows, subs, absent, entry, section_id, teachers, subjects_by_teacher, sections_by_teacher, names):
        covers_today = {}
        for s in subs.values():
            if s.substitute_teacher_id:
                covers_today[s.substitute_teacher_id] = covers_today.get(s.substitute_teacher_id, 0) + 1
        out = []
        for tid in teachers:
            if tid == entry.teacher_id or tid in absent:
                continue
            if SubstitutionService._busy(rows, subs, tid, entry.start_time, entry.end_time, skip_entry=entry.id):
                continue
            same_subject = entry.subject_id in subjects_by_teacher.get(tid, set())
            same_class = section_id in sections_by_teacher.get(tid, set())
            n = covers_today.get(tid, 0)
            tags = (['Same subject'] if same_subject else []) + (['Teaches this class'] if same_class else []) + \
                   ([f'{n} cover{"s" if n != 1 else ""} today'] if n else [])
            out.append({'teacher_id': tid, 'name': names.get(tid, ''), 'tags': tags,
                        '_rank': (-int(same_subject), -int(same_class), n, names.get(tid, ''))})
        out.sort(key=lambda x: x['_rank'])
        for x in out:
            x.pop('_rank')
        return out

    @staticmethod
    def day(skid, day):
        day = _parse_day(day)
        with switch_to_institution_db(skid) as session:
            ensure_table(session)
            off = _off_day(session, day)
            if off:
                return {'date': day.isoformat(), 'off_day': off, 'periods': [], 'needed': 0, 'covered': 0, 'teachers': []}
            rows, subs, absent = SubstitutionService._context(session, day)
            teachers = [r[0] for r in session.query(Teacher.user_id).join(InstitutionUsers, InstitutionUsers.id == Teacher.user_id)
                        .filter(InstitutionUsers.is_active.isnot(False)).all()]
            subjects_by_teacher, sections_by_teacher = {}, {}
            # whole-week view of who teaches what (for "same subject" / "teaches this class")
            from app.services.timeTable_service import live_timetable_ids
            live = live_timetable_ids(session, day)
            if live:
                for tid, subject_id, section_id in (session.query(TimetableEntry.teacher_id, TimetableEntry.subject_id, Timetable.section_id)
                                                    .join(Timetable, Timetable.id == TimetableEntry.timetable_id)
                                                    .filter(Timetable.id.in_(live), TimetableEntry.is_active.is_(True)).distinct().all()):
                    subjects_by_teacher.setdefault(tid, set()).add(subject_id)
                    sections_by_teacher.setdefault(tid, set()).add(section_id)
            names = _names(session, set(teachers) | set(absent) | {e.teacher_id for e, *_ in rows}
                           | {s.substitute_teacher_id for s in subs.values()})
            periods = []
            for (entry, class_name, section_name, section_id, subject_name) in rows:
                sub = subs.get(entry.id)
                reason = absent.get(entry.teacher_id)
                if not reason and not sub:
                    continue
                teacher_back = bool(sub and sub.reason != 'MANUAL' and not reason)
                row = {
                    'entry_id': entry.id, 'period_number': entry.period_number,
                    'start_time': entry.start_time.strftime('%H:%M'), 'end_time': entry.end_time.strftime('%H:%M'),
                    'class_section': f'{class_name} - {section_name}', 'subject_name': subject_name,
                    'teacher_id': entry.teacher_id, 'teacher_name': names.get(entry.teacher_id, ''),
                    'reason': (sub.reason if sub and sub.reason == 'MANUAL' else reason) or (sub.reason if sub else None),
                    'optional': reason == 'HALF_DAY' and not sub,
                    'teacher_back': teacher_back,
                    'substitute_id': sub.substitute_teacher_id if sub else None,
                    'substitute_name': names.get(sub.substitute_teacher_id) if sub and sub.substitute_teacher_id else None,
                    'note': sub.note if sub else None,
                }
                row['reason_label'] = REASON_LABEL.get(row['reason'], '')
                row['suggestions'] = SubstitutionService._suggest(session, rows, subs, absent, entry, section_id, teachers,
                                                                  subjects_by_teacher, sections_by_teacher, names)
                periods.append(row)
            needed = [p for p in periods if not p['optional'] and not p['teacher_back']]
            return {
                'date': day.isoformat(), 'off_day': None, 'periods': periods,
                'needed': len(needed), 'covered': sum(1 for p in needed if p['substitute_id']),
                # for "Add cover by hand": teachers with periods that day
                'teachers': sorted([{'id': t, 'name': names.get(t, '')} for t in {e.teacher_id for e, *_ in rows}], key=lambda x: x['name']),
            }

    @staticmethod
    def teacher_periods(skid, day, teacher_id):
        """A teacher's periods on a date (for marking cover by hand)."""
        day = _parse_day(day)
        with switch_to_institution_db(skid) as session:
            return [{'entry_id': e.id, 'period_number': e.period_number, 'start_time': e.start_time.strftime('%H:%M'),
                     'end_time': e.end_time.strftime('%H:%M'), 'class_section': f'{c} - {s}', 'subject_name': subj}
                    for (e, c, s, _sid, subj) in _day_entries(session, day) if e.teacher_id == int(teacher_id)]

    @staticmethod
    def assign(skid, actor_id, day, entry_id, substitute_id, note=None):
        day = _parse_day(day)
        note = (str(note).strip() if note else '') or None
        if note and len(note) > NOTE_MAX:
            raise SubstitutionError(f'The note can be at most {NOTE_MAX} characters')
        with switch_to_institution_db(skid) as session:
            ensure_table(session)
            if _off_day(session, day):
                raise SubstitutionError('That day is a holiday / weekly off')
            rows, subs, absent = SubstitutionService._context(session, day)
            match = next(((e, c, s) for (e, c, s, _sid, _subj) in rows if e.id == int(entry_id)), None)
            if not match:
                raise SubstitutionError("That period isn't in the timetable on this day", 404)
            entry = match[0]
            sub_id = int(substitute_id)
            if sub_id == entry.teacher_id:
                raise SubstitutionError("A teacher can't cover their own period")
            if not session.query(Teacher).filter_by(user_id=sub_id).first():
                raise SubstitutionError('Choose a teacher')
            if sub_id in absent:
                raise SubstitutionError("That teacher isn't available today")
            if SubstitutionService._busy(rows, subs, sub_id, entry.start_time, entry.end_time, skip_entry=entry.id):
                raise SubstitutionError('That teacher has another class at this time', 409)
            row = subs.get(entry.id)
            previous = row.substitute_teacher_id if row else None
            if row:
                row.substitute_teacher_id, row.assigned_by = sub_id, actor_id
                if note is not None:
                    row.note = note
            else:
                row = Substitution(date=day, timetable_entry_id=entry.id, absent_teacher_id=entry.teacher_id,
                                   substitute_teacher_id=sub_id, reason=absent.get(entry.teacher_id) or 'MANUAL',
                                   note=note, assigned_by=actor_id)
                session.add(row)
            session.commit()
            from app.services import push_events
            if previous and previous != sub_id:
                push_events.substitution_changed(skid, session, row, previous, removed=True)
            if previous != sub_id:
                push_events.substitution_changed(skid, session, row, sub_id, removed=False)
            return {'entry_id': entry.id, 'substitute_id': sub_id}

    @staticmethod
    def assign_all(skid, actor_id, day):
        """Give every uncovered period (not half day / teacher back) its top suggestion."""
        data = SubstitutionService.day(skid, day)
        done = 0
        for p in data['periods']:
            if p['substitute_id'] or p['optional'] or p['teacher_back']:
                continue
            # re-read: earlier assignments in this loop change who is free
            fresh = next((x for x in SubstitutionService.day(skid, day)['periods'] if x['entry_id'] == p['entry_id']), None)
            if fresh and fresh['suggestions']:
                SubstitutionService.assign(skid, actor_id, day, p['entry_id'], fresh['suggestions'][0]['teacher_id'])
                done += 1
        return {'assigned': done}

    @staticmethod
    def remove(skid, day, entry_id):
        """Take the substitute off a period (a period marked by hand stays listed, without a substitute)."""
        day = _parse_day(day)
        with switch_to_institution_db(skid) as session:
            ensure_table(session)
            row = session.query(Substitution).filter_by(date=day, timetable_entry_id=int(entry_id)).first()
            if not row:
                raise SubstitutionError('No cover arranged for that period', 404)
            previous = row.substitute_teacher_id
            if row.reason == 'MANUAL' and previous:
                row.substitute_teacher_id = None
            else:
                session.delete(row)
            session.commit()
            if previous:
                from app.services import push_events
                push_events.substitution_changed(skid, session, row, previous, removed=True)
            return {'removed': True}

    @staticmethod
    def mark_manual(skid, actor_id, day, entry_ids, note=None):
        """Mark periods of a present teacher as needing cover (exam duty, a meeting...)."""
        day = _parse_day(day)
        note = (str(note).strip() if note else '') or None
        with switch_to_institution_db(skid) as session:
            ensure_table(session)
            rows = {e.id: e for (e, *_rest) in _day_entries(session, day)}
            ids = [int(i) for i in (entry_ids or [])]
            if not ids:
                raise SubstitutionError('Choose at least one period')
            added = 0
            for eid in ids:
                if eid not in rows:
                    raise SubstitutionError("A chosen period isn't in the timetable on this day")
                if session.query(Substitution).filter_by(date=day, timetable_entry_id=eid).first():
                    continue
                session.add(Substitution(date=day, timetable_entry_id=eid, absent_teacher_id=rows[eid].teacher_id,
                                         reason='MANUAL', note=note, assigned_by=actor_id))
                added += 1
            session.commit()
            return {'added': added}

    @staticmethod
    def unmark(skid, day, entry_id):
        """Drop a period from the list altogether (by-hand periods, or "teacher is back")."""
        day = _parse_day(day)
        with switch_to_institution_db(skid) as session:
            ensure_table(session)
            row = session.query(Substitution).filter_by(date=day, timetable_entry_id=int(entry_id)).first()
            if not row:
                raise SubstitutionError('Nothing to remove', 404)
            previous = row.substitute_teacher_id
            session.delete(row)
            session.commit()
            if previous:
                from app.services import push_events
                push_events.substitution_changed(skid, session, row, previous, removed=True)
            return {'removed': True}

    @staticmethod
    def uncovered_today(skid):
        data = SubstitutionService.day(skid, date.today().isoformat())
        return {'needed': data['needed'], 'covered': data['covered'], 'uncovered': data['needed'] - data['covered']}


# ---------------------------------------------------------------- for timetables and the leave card

def day_substitutions(session, day):
    """{entry_id: (substitute_id, substitute_name, absent_teacher_name)} with a substitute on that date."""
    try:
        ensure_table(session)
        rows = session.query(Substitution).filter(Substitution.date == day, Substitution.substitute_teacher_id.isnot(None)).all()
    except Exception:
        session.rollback()
        return {}
    names = _names(session, {r.substitute_teacher_id for r in rows} | {r.absent_teacher_id for r in rows})
    return {r.timetable_entry_id: (r.substitute_teacher_id, names.get(r.substitute_teacher_id, ''), names.get(r.absent_teacher_id, ''))
            for r in rows}


def covering_periods(session, day, teacher_id):
    """Periods this teacher covers on that date, shaped like the teacher day timetable."""
    try:
        ensure_table(session)
        subs = {s.timetable_entry_id: s for s in session.query(Substitution).filter(
            Substitution.date == day, Substitution.substitute_teacher_id == int(teacher_id)).all()}
    except Exception:
        session.rollback()
        return []
    if not subs:
        return []
    names = _names(session, {s.absent_teacher_id for s in subs.values()})
    out = []
    for (e, c, s, _sid, subj) in _day_entries(session, day):
        if e.id in subs:
            out.append({'id': f'sub-{e.id}', 'period_number': e.period_number, 'start_time': e.start_time.strftime('%H:%M'),
                        'end_time': e.end_time.strftime('%H:%M'), 'subject_name': subj, 'subject_id': e.subject_id,
                        'class_name': c, 'section_name': s, 'room': e.room_number, 'day': day.strftime('%A'),
                        'is_substitution': True, 'substitute_for': names.get(subs[e.id].absent_teacher_id, '')})
    return out


def leave_cover(session, leave):
    """Approved staff leave: (periods on its working days from today, how many have a substitute)."""
    from app.services.calendar_service import working_dates
    start = max(leave.from_date, date.today())
    if leave.to_date < start:
        return None
    total = covered = 0
    try:
        ensure_table(session)
        for day in working_dates(session, start, leave.to_date, 'STAFF'):
            mine = [e for (e, *_rest) in _day_entries(session, day) if e.teacher_id == leave.user_id]
            if not mine:
                continue
            total += len(mine)
            covered += session.query(Substitution).filter(
                Substitution.date == day, Substitution.timetable_entry_id.in_([e.id for e in mine]),
                Substitution.substitute_teacher_id.isnot(None)).count()
    except Exception:
        session.rollback()
        return None
    return {'periods': total, 'covered': covered} if total else None
