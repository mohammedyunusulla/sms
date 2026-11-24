from flask import Blueprint, request, jsonify
from app.services.userRole_service import UserRolesService
from app.decorators import login_required

user_roles_bp  = Blueprint('user-roles', __name__)

# 1. CREATE USER-ROLE
@user_roles_bp.route('/assign-role/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN'], full_access_only=True)
def assign_role_to_user(skid):
    try:
        data = request.get_json()
        if not skid:
            raise ValueError("Institution ID (skid) is required")
        
        role = UserRolesService.assign_role_to_user(data or {}, skid)
        return jsonify({'message': role['message'], 'data': role, 'status': 'success', 'code':200}), 200
    except ValueError as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error'}), 500