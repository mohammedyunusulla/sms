"""
Server-side permission checks (QA A15): routes declare the permission they need, and the server reads the
same role tick boxes the menu uses.

PERMISSION_ENFORCEMENT (config / env):
  off     - only the routes' old role lists decide (as before)
  log     - the old role lists still decide; every request where the permission rule would decide
            differently is logged as PERMISSION_MISMATCH (for review before switching on)
  enforce - routes that declare a permission are decided by the user's role permissions
"""
import threading
import time

from flask import current_app, request

# Roles with full access (they don't use tick boxes; the menu treats them the same way)
FULL_ACCESS_ROLES = frozenset({'SUPER_ADMIN', 'SCHOOL_ADMIN'})
CACHE_SECONDS = 60

_cache = {}
_lock = threading.Lock()


def enforcement_mode():
    mode = str(current_app.config.get('PERMISSION_ENFORCEMENT') or 'off').strip().lower()
    return mode if mode in ('off', 'log', 'enforce') else 'off'


def account_role(session, school_user_id):
    """
    A person's one role: the role on their school record (school_users.role_id), falling back to their
    user_roles row for records saved without it. Sign-in and the permission check both use this.
    """
    from app.models.tenant.Roles import Role
    from app.models.tenant.SchoolUsers import SchoolUsers
    from app.models.tenant.UserRoles import UserRoles
    school_user = session.query(SchoolUsers).get(school_user_id)
    if school_user and school_user.role_id:
        role = session.query(Role).get(school_user.role_id)
        if role:
            return role
    return (
        session.query(Role)
        .join(UserRoles, UserRoles.role_id == Role.id)
        .filter(UserRoles.user_id == school_user_id)
        .order_by(Role.id)
        .first()
    )


def user_permissions(user):
    """
    The permission keys of the user's school role (the tick boxes), cached for CACHE_SECONDS per user.
    Empty for users without a school role, or whose role is switched off.
    """
    if not user.skid or not user.school_user_id:
        return frozenset()
    key = (str(user.skid), int(user.school_user_id))
    now = time.monotonic()
    with _lock:
        hit = _cache.get(key)
        if hit and hit[0] > now:
            return hit[1]
    from app.utils.db_manager import switch_to_school_db
    with switch_to_school_db(user.skid) as session:
        role = account_role(session, user.school_user_id)
        perms = frozenset(role.permissions or []) if role and role.is_active is not False else frozenset()
    with _lock:
        _cache[key] = (now + CACHE_SECONDS, perms)
    return perms


def forget_cached_permissions(skid=None):
    """Drop cached permissions (all, or one school's) - e.g. right after a role's tick boxes are saved."""
    with _lock:
        if skid is None:
            _cache.clear()
        else:
            for key in [k for k in _cache if k[0] == str(skid)]:
                _cache.pop(key, None)


def permission_allows(user, role, permissions):
    """True if the role has full access or its tick boxes include any of `permissions`."""
    if role in FULL_ACCESS_ROLES:
        return True
    return bool(user_permissions(user) & set(permissions))


def decide(user, role, allowed_roles, permissions):
    """
    Final access decision for a route. `permissions` is a tuple of keys (any one is enough), or empty when the
    route is decided by role only (sign-in, a student's / parent's own pages, Super Admin's school management).
    """
    old_ok = not allowed_roles or role in allowed_roles
    if not permissions:
        return old_ok
    mode = enforcement_mode()
    if mode == 'off':
        return old_ok
    try:
        new_ok = permission_allows(user, role, permissions)
    except Exception as e:  # never let the check itself break a request in off/log mode
        current_app.logger.error(f"Permission check failed for {request.path}: {e}")
        if mode == 'enforce':
            return False
        return old_ok
    if mode == 'enforce':
        return new_ok
    if new_ok != old_ok:
        current_app.logger.warning(
            f"PERMISSION_MISMATCH {request.method} {request.url_rule.rule if request.url_rule else request.path} "
            f"role={role} user={user.id} needs={'|'.join(permissions)} old={'allow' if old_ok else 'deny'} "
            f"new={'allow' if new_ok else 'deny'}"
        )
    return old_ok
