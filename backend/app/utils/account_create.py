"""
Helpers that keep student / teacher / parent creation all-or-nothing.

An account lives in two databases: the login (main DB) and the institution record + profile (tenant DB).
Creation order:
  1. main DB: add the login and flush (checks it, nothing saved yet)
  2. tenant DB: institution record + profile (+ enrollment) + role link, saved together in one commit
  3. main DB: commit the login
If step 3 fails, remove_institution_user() deletes what step 2 saved, so nothing half-made is left.
"""
from sqlalchemy import text

from app.models.tenant.Roles import Role
from app.models.tenant.UserRoles import UserRoles
from app.utils.db_manager import switch_to_institution_db


def role_for(tenant_session, role_code):
    """The institution's role for this account type (looked up by code, never taken from the request)."""
    role = tenant_session.query(Role).filter_by(role_code=role_code).first()
    if not role:
        raise ValueError(f"This institution has no {role_code.replace('_', ' ').title()} role set up")
    return role


def add_role_link(tenant_session, institution_user, role):
    """Set the institution user's role and add the user_roles row (same transaction as the user)."""
    institution_user.role_id = role.id
    tenant_session.add(UserRoles(user_id=institution_user.id, role_id=role.id, assigned_by=None, is_active=True))


def remove_institution_user(skid, institution_user_id):
    """Undo step 2: delete the tenant rows created for this new account."""
    if not institution_user_id:
        return
    params = {"id": int(institution_user_id)}
    with switch_to_institution_db(skid) as tenant_session:
        for statement in (
            "DELETE FROM user_roles WHERE user_id = :id",
            "DELETE FROM student_parents WHERE student_user_id = :id OR parent_user_id = :id",
            "DELETE FROM student_enrollments WHERE student_id = :id",
            "DELETE FROM students WHERE user_id = :id",
            "DELETE FROM teachers WHERE user_id = :id",
            "DELETE FROM parent WHERE user_id = :id",
            "DELETE FROM institution_users WHERE id = :id",
        ):
            tenant_session.execute(text(statement), params)
        tenant_session.commit()
