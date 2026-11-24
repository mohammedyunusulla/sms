import re
import secrets
import string
from datetime import datetime, timedelta
from flask import jsonify

def generate_institution_code(institution_name):
    """
    Generate a unique institution code from institution name
    """
    # Remove special characters and spaces, take first 3 letters
    clean_name = re.sub(r'[^A-Za-z0-9]', '', institution_name).upper()
    prefix = clean_name[:3] if len(clean_name) >= 3 else clean_name.ljust(3, 'X')
    
    # Add random suffix
    suffix = ''.join(secrets.choice(string.digits) for _ in range(3))
    
    return f"{prefix}{suffix}"

def validate_email(email):
    """
    Validate email format
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    """
    Validate phone number format
    """
    if not phone:
        return True  # Phone is optional
    
    # Remove all non-digit characters
    digits = re.sub(r'[^\d]', '', phone)
    
    # Check if it has 10-15 digits
    return 10 <= len(digits) <= 15

def validate_password(password):
    """
    Validate password strength
    Returns tuple (is_valid, error_message)
    """
    # The one password rule for every account (create, reset, change your own, bulk logins).
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if len(password) > 128:
        return False, "Password must not exceed 128 characters"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one digit"
    
    return True, "Password is valid"

def sanitize_input(input_string):
    """
    Sanitize input string to prevent basic injection attacks
    """
    if not isinstance(input_string, str):
        return input_string
    
    # Remove potential SQL injection characters
    dangerous_chars = ["'", '"', ';', '--', '/*', '*/', 'xp_', 'sp_']
    
    for char in dangerous_chars:
        input_string = input_string.replace(char, '')
    
    return input_string.strip()

def create_response(data=None, message=None, status_code=200, errors=None):
    """
    Create standardized API response
    """
    response = {}
    
    if message:
        response['message'] = message
    
    if data is not None:
        response['data'] = data
    
    if errors:
        response['errors'] = errors
    
    response['timestamp'] = datetime.utcnow().isoformat()
    response['status'] = 'success' if status_code < 400 else 'error'
    
    return jsonify(response), status_code

def paginate_query(query, page=1, per_page=20, max_per_page=100):
    """
    Paginate SQLAlchemy query
    """
    # Ensure per_page doesn't exceed maximum
    per_page = min(per_page, max_per_page)
    
    # Calculate offset
    offset = (page - 1) * per_page
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    items = query.offset(offset).limit(per_page).all()
    
    # Calculate pagination info
    total_pages = (total + per_page - 1) // per_page
    has_prev = page > 1
    has_next = page < total_pages
    
    return {
        'items': items,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': total_pages,
            'has_prev': has_prev,
            'has_next': has_next,
            'prev_page': page - 1 if has_prev else None,
            'next_page': page + 1 if has_next else None
        }
    }

def format_datetime(dt, format_string='%Y-%m-%d %H:%M:%S'):
    """
    Format datetime object to string
    """
    if dt is None:
        return None
    
    if isinstance(dt, datetime):
        return dt.strftime(format_string)
    
    return str(dt)

def parse_datetime(date_string, format_string='%Y-%m-%d %H:%M:%S'):
    """
    Parse string to datetime object
    """
    if not date_string:
        return None
    
    try:
        return datetime.strptime(date_string, format_string)
    except ValueError:
        # Try ISO format
        try:
            return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        except ValueError:
            return None

def calculate_age(birth_date):
    """
    Calculate age from birth date
    """
    if not birth_date:
        return None
    
    today = datetime.now().date()
    if isinstance(birth_date, datetime):
        birth_date = birth_date.date()
    
    age = today.year - birth_date.year
    
    # Adjust if birthday hasn't occurred this year
    if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
        age -= 1
    
    return age

def generate_random_string(length=8, include_digits=True, include_uppercase=True, include_lowercase=True):
    """
    Generate random string for passwords, tokens, etc.
    """
    characters = ""
    
    if include_lowercase:
        characters += string.ascii_lowercase
    
    if include_uppercase:
        characters += string.ascii_uppercase
    
    if include_digits:
        characters += string.digits
    
    if not characters:
        characters = string.ascii_letters + string.digits
    
    return ''.join(secrets.choice(characters) for _ in range(length))

def mask_sensitive_data(data, sensitive_fields=None):
    """
    Mask sensitive data in dictionary for logging
    """
    if sensitive_fields is None:
        sensitive_fields = ['password', 'password_hash', 'token', 'secret', 'key']
    
    if isinstance(data, dict):
        masked_data = {}
        for key, value in data.items():
            if any(field in key.lower() for field in sensitive_fields):
                masked_data[key] = "***MASKED***"
            elif isinstance(value, dict):
                masked_data[key] = mask_sensitive_data(value, sensitive_fields)
            elif isinstance(value, list):
                masked_data[key] = [mask_sensitive_data(item, sensitive_fields) if isinstance(item, dict) else item for item in value]
            else:
                masked_data[key] = value
        return masked_data
    
    return data


def generate_student_id(institution_code):
    import random
    year = datetime.now().year
    random_number = random.randint(100000, 999999)
    return f"{institution_code.upper()}-{year}-{random_number}"
