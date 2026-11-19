"""
Soft delete / reactivate for school users (teachers, parents, ...).

Only the active flags change — the tenant school_users row and the main-DB login. Every record
that references the person (sections, timetables, assignments, marks, children links, ...) is kept,
so reactivating restores everything.
"""
from app import db
from app.models.main.User import User
from app.models.tenant import SchoolUsers
from app.utils.db_manager import switch_to_school_db


def set_school_user_active(skid, school_user_id, active, profile_model, label):
    """
    profile_model: the role table keyed by user_id (e.g. Teacher, Parent) — used to confirm the role.
    Returns {'success', 'code', 'message', 'data'}.
    """
    try:
        school_user_id = int(school_user_id)
    except (TypeError, ValueError):
        return {'success': False, 'code': 400, 'message': f'Invalid {label.lower()} id'}

    with switch_to_school_db(skid) as tenant_session:
        school_user = tenant_session.query(SchoolUsers).filter_by(id=school_user_id).first()
        profile = school_user and tenant_session.query(profile_model).filter_by(user_id=school_user_id).first()
        if not profile:
            return {'success': False, 'code': 404, 'message': f'{label} not found'}
        if bool(school_user.is_active) == bool(active):
            state = 'active' if active else 'inactive'
            return {'success': False, 'code': 400, 'message': f'{label} is already {state}'}
        school_user.is_active = bool(active)
        name = f"{school_user.first_name} {school_user.last_name}".strip()

    main_user = User.query.filter_by(school_user_id=school_user_id, skid=skid).first()
    if main_user:
        main_user.is_active = bool(active)
        db.session.commit()

    return {
        'success': True,
        'code': 200,
        'message': f"{name} {'reactivated' if active else 'deactivated (records kept, can be reactivated)'}",
        'data': {'id': school_user_id, 'is_active': bool(active), 'login_updated': bool(main_user)},
    }


def status_response(result):
    """Flask response for a set_school_user_active result."""
    from flask import jsonify
    if result['success']:
        return jsonify({'code': 200, 'status': 'success', 'message': result['message'], 'data': result['data']}), 200
    return jsonify({'code': result['code'], 'status': 'error', 'message': result['message']}), result['code']
