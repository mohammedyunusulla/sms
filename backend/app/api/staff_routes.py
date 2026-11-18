from flask import Blueprint, request, jsonify
from app.decorators.auth import login_required
from app.services.staff_service import StaffService

staff_bp = Blueprint('staff', __name__)


@staff_bp.route('/create/<skid>', methods=['POST'])
@login_required(allowed_roles=['SCHOOL_ADMIN', 'PRINCIPAL'])
def create_staff(skid):
    """Create a new staff member (PRINCIPAL, BUS_STAFF)."""
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No data provided'}), 400

    user = StaffService.create_staff(data, skid)
    return jsonify({
        'message': 'Staff member created successfully',
        'user': user.to_dict(),
        'status': 'success',
        'code': 200,
    }), 200


@staff_bp.route('/list/<skid>', methods=['GET'])
@login_required(allowed_roles=['SCHOOL_ADMIN', 'PRINCIPAL'])
def list_staff(skid):
    """List all active staff for a school."""
    staff = StaffService.get_staff_list(skid)
    return jsonify({
        'data': staff,
        'total': len(staff),
        'status': 'success',
        'code': 200,
    }), 200
