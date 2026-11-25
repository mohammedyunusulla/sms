# utils/seeders.py

from app.models.tenant.Roles import Role
from app.models.main.User import UserRole  # your Enum

# Every permission key the frontend understands.
# Keep in sync with the `Permission` enum in frontend/src/config/permissions.ts.
ALL_PERMISSIONS = [
    'view_users', 'manage_users', 'delete_users',
    'view_teachers', 'manage_teachers', 'delete_teachers',
    'view_students', 'manage_students', 'delete_students',
    'manage_roles',
    'view_classes', 'manage_classes',
    'view_attendance', 'manage_attendance',
    'view_announcements', 'manage_announcements',
    'view_timetable', 'manage_timetable', 'view_my_timetable',
    'view_exams', 'manage_exams',
    'view_marks', 'manage_marks',
    'view_fees', 'manage_fees',
    'view_expenses', 'manage_expenses',
    'view_syllabus_and_progress', 'manage_syllabus',
    'view_assignments', 'manage_assignments',
    'view_child_assignments', 'view_child_timetable', 'view_child_fees', 'view_child_syllabus',
    'view_bus_scan', 'manage_bus_scan',
    # added with server-side permission checks (QA A15)
    'manage_academic_years', 'manage_rooms', 'manage_salaries',
    # fee structures, installment plans, discounts, cancelling payments (a Clerk only collects)
    'manage_fee_settings',
    # decide any leave request (class teachers decide their own sections' student leave without it)
    'approve_leave',
    # mark / edit staff attendance and see the monthly staff register
    'manage_staff_attendance',
    # holiday calendar: weekly offs and holidays (everyone can view)
    'manage_holidays',
    # events / parent-teacher meetings for everyone (class teachers manage their own section's without it)
    'manage_events',
]

# Default permissions for system roles in a new institution.
# INSTITUTION_ADMIN bypasses permission checks in the frontend, so it needs none.
DEFAULT_ROLE_PERMISSIONS = {
    'PRINCIPAL': list(ALL_PERMISSIONS),
    'TEACHER': [
        'view_students', 'view_classes',
        'view_attendance', 'manage_attendance',
        'view_announcements',
        'view_timetable', 'view_my_timetable',
        'view_exams',
        'manage_marks', 'view_marks',
        'view_syllabus_and_progress',
        'manage_assignments',
    ],
    'STUDENT': [
        'view_announcements', 'view_my_timetable', 'view_exams',
        'view_assignments', 'view_syllabus_and_progress',
    ],
    'PARENT': [
        'view_child_assignments', 'view_child_timetable', 'view_child_fees', 'view_child_syllabus',
        'view_announcements',
    ],
    'BUS_STAFF': ['view_bus_scan', 'manage_bus_scan'],
    # Fee counter: look up students, collect fees, receipts, defaulters; fee structures and classes read-only.
    # The backend routes for these allow CLERK (cancelling, discounts and installment plans stay with admins).
    'CLERK': ['view_fees', 'manage_fees', 'view_students', 'view_classes'],
}

# Built-in role names shown to users where the plain title of the code doesn't fit (global wording:
# schools, colleges and universities). Existing databases are renamed at start-up (TENANT_SCHEMA_UPDATES).
ROLE_DISPLAY_NAMES = {'INSTITUTION_ADMIN': 'Institution Admin'}


def seed_default_roles(session, institution_id=None):
    """
    Insert default roles (with default permissions) into the tenant DB's `roles` table.
    """
    existing_roles = session.query(Role.role_code).all()
    existing_codes = {r[0] for r in existing_roles}

    new_roles = []

    for role_enum in UserRole:
        if role_enum.value not in existing_codes and role_enum.value !="SUPER_ADMIN":
            new_roles.append(
                Role(
                    # e.g. TEACHER -> Teacher; the admin role is shown as "Institution Admin" (code stays INSTITUTION_ADMIN)
                    role_name=ROLE_DISPLAY_NAMES.get(role_enum.value, role_enum.value.replace("_", " ").title()),
                    role_code=role_enum.value,
                    base_role=role_enum.value,
                    permissions=list(DEFAULT_ROLE_PERMISSIONS.get(role_enum.value, [])),
                    is_system_role=True,
                    is_active=True,
                    institution_id=institution_id
                )
            )

    if new_roles:
        session.add_all(new_roles)
        session.commit()


def add_missing_system_roles(session, apply=False):
    """
    For existing institutions: the system roles they don't have yet (e.g. CLERK, added later), with default permissions.
    Returns the role codes that were (or would be) added.
    """
    existing = {r[0] for r in session.query(Role.role_code).all()}
    missing = [r.value for r in UserRole if r.value not in existing and r.value != "SUPER_ADMIN"]
    if apply and missing:
        seed_default_roles(session)
    return missing


def fill_empty_role_permissions(session, apply=False):
    """
    For existing institutions: give default permissions to system roles that currently have none.
    Roles that already have any permissions (e.g. configured by hand) are never touched.
    Returns a list of (role_code, permissions) that were (or would be) filled.
    """
    changes = []
    for role in session.query(Role).filter(Role.is_system_role.is_(True)).all():
        defaults = DEFAULT_ROLE_PERMISSIONS.get(role.role_code)
        if defaults and not role.permissions:
            changes.append((role.role_code, list(defaults)))
            if apply:
                role.permissions = list(defaults)
    if apply and changes:
        session.commit()
    return changes
