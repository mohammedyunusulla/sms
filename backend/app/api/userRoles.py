from flask import Blueprint, request, jsonify
from app.services.userRole_service import UserRolesService
from app.decorators import login_required

user_roles_bp  = Blueprint('user-roles', __name__)

# 1. CREATE USER-ROLE
@user_roles_bp.route('/assign-role/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
def assign_role_to_user(skid):
    try:
        data = request.get_json()
        if not skid:
            raise ValueError("School ID (skid) is required")
        
        role = UserRolesService.assign_role_to_user(data, skid)
        return jsonify({'message': 'Role created', 'data': role, 'status': 'success', 'code':200}), 200
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error'}), 500