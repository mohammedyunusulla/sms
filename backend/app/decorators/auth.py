from functools import wraps
from flask import request, jsonify, current_app, g
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.main.User import User, UserRole


def _requested_skid(view_kwargs):
    """
    Return the school (tenant) code a request targets, if any.
    Checked in order: URL path parameter, ?skid= query string, "skid" in the JSON body.
    """
    if view_kwargs.get('skid') is not None:
        return view_kwargs['skid']
    if request.args.get('skid'):
        return request.args.get('skid')
    body = request.get_json(silent=True)
    if isinstance(body, dict) and body.get('skid'):
        return body['skid']
    return None


def login_required(allowed_roles=None):
    """
    Decorator to require login and optionally check roles.
    Attaches the authenticated user to request.current_user and g.current_user.
    """
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            try:
                # Allow CORS preflight without JWT validation.
                if request.method == 'OPTIONS':
                    return current_app.make_default_options_response()

                # Get current user ID from JWT
                current_user_id = get_jwt_identity()
                if not current_user_id:
                    return jsonify({'message': 'Invalid token'}), 401

                # Get user from database
                user = User.get_by_id(current_user_id)

                if not user:
                    return jsonify({'message': 'User not found'}), 401

                if not user.is_active:
                    return jsonify({'message': 'User account is deactivated'}), 403

                # Check roles if specified
                if allowed_roles:
                    user_role = user.role.value if hasattr(user.role, 'value') else user.role
                    if user_role not in allowed_roles:
                        return jsonify({'message': 'Insufficient permissions'}), 403

                # Tenant isolation: non-super-admins may only touch their own school's data.
                if user.role != UserRole.SUPER_ADMIN:
                    target_skid = _requested_skid(kwargs)
                    if target_skid is not None and str(target_skid) != str(user.skid):
                        current_app.logger.warning(
                            f"Cross-school access blocked: user {user.id} (skid={user.skid}) "
                            f"-> skid={target_skid} {request.method} {request.path}"
                        )
                        return jsonify({'message': 'Access denied: you can only access your own school data'}), 403

                # Add user to request context
                request.current_user = user
                g.current_user = user

            except Exception as e:
                current_app.logger.error(f"Authentication error: {str(e)}")
                return jsonify({'message': 'Authentication failed'}), 401

            return f(*args, **kwargs)

        return decorated_function
    return decorator


def super_admin_required(f):
    """Decorator to require super admin role"""
    return login_required(['super_admin'])(f)


def school_admin_required(f):
    """Decorator to require school admin or higher role"""
    return login_required(['super_admin', 'school_admin', 'principal'])(f)


def teacher_required(f):
    """Decorator to require teacher or higher role"""
    return login_required(['super_admin', 'school_admin', 'principal', 'teacher'])(f)


# Roles that may look up any student in their own school (teacher scoping is handled separately).
STUDENT_DATA_STAFF_ROLES = {'SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER', 'BUS_STAFF', 'ACCOUNTANT', 'CLERK'}
STUDENT_ACCESS_DENIED = "Access denied: you can only view your own or your child's records"


def _role_value(user):
    return user.role.value if hasattr(user.role, 'value') else str(user.role)


def can_view_student(user, skid, student_user_id):
    """
    Staff may view any student of their school; a student only themselves;
    a parent only students linked to them in student_parents.
    """
    role = _role_value(user)
    if role in STUDENT_DATA_STAFF_ROLES:
        return True
    if role == 'STUDENT':
        return user.school_user_id is not None and int(student_user_id) == int(user.school_user_id)
    if role == 'PARENT' and user.school_user_id is not None:
        from app.utils.db_manager import switch_to_school_db
        from app.models.tenant.StudentParent import StudentParent
        with switch_to_school_db(skid) as session:
            return session.query(StudentParent).filter_by(
                parent_user_id=user.school_user_id, student_user_id=int(student_user_id)
            ).first() is not None
    return False


def student_access_required(param='student_id', source='path', resolver=None):
    """
    Restrict an endpoint to the student themselves, their parents, or staff.
    Must be placed BELOW @login_required (it needs request.current_user).

    param:    name of the path/query parameter holding the id
    source:   'path' (view kwargs) or 'query' (request.args)
    resolver: optional fn(skid, value) -> student_user_id, when the id is not a student id
              (e.g. a student_fee_id). Returning None means "not found" (404).
    If the parameter is absent the endpoint runs as normal (e.g. a student resolving themselves).
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = getattr(request, 'current_user', None)
            if not user:
                return jsonify({'message': 'User not authenticated'}), 401
            if _role_value(user) in STUDENT_DATA_STAFF_ROLES:
                return f(*args, **kwargs)

            raw = kwargs.get(param) if source == 'path' else request.args.get(param)
            if raw in (None, ''):
                return f(*args, **kwargs)
            skid = kwargs.get('skid') or request.args.get('skid') or user.skid
            try:
                value = int(raw)
                student_user_id = resolver(skid, value) if resolver else value
            except (TypeError, ValueError):
                return jsonify({'message': f'Invalid {param}'}), 400
            if student_user_id is None:
                return jsonify({'message': 'Record not found'}), 404
            if not can_view_student(user, skid, student_user_id):
                current_app.logger.warning(
                    f"Student data access blocked: user {user.id} ({_role_value(user)}) -> student {student_user_id} "
                    f"{request.method} {request.path}"
                )
                return jsonify({'message': STUDENT_ACCESS_DENIED}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator


def student_fee_owner(skid, student_fee_id):
    """Resolver for student_access_required: student_fee_id -> student_user_id."""
    from app.utils.db_manager import switch_to_school_db
    from app.models.tenant.FeeModels import StudentFee
    with switch_to_school_db(skid) as session:
        fee = session.query(StudentFee).filter_by(id=student_fee_id).first()
        return fee.student_id if fee else None


def own_parent_required(param='parent_user_id'):
    """A parent may only use their own parent id; staff are unrestricted. Place BELOW @login_required."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = getattr(request, 'current_user', None)
            if not user:
                return jsonify({'message': 'User not authenticated'}), 401
            if _role_value(user) in STUDENT_DATA_STAFF_ROLES:
                return f(*args, **kwargs)
            if _role_value(user) == 'PARENT' and str(kwargs.get(param)) == str(user.school_user_id):
                return f(*args, **kwargs)
            current_app.logger.warning(
                f"Parent data access blocked: user {user.id} ({_role_value(user)}) -> parent {kwargs.get(param)} {request.path}"
            )
            return jsonify({'message': STUDENT_ACCESS_DENIED}), 403
        return wrapper
    return decorator


def same_school_required(f):
    """
    Decorator to ensure user can only access data from their own school.
    Super admins can access any school.
    Validates that any school_id in the URL matches the user's school.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = getattr(request, 'current_user', None)
        if not user:
            return jsonify({'message': 'User not authenticated'}), 401

        # Super admins can access any school
        if user.role == UserRole.SUPER_ADMIN:
            return f(*args, **kwargs)

        # Validate school_id if present in URL kwargs
        if 'school_id' in kwargs:
            if str(kwargs['school_id']) != str(user.school_id):
                return jsonify({'message': 'Access denied: you can only access your own school data'}), 403
        else:
            # Auto-inject user's school_id if not in URL
            if user.school_id:
                kwargs['school_id'] = user.school_id

        return f(*args, **kwargs)

    return decorated_function