from functools import wraps
from flask import request, current_app, g
from datetime import datetime
import json

def log_actions(action_type=None):
    """
    Decorator to log user actions
    Usage: @log_actions('USER_LOGIN')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = datetime.utcnow()
            
            # Get user info if available
            user = getattr(request, 'current_user', None)
            user_id = user.id if user else None
            username = user.username if user else 'Anonymous'
            
            # Get request info
            from app.utils.security import get_client_ip
            ip_address = get_client_ip()
            user_agent = request.headers.get('User-Agent', '')
            method = request.method
            endpoint = request.endpoint
            url = request.url
            
            # Log request
            log_data = {
                'timestamp': start_time.isoformat(),
                'action_type': action_type or f"{method}_{endpoint}",
                'user_id': user_id,
                'username': username,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'method': method,
                'endpoint': endpoint,
                'url': url,
                'request_data': {}
            }
            
            # Log request data (excluding sensitive fields)
            if request.is_json and request.json:
                filtered_data = {k: v for k, v in request.json.items() 
                               if k not in ['password', 'password_hash', 'token']}
                log_data['request_data'] = filtered_data
            elif request.form:
                filtered_data = {k: v for k, v in request.form.items() 
                               if k not in ['password', 'password_hash', 'token']}
                log_data['request_data'] = filtered_data
            
            try:
                # Execute the function
                result = f(*args, **kwargs)
                
                # Log successful completion
                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()
                
                log_data.update({
                    'status': 'SUCCESS',
                    'duration_seconds': duration,
                    'completed_at': end_time.isoformat()
                })
                
                current_app.logger.info(f"ACTION: {json.dumps(log_data)}")
                
                return result
                
            except Exception as e:
                # Log error
                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()
                
                log_data.update({
                    'status': 'ERROR',
                    'error': str(e),
                    'duration_seconds': duration,
                    'completed_at': end_time.isoformat()
                })
                
                current_app.logger.error(f"ACTION_ERROR: {json.dumps(log_data)}")
                raise
        
        return decorated_function
    return decorator

def log_login_attempt(success=True, user=None, error_message=None):
    """Helper function to log login attempts"""
    from app.utils.security import get_client_ip
    ip_address = get_client_ip()
    user_agent = request.headers.get('User-Agent', '')

    # Safely get identifier from request
    identifier = 'Unknown'
    if user:
        identifier = user.username
    elif request.is_json and request.json:
        identifier = request.json.get('identifier', 'Unknown')

    log_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'action_type': 'LOGIN_ATTEMPT',
        'success': success,
        'ip_address': ip_address,
        'user_agent': user_agent,
        'user_id': user.id if user else None,
        'username': identifier
    }

    if not success and error_message:
        log_data['error'] = error_message

    if success:
        current_app.logger.info(f"LOGIN_SUCCESS: {json.dumps(log_data)}")
    else:
        current_app.logger.warning(f"LOGIN_FAILED: {json.dumps(log_data)}")

def log_logout(user):
    """Helper function to log logout"""
    from app.utils.security import get_client_ip
    ip_address = get_client_ip()
    
    log_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'action_type': 'LOGOUT',
        'user_id': user.id,
        'username': user.username,
        'ip_address': ip_address
    }
    
    current_app.logger.info(f"LOGOUT: {json.dumps(log_data)}")