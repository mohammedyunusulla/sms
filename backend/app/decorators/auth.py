from functools import wraps
from flask import request, jsonify, current_app, g
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.main.User import User, UserRole


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