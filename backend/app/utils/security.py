"""
Security utilities for authentication and authorization.
"""
import re
from flask import request, current_app


def validate_password_strength(password):
    """
    Validate password meets minimum security requirements.
    Returns (is_valid, error_message).

    Requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if len(password) > 128:
        return False, "Password must not exceed 128 characters"

    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"

    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"

    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"

    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/~`]', password):
        return False, "Password must contain at least one special character"

    return True, None


def get_client_ip():
    """
    Get the client's real IP address safely.
    Only trusts X-Forwarded-For when TRUSTED_PROXY is configured.
    In production behind a reverse proxy, set TRUSTED_PROXY=true in .env.
    """
    trust_proxy = current_app.config.get('TRUSTED_PROXY', False)

    if trust_proxy:
        # Take the first (client) IP from X-Forwarded-For if behind trusted proxy
        forwarded_for = request.environ.get('HTTP_X_FORWARDED_FOR', '')
        if forwarded_for:
            # X-Forwarded-For: client, proxy1, proxy2 — take the leftmost
            return forwarded_for.split(',')[0].strip()

    return request.environ.get('REMOTE_ADDR', '0.0.0.0')


def sanitize_error_message(error):
    """
    Return a generic error message for client responses.
    Log the actual error internally.
    """
    current_app.logger.error(f"Internal error: {str(error)}")
    return "An internal error occurred. Please try again later."
