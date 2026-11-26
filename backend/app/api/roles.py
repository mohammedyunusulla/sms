from flask import Blueprint, request, jsonify
from app.services.roles_service import RolesService
from app.decorators import login_required

roles_bp = Blueprint('roles', __name__)

# 1. CREATE ROLE
@roles_bp.route('/create/role/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN'], permission='manage_roles')
def create_role(skid):
    # New custom roles are no longer made: institutions use the built-in roles (sign-in is switched per
    # built-in role - app/utils/features.py). Existing custom roles keep working and can be edited.
    return jsonify({'message': 'New custom roles can no longer be created. Use the built-in roles.',
                    'code': 'CUSTOM_ROLES_CLOSED'}), 403


@roles_bp.route('/list/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN', 'PRINCIPAL'], permission='manage_roles')
def get_all_roles_paginated(skid):
    """
    Get paginated list of roles in the specific institution with filtering and sorting
    Query Parameters:
    - page: Page number (default: 1)
    - limit: Items per page (default: 10)
    - search: Search term for role name
    - status: Filter by status (active, inactive)
    """
    try:
        if not skid:
            raise ValueError("Institution ID (skid) is required")

        # Get query parameters
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        search = request.args.get('search', '', type=str)
        status = request.args.get('status', '', type=str)

        # Validate pagination parameters
        page = max(1, page)
        limit = max(1, min(limit, 100))  # Limit max 100 items per page

        # Get roles with pagination and filters
        result = RolesService.get_all_roles_paginated(
            skid=skid,
            page=page,
            limit=limit,
            search=search,
            status=status
        )

        return jsonify({
            'data': result['data'],
            'meta': result['meta'],
            'status': 'success',
            'code': 200
        }), 200

    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error'}), 500


# 3. GET SINGLE ROLE BY ID
@roles_bp.route('/role/<skid>/<int:role_id>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN'], permission='manage_roles')
def get_role_by_id(skid, role_id):
    try:
        if not skid:
            raise ValueError("Institution ID (skid) is required")
        role = RolesService.get_role_by_id(role_id, skid)
        
        return jsonify({'data': role, 'status': 'success', 'code':200}), 200
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error'}), 500


# 4. UPDATE ROLE
@roles_bp.route('/update/role/<skid>/<int:role_id>', methods=['PUT'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN'], permission='manage_roles')
def update_role(skid, role_id):
    try:
        data = request.get_json()
        if not skid:
            raise ValueError("Institution ID (skid) is required")
            
        updated_role = RolesService.update_role(role_id, data, skid)
        return jsonify({'message': 'Role updated', 'data': updated_role, 'status': 'success', 'code':200}), 200
    except ValueError as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error'}), 500


# 5. ASSIGN PERMISSIONS TO ROLE
@roles_bp.route('/addPermissionsToRole/<skid>/<int:role_id>', methods=['PUT'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN'], permission='manage_roles')
def assign_permissions(skid, role_id):
    try:
        data = request.get_json()
        permissions = data.get('permissions', [])
        if not skid:
            raise ValueError("Institution ID (skid) is required")
            
        updated = RolesService.assign_permissions(skid, role_id, permissions)
        return jsonify({'message': 'Permissions updated', 'data': updated, 'status': 'success', 'code':200}), 200
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error'}), 500


# 6. TOGGLE ACTIVE/INACTIVE
@roles_bp.route('/toggleRole/<skid>/<int:role_id>', methods=['PATCH'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN'], permission='manage_roles')
def toggle_role_status(skid, role_id):
    try:
        if not skid:
            raise ValueError("Institution ID (skid) is required")
            
        updated = RolesService.toggle_role_status(role_id, skid)
        return jsonify({'message': 'Role status updated', 'data': updated, 'status': 'success', 'code':200}), 200
    except ValueError as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error'}), 500


# 7. DELETE ROLE
@roles_bp.route('/delete/role/<skid>/<int:role_id>', methods=['DELETE'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN'], permission='manage_roles')
def delete_role(skid, role_id):
    try:
        if not skid:
            raise ValueError("Institution ID (skid) is required")
        
        RolesService.delete_role(role_id, skid)
        return jsonify({'message': 'Role deleted', 'status': 'success', 'code':200}), 200
    except ValueError as e:
        code = 404 if 'not found' in str(e).lower() else 400
        return jsonify({'message': str(e), 'status': 'error', 'code': code}), code
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error'}), 500
