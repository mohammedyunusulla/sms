"""
What each institution has switched on: features and sign-in roles (set by the Super Admin).

- institutions.features     JSON list of feature keys (the always-on ones are not stored)
- institutions.login_roles  JSON list of role codes that may sign in (the Institution Admin always may)

A feature that is off is refused for that institution's API calls (login_required checks the request's
address against API_PREFIXES) and hidden in the web app. Its data stays.
"""
import time
from typing import Dict, Iterable, List, Optional, Set

# Always on (not switches): dashboard, user management, classes & sections, academic years, roles, push.

# key -> label, what it covers, the features it needs
FEATURES: Dict[str, dict] = {
    'subjects':         {'label': 'Subjects', 'about': 'Subjects and which sections study them', 'requires': []},
    'attendance':       {'label': 'Attendance', 'about': 'Daily student attendance and reports', 'requires': []},
    'staff_attendance': {'label': 'Staff Attendance', 'about': 'Daily staff attendance and the monthly register', 'requires': []},
    'leave':            {'label': 'Leave', 'about': 'Leave requests for students and staff, with paid-leave balances', 'requires': []},
    'calendar':         {'label': 'Calendar & Holidays', 'about': 'Holidays, weekly offs and the calendar page', 'requires': []},
    'events':           {'label': 'Events', 'about': 'Events and parent-teacher meetings on the calendar', 'requires': ['calendar']},
    'announcements':    {'label': 'Announcements', 'about': 'Notices to students, parents and staff', 'requires': []},
    'timetable':        {'label': 'Timetable', 'about': 'Class and teacher timetables', 'requires': ['subjects']},
    'substitutions':    {'label': 'Substitutions', 'about': 'Cover for absent teachers', 'requires': ['timetable']},
    'exams':            {'label': 'Exams', 'about': 'Exam types, subject configuration and exam timetables', 'requires': ['subjects']},
    'marks':            {'label': 'Marks & Results', 'about': 'Marks entry, results and progress cards', 'requires': ['exams']},
    'rooms':            {'label': 'Rooms', 'about': 'Rooms and their capacity', 'requires': []},
    'seating':          {'label': 'Seating Arrangement', 'about': 'Exam seating plans', 'requires': ['exams', 'rooms']},
    'syllabus':         {'label': 'Syllabus', 'about': 'Lessons, topics and progress tracking', 'requires': ['subjects']},
    'assignments':      {'label': 'Assignments', 'about': 'Assignments with submissions and feedback', 'requires': ['subjects']},
    'homework':         {'label': 'Homework AI', 'about': 'Daily homework with a timer, hints and AI grading', 'requires': ['subjects']},
    'fees':             {'label': 'Fees', 'about': 'Fee structure, collection, defaulters and reports', 'requires': []},
    'expenses':         {'label': 'Expenses', 'about': 'Day-to-day expenses', 'requires': []},
    'salary':           {'label': 'Salary', 'about': 'Salary setup and monthly payments', 'requires': []},
    'bus':              {'label': 'Bus Management', 'about': 'Bus check-in by QR and live tracking', 'requires': []},
}
ALL_FEATURES: List[str] = list(FEATURES)

# Roles whose sign-in can be switched on or off (the Institution Admin can always sign in)
LOGIN_ROLES: Dict[str, str] = {
    'PRINCIPAL': 'Principal', 'TEACHER': 'Teacher', 'CLERK': 'Clerk', 'BUS_STAFF': 'Bus Staff',
    'STUDENT': 'Student', 'PARENT': 'Parent',
}
STAFF_LOGIN_ROLES = ['PRINCIPAL', 'TEACHER', 'CLERK', 'BUS_STAFF']
ALWAYS_LOGIN_ROLES = ('SUPER_ADMIN', 'INSTITUTION_ADMIN')

# A new institution starts with no optional feature and staff sign-in only
DEFAULT_FEATURES: List[str] = []
DEFAULT_LOGIN_ROLES: List[str] = list(STAFF_LOGIN_ROLES)

# API address -> feature (longest match wins). Addresses not listed are always on.
API_PREFIXES = (
    ('/api/subjects', 'subjects'),
    ('/api/attendance', 'attendance'),
    ('/api/staff-attendance', 'staff_attendance'),
    ('/api/leave', 'leave'),
    ('/api/holidays', 'calendar'),
    ('/api/calendar', 'calendar'),
    ('/api/events', 'events'),
    ('/api/announcements', 'announcements'),
    ('/api/timeTable', 'timetable'),
    ('/api/substitutions', 'substitutions'),
    ('/api/exams', 'exams'),
    ('/api/marks', 'marks'),
    ('/api/progress-card', 'marks'),
    ('/api/rooms', 'rooms'),
    ('/api/seating', 'seating'),
    ('/api/syllabus', 'syllabus'),
    ('/api/assignments', 'assignments'),
    ('/api/homework', 'homework'),
    ('/api/fee', 'fees'),
    ('/api/expenses/salary-setup', 'salary'),
    ('/api/expenses/salary-payments', 'salary'),
    ('/api/expenses/list/salary-setup', 'salary'),
    ('/api/expenses', 'expenses'),
    ('/api/bus-scan', 'bus'),
    ('/api/bus-location', 'bus'),
)
_PREFIXES_LONGEST_FIRST = sorted(API_PREFIXES, key=lambda row: -len(row[0]))


def feature_for_path(path: str) -> Optional[str]:
    """The feature an API address belongs to, or None when it is always on."""
    for prefix, feature in _PREFIXES_LONGEST_FIRST:
        if path == prefix or path.startswith(prefix + '/'):
            return feature
    return None


