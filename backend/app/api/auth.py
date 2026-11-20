from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.services import AuthService
from app.decorators import log_actions, login_required
from app import limiter
from app.utils.security import validate_password_strength

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
@log_actions('USER_LOGIN')
def login():
    """
    User login endpoint.
    Rate limited to 5 attempts per minute per IP.
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'message': 'No data provided'}), 400

        identifier = data.get('identifier')
        password = data.get('password')

        if not identifier or not password:
            return jsonify({'message': 'Username and password are required'}), 400

        # Authenticate user
        user = AuthService.authenticate_user(identifier, password)
        if not user:
            return jsonify({'message': 'Invalid credentials'}), 401

        # Check if user's school is active
        if user.school_id:
            school = user.school
            if not school:
                return jsonify({'message': 'School not found'}), 404

            if not school.is_active:
                return jsonify({
                    'message': 'Your school account is currently inactive. Please contact support for assistance.'
                }), 403

        # Create session and tokens
        session_data = AuthService.create_user_session(user)

        return jsonify({
            'message': 'Login successful',
            'access_token': session_data['access_token'],
            'refresh_token': session_data['refresh_token'],
            'user': session_data['user']
        }), 200

    except Exception as e:
        current_app.logger.error(f"Login error: {str(e)}")
        return jsonify({'message': 'Login failed. Please try again later.'}), 500

@auth_bp.route('/logout', methods=['POST'])
@login_required(self_service=True)
@log_actions('USER_LOGOUT')
def logout():
    """
    User logout endpoint.
    Invalidates the current session token from JWT claims.
    """
    try:
        user = request.current_user
        claims = get_jwt()
        session_token = claims.get('session_token')

        # Logout user (specific session if token available, all sessions otherwise)
        AuthService.logout_user(user, session_token)

        return jsonify({'message': 'Logout successful'}), 200

    except Exception as e:
        current_app.logger.error(f"Logout error: {str(e)}")
        return jsonify({'message': 'Logout failed. Please try again.'}), 500

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
@limiter.limit("10 per minute")
@log_actions('TOKEN_REFRESH')
def refresh():
    """
    Refresh access token.
    Rotates both access and refresh tokens for security.
    """
    try:
        current_user_id = get_jwt_identity()
        claims = get_jwt()
        old_session_token = claims.get('session_token')

        # Create new access token with session rotation
        token_data = AuthService.refresh_token(current_user_id, old_session_token)
        if not token_data:
            return jsonify({'message': 'Invalid or expired session'}), 401

        response = {
            'message': 'Token refreshed successfully',
            'access_token': token_data['access_token'],
            'user': token_data['user']
        }

        # Include new refresh token if rotated
        if 'refresh_token' in token_data:
            response['refresh_token'] = token_data['refresh_token']

        return jsonify(response), 200

    except Exception as e:
        current_app.logger.error(f"Token refresh error: {str(e)}")
        return jsonify({'message': 'Token refresh failed. Please login again.'}), 500

@auth_bp.route('/me', methods=['GET'])
@login_required(self_service=True)
def get_current_user():
    """
    Get current user information
    """
    try:
        user = request.current_user
        return jsonify({
            'user': user.to_dict()
        }), 200

    except Exception as e:
        current_app.logger.error(f"Get user info error: {str(e)}")
        return jsonify({'message': 'Failed to get user info'}), 500


@auth_bp.route('/me', methods=['PUT'])
@login_required(self_service=True)
@log_actions('PROFILE_UPDATE')
def update_current_user():
    """
    Update the current user's own profile.
    Only first_name, last_name, and phone can be changed via this endpoint.
    Email, username, role, and school are protected.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No data provided'}), 400

        user = request.current_user
        updated = AuthService.update_profile(user, data)

        return jsonify({
            'message': 'Profile updated successfully',
            'user': updated,
        }), 200

    except ValueError as e:
        return jsonify({'message': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Profile update error: {str(e)}")
        return jsonify({'message': 'Failed to update profile'}), 500

@auth_bp.route('/change-password', methods=['POST'])
@login_required(self_service=True)
@limiter.limit("3 per minute")
@log_actions('PASSWORD_CHANGE')
def change_password():
    """
    Change user password.
    Validates new password strength.
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'message': 'No data provided'}), 400

        old_password = data.get('old_password')
        new_password = data.get('new_password')

        if not old_password or not new_password:
            return jsonify({'message': 'Old password and new password are required'}), 400

        # Validate new password strength
        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            return jsonify({'message': error_msg}), 400

        user = request.current_user

        # Change password using service
        from app.services import UserService
        UserService.change_password(user.id, old_password, new_password)

        return jsonify({'message': 'Password changed successfully'}), 200

    except ValueError as e:
        return jsonify({'message': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Password change error: {str(e)}")
        return jsonify({'message': 'Password change failed. Please try again.'}), 500