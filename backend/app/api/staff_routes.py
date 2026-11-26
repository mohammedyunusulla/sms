from flask import Blueprint, request, jsonify
from app.decorators.auth import login_required
from app.services.staff_service import StaffService

staff_bp = Blueprint('staff', __name__)


@staff_bp.route('/create/<skid>', methods=['POST'])
@login_required(allowed_roles=['INSTITUTION_ADMIN', 'PRINCIPAL'], permission='manage_users')
def create_staff(skid):
    """Create a new staff member (PRINCIPAL, BUS_STAFF)."""
    from app.utils.form_input import clean_payload, missing_fields_message, error
    from app.utils.helpers import validate_password
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No data provided'}), 400

    data = clean_payload(data, ('phone', 'gender', 'date_of_birth', 'address', 'employee_id', 'designation', 'salary'))
    missing = missing_fields_message(data, (('first_name', 'First name'), ('last_name', 'Last name'), ('username', 'Username'),
                                            ('email', 'Email'), ('role', 'Role')))
    if missing:
        return error(missing, 400)
    # A password only where the person gets a login (StaffService checks the role's sign-in switch)
    if data.get('password'):
        ok, password_error = validate_password(data['password'])
        if not ok:
            return error(password_error, 400)

    # Errors used to escape as an HTML 500 without CORS headers (the browser showed "Network Error")
    try:
        user = StaffService.create_staff(data, skid)
    except ValueError as e:
        message = str(e)
        return error(message, 409 if 'already exists' in message.lower() else 400)
    except Exception as e:
        return error(f'Failed to create staff member: {e}', 500)
    return jsonify({
        'message': 'Staff member created successfully',
        'user': user,
        'status': 'success',
        'code': 200,
    }), 200


@staff_bp.route('/list/<skid>', methods=['GET'])
@login_required(allowed_roles=['INSTITUTION_ADMIN', 'PRINCIPAL'], permission=('view_users', 'manage_users'))
def list_staff(skid):
    """List all active staff for an institution."""
    staff = StaffService.get_staff_list(skid)
    return jsonify({
        'data': staff,
        'total': len(staff),
        'status': 'success',
        'code': 200,
    }), 200
