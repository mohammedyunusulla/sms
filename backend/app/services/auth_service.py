from flask import request, current_app
from flask_jwt_extended import create_access_token, create_refresh_token
from app.models.main.User import User
from app.models.main.UserSession import UserSession
from app.models.tenant.Roles import Role
from app.models.tenant.UserRoles import UserRoles
from app.models.tenant.AcademicYear import AcademicYear
from app.decorators.logging import log_login_attempt, log_logout
from datetime import datetime, timedelta
from app.utils.db_manager import switch_to_school_db
from app.utils.security import validate_password_strength, get_client_ip
import uuid

class AuthService:
    
    # Maximum failed login attempts before account lockout
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 15
    # Maximum concurrent sessions per user
    MAX_SESSIONS_PER_USER = 5

    @staticmethod
    def authenticate_user(identifier, password):
        """
        Authenticate user with username/password.
        Returns user object if successful, None otherwise.
        Includes account lockout after MAX_FAILED_ATTEMPTS.
        """
        try:
            # Find user by username or email
            user = User.get_by_username(identifier)
            if not user:
                user = User.get_by_email(identifier)
            if not user:
                log_login_attempt(success=False, error_message="User not found")
                return None

            if not user.is_active:
                log_login_attempt(success=False, user=user, error_message="Account deactivated")
                return None

            # Check account lockout
            if user.is_locked_out():
                log_login_attempt(success=False, user=user, error_message="Account locked due to too many failed attempts")
                return None

            if not user.check_password(password):
                user.record_failed_login()
                remaining = AuthService.MAX_FAILED_ATTEMPTS - user.failed_login_attempts
                log_login_attempt(success=False, user=user, error_message=f"Invalid password ({remaining} attempts remaining)")
                return None

            # Reset failed attempts on successful login
            user.reset_failed_login()
            log_login_attempt(success=True, user=user)
            return user

        except Exception as e:
            current_app.logger.error(f"Authentication error: {str(e)}")
            log_login_attempt(success=False, error_message="Authentication error")
            return None
    
    @staticmethod
    def create_user_session(user):
        """
        Create user session and JWT tokens.
        Enforces concurrent session limit.
        Returns dict with tokens and user info.
        """
        try:
            # Update user's last login
            user.update_last_login()

            # Enforce concurrent session limit — evict oldest sessions
            active_sessions = UserSession.get_user_sessions(user.id, active_only=True)
            if len(active_sessions) >= AuthService.MAX_SESSIONS_PER_USER:
                # Sort by login_time ascending and logout the oldest
                active_sessions.sort(key=lambda s: s.login_time)
                sessions_to_evict = active_sessions[:len(active_sessions) - AuthService.MAX_SESSIONS_PER_USER + 1]
                for old_session in sessions_to_evict:
                    old_session.logout()

            # Create session record
            session_token = str(uuid.uuid4())
            ip_address = get_client_ip()
            user_agent = request.headers.get('User-Agent', '')

            session = UserSession(
                user_id=user.id,
                session_token=session_token,
                ip_address=ip_address,
                user_agent=user_agent
            )
            session.save()

            # Fetch role data from the tenant (school) DB
            role_data = None
            academic_years_data = []
            current_academic_year = None

            if user.skid:
                with switch_to_school_db(user.skid) as school_session:
                    user_role = (
                        school_session.query(Role)
                        .join(UserRoles, UserRoles.role_id == Role.id)
                        .filter(UserRoles.user_id == user.school_user_id)
                        .first()
                    )

                    if user_role:
                        role_data = {
                            "id": user_role.id,
                            "role_name": user_role.role_name,
                            "role_code": user_role.role_code,
                            "school_id": user_role.school_id,
                            "is_active": user_role.is_active,
                            "is_system_role": user_role.is_system_role,
                            "permissions": user_role.permissions
                        }

                    # Fetch academic years
                    academic_years = (
                        school_session.query(AcademicYear)
                        .filter(AcademicYear.is_active == True)
                        .order_by(AcademicYear.start_date.desc())
                        .all()
                    )

                    for year in academic_years:
                        year_dict = {
                            "id": year.id,
                            "year_name": year.year_name,
                            "start_date": year.start_date.isoformat(),
                            "end_date": year.end_date.isoformat(),
                            "is_current": year.is_current,
                            "is_active": year.is_active
                        }
                        academic_years_data.append(year_dict)

                        # Set current academic year
                        if year.is_current:
                            current_academic_year = year_dict

            # Create JWT tokens with session_token in claims
            additional_claims = {
                'session_token': session_token
            }

            access_token = create_access_token(
                identity=str(user.id),
                additional_claims=additional_claims
            )

            refresh_token = create_refresh_token(
                identity=str(user.id),
                additional_claims=additional_claims
            )

            return {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user': {
                    **user.to_dict(),
                    'role_obj': role_data,
                    'academic_years': academic_years_data,
                    'current_academic_year': current_academic_year,
                },
                'session_id': session.id
            }

        except Exception as e:
            current_app.logger.error(f"Failed to create session: {str(e)}")
            raise Exception("Failed to create session")
    
    @staticmethod
    def logout_user(user, session_token=None):
        """
        Logout user and invalidate session.
        If session_token provided, logout that specific session.
        Otherwise, logout all active sessions for the user.
        """
        try:
            if session_token:
                session = UserSession.get_active_session(session_token)
                if session and session.user_id == user.id:
                    session.logout()
            else:
                # Logout all active sessions for user
                active_sessions = UserSession.get_user_sessions(user.id, active_only=True)
                for session in active_sessions:
                    session.logout()

            log_logout(user)
            return True

        except Exception as e:
            current_app.logger.error(f"Failed to logout user {user.id}: {str(e)}")
            raise Exception("Failed to logout")

    @staticmethod
    def refresh_token(user_id, old_session_token=None):
        """
        Create new access token from refresh token.
        Rotates the session token for security (refresh token rotation).
        """
        try:
            user = User.get_by_id(user_id)
            if not user or not user.is_active:
                return None

            # Check if user is locked out
            if user.is_locked_out():
                return None

            # Validate and rotate the session
            new_session_token = old_session_token
            new_refresh_token = None

            if old_session_token:
                old_session = UserSession.get_active_session(old_session_token)
                if not old_session or old_session.user_id != user.id:
                    # Session invalid or doesn't belong to user — reject
                    return None

                # Rotate: invalidate old session, create new one
                old_session.logout()

                new_session_token = str(uuid.uuid4())
                ip_address = get_client_ip()
                user_agent = request.headers.get('User-Agent', '')

                new_session = UserSession(
                    user_id=user.id,
                    session_token=new_session_token,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                new_session.save()

            additional_claims = {
                'session_token': new_session_token
            }

            access_token = create_access_token(
                identity=str(user.id),
                additional_claims=additional_claims
            )

            # Issue new refresh token with rotated session
            new_refresh_token = create_refresh_token(
                identity=str(user.id),
                additional_claims=additional_claims
            )

            result = {
                'access_token': access_token,
                'user': user.to_dict()
            }

            if new_refresh_token:
                result['refresh_token'] = new_refresh_token

            return result

        except Exception as e:
            current_app.logger.error(f"Failed to refresh token: {str(e)}")
            raise Exception("Failed to refresh token")

    # Fields a user is allowed to update on their own profile.
    # NOT included (and never editable via this path):
    #   - email, username (login identity)
    #   - role, school_id, is_active, plan, password_hash
    SELF_EDITABLE_FIELDS = ('first_name', 'last_name', 'phone')

    @staticmethod
    def update_profile(user, data):
        """
        Update the current user's own profile.
        Only whitelisted fields are accepted; everything else is silently ignored.
        Returns the updated user dict.
        """
        from app import db

        if not isinstance(data, dict):
            raise ValueError('Invalid payload')

        changed = False
        for field in AuthService.SELF_EDITABLE_FIELDS:
            if field in data:
                value = data[field]
                if isinstance(value, str):
                    value = value.strip()
                # Required string fields cannot be cleared
                if field in ('first_name', 'last_name') and not value:
                    raise ValueError(f'{field.replace("_", " ").title()} cannot be empty')
                if getattr(user, field) != value:
                    setattr(user, field, value)
                    changed = True

        if changed:
            db.session.commit()

        return user.to_dict()

    @staticmethod
    def cleanup_expired_sessions(days_old=30):
        """
        Remove sessions older than specified days.
        Should be called periodically (e.g., via a scheduled task).
        """
        try:
            from app import db
            cutoff = datetime.utcnow() - timedelta(days=days_old)
            expired = UserSession.query.filter(
                UserSession.login_time < cutoff,
                UserSession.is_logged_out == True
            ).all()
            count = len(expired)
            for session in expired:
                db.session.delete(session)
            db.session.commit()
            return count
        except Exception as e:
            current_app.logger.error(f"Failed to cleanup sessions: {str(e)}")
            return 0