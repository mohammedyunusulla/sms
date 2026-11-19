"""
Helpers that keep student / teacher / parent creation all-or-nothing.

An account lives in two databases: the login (main DB) and the school record + profile (tenant DB).
Creation order:
  1. main DB: add the login and flush (checks it, nothing saved yet)
  2. tenant DB: school record + profile (+ enrollment) + role link, saved together in one commit
  3. main DB: commit the login
If step 3 fails, remove_school_user() deletes what step 2 saved, so nothing half-made is left.
"""
from sqlalchemy import text

from app.models.tenant.Roles import Role
from app.models.tenant.UserRoles import UserRoles
from app.utils.db_manager import switch_to_school_db


def role_for(tenant_session, role_code):
    """The school's role for this account type (looked up by code, never taken from the request)."""
    role = tenant_session.query(Role).filter_by(role_code=role_code).first()
    if not role:
        raise ValueError(f"This school has no {role_code.replace('_', ' ').title()} role set up")
    return role


def add_role_link(tenant_session, school_user, role):
    """Set the school user's role and add the user_roles row (same transaction as the user)."""
    school_user.role_id = role.id
    tenant_session.add(UserRoles(user_id=school_user.id, role_id=role.id, assigned_by=None, is_active=True))


def remove_school_user(skid, school_user_id):
    """Undo step 2: delete the tenant rows created for this new account."""
    if not school_user_id:
        return
    params = {"id": int(school_user_id)}
    with switch_to_school_db(skid) as tenant_session:
        for statement in (
            "DELETE FROM user_roles WHERE user_id = :id",
            "DELETE FROM student_parents WHERE student_user_id = :id OR parent_user_id = :id",
            "DELETE FROM student_enrollments WHERE student_id = :id",
            "DELETE FROM students WHERE user_id = :id",
            "DELETE FROM teachers WHERE user_id = :id",
            "DELETE FROM parent WHERE user_id = :id",
            "DELETE FROM school_users WHERE id = :id",
        ):
            tenant_session.execute(text(statement), params)
        tenant_session.commit()
