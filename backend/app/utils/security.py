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
    """
    # Same rule as everywhere else (app.utils.helpers.validate_password); a special character is no
    # longer required only here, so changing your own password follows the rule used to create it.
    from app.utils.helpers import validate_password
    ok, message = validate_password(password)
    return (True, None) if ok else (False, message)


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