def with_requirements(keys: Iterable[str]) -> List[str]:
    """The given features plus everything they need, in catalogue order (unknown keys dropped)."""
    wanted: Set[str] = set()

    def add(key):
        if key in FEATURES and key not in wanted:
            wanted.add(key)
            for needed in FEATURES[key]['requires']:
                add(needed)
    for key in keys or []:
        add(key)
    return [key for key in ALL_FEATURES if key in wanted]


def dependents_of(key: str) -> List[str]:
    """Features that can't work without this one (directly or through another feature)."""
    found: Set[str] = set()

    def walk(needed):
        for other, info in FEATURES.items():
            if needed in info['requires'] and other not in found:
                found.add(other)
                walk(other)
    walk(key)
    return [k for k in ALL_FEATURES if k in found]


def clean_login_roles(roles: Iterable[str]) -> List[str]:
    chosen = {str(r).upper() for r in (roles or [])}
    return [code for code in LOGIN_ROLES if code in chosen]


def catalogue() -> dict:
    """The switches the Super Admin page shows."""
    return {
        'features': [
            {'key': key, 'label': info['label'], 'about': info['about'], 'requires': info['requires'],
             'needed_by': dependents_of(key)}
            for key, info in FEATURES.items()
        ],
        'always_on': ['Dashboard', 'User Management', 'Classes & Sections', 'Academic Years'],
        'login_roles': [{'code': code, 'label': label} for code, label in LOGIN_ROLES.items()],
    }


# ------------------------------------------------------------------ an institution's settings
_CACHE: Dict[str, tuple] = {}
_CACHE_SECONDS = 30  # also cleared on save (forget); the time limit covers other server processes


def forget(skid: Optional[str] = None) -> None:
    if skid is None:
        _CACHE.clear()
    else:
        _CACHE.pop(str(skid), None)


def settings_for(skid) -> dict:
    """{'features': [...], 'login_roles': [...]} of an institution; everything off when it isn't found."""
    key = str(skid)
    hit = _CACHE.get(key)
    if hit and hit[0] > time.monotonic():
        return hit[1]
    from app.models.main.Institution import Institution
    institution = Institution.query.filter_by(skid=key).first()
    value = settings_of(institution)
    _CACHE[key] = (time.monotonic() + _CACHE_SECONDS, value)
    return value


def settings_of(institution) -> dict:
    if not institution:
        return {'features': [], 'login_roles': []}
    return {
        'features': with_requirements(institution.features or []),
        'login_roles': clean_login_roles(institution.login_roles or []),
    }


def feature_enabled(skid, feature: str) -> bool:
    return feature in settings_for(skid)['features']


def login_enabled(skid, role) -> bool:
    """May people of this role sign in (and get a login when they are created)?"""
    code = getattr(role, 'value', role)
    code = str(code or '').upper()
    if code in ALWAYS_LOGIN_ROLES:
        return True
    return code in settings_for(skid)['login_roles']


def feature_label(feature: str) -> str:
    return FEATURES.get(feature, {}).get('label', feature)


# ------------------------------------------------------------------ start-up: older databases
def prepare_switches(conn) -> Optional[str]:
    """
    One-time, for databases older than the switches: add the two columns, switch every feature on for the
    institutions that exist (they had everything), give sign-in to staff and - where the old tier column
    allowed student / parent logins - to students and parents, then drop that old column from both tables.
    Does nothing once done.
    """
    import json
    from sqlalchemy import text

    def has_column(table, column):
        return conn.execute(text(
            "SELECT 1 FROM information_schema.columns WHERE table_name = :t AND column_name = :c"
        ), {'t': table, 'c': column}).first() is not None

    if not conn.execute(text("SELECT to_regclass('institutions')")).scalar():
        return None
    done = []
    for column in ('features', 'login_roles'):
        if not has_column('institutions', column):
            conn.execute(text(f"ALTER TABLE institutions ADD COLUMN {column} JSON"))
            done.append(f'added institutions.{column}')

    OLD = 'plan'  # the old tier column; its two upper values gave students and parents a login
    had_old = has_column('institutions', OLD)
    rows = conn.execute(text(
        "SELECT id" + (f", {OLD}::text" if had_old else ", NULL") + " FROM institutions WHERE features IS NULL OR login_roles IS NULL"
    )).fetchall()
    for institution_id, old_value in rows:
        family_logins = not had_old or str(old_value).upper() in ('STANDARD', 'PREMIUM')
        roles = list(STAFF_LOGIN_ROLES) + (['STUDENT', 'PARENT'] if family_logins else [])
        conn.execute(text(
            "UPDATE institutions SET features = COALESCE(features, CAST(:f AS JSON)), "
            "login_roles = COALESCE(login_roles, CAST(:r AS JSON)) WHERE id = :id"
        ), {'f': json.dumps(ALL_FEATURES), 'r': json.dumps(roles), 'id': institution_id})
    if rows:
        done.append(f'set switches for {len(rows)} institution(s)')

    if had_old:
        conn.execute(text(f"ALTER TABLE institutions DROP COLUMN {OLD}"))
        done.append(f'dropped institutions.{OLD}')
    if conn.execute(text("SELECT to_regclass('users')")).scalar() and has_column('users', OLD):
        conn.execute(text(f"ALTER TABLE users DROP COLUMN {OLD}"))
        done.append(f'dropped users.{OLD}')
    conn.execute(text("DROP TYPE IF EXISTS institutionplan"))
    return '; '.join(done) or None
