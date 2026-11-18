from flask import Blueprint, request, jsonify
from app.services import UserService
from app.decorators import log_actions, login_required, super_admin_required, school_admin_required, same_school_required
from app.models.main.User import UserRole

user_bp = Blueprint('users', __name__)

@user_bp.route('/create', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
@log_actions('CREATE_USER')
def create_school_admin():
    """
    Create a new school sadmin
    Only super admin
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'message': 'No data provided'}), 400
        
        user = UserService.create_school_admin(data)
        
        return jsonify({
            'message': 'User created successfully',
            'user': user.to_dict(),
            'status': 'success',
            'code': 200
        }), 200
        
    except ValueError as e:
        return jsonify({'message': str(e)}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to create user: {str(e)}'}), 500

@user_bp.route('/update/<int:user_id>', methods=['PUT'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
@log_actions('UPDATE_USER')
def update_user(user_id):
    """
    Update user information
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'message': 'No data provided'}), 400
        
        current_user = request.current_user
        
        # Get the user to be updated
        target_user = UserService.get_user_by_id(user_id, include_inactive=True)
        if not target_user:
            return jsonify({'message': 'User not found'}), 404
        
        # Validate permissions
        if current_user.role == UserRole.SCHOOL_ADMIN:
            # School admin can only update users from their own school
            if target_user.school_id != current_user.school_id:
                return jsonify({'message': 'Cannot update user from different school'}), 403
            
            # School admin cannot update super admin or other school admins
            if target_user.role in [UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN]:
                return jsonify({'message': 'Insufficient permissions to update this user'}), 403
            
            # School admin cannot assign super admin or school admin roles
            if data.get('role') in ['super_admin', 'school_admin']:
                return jsonify({'message': 'Insufficient permissions to assign this role'}), 403
            
            # Force school_id to current user's school if provided
            if 'school_id' in data:
                data['school_id'] = current_user.school_id
        
        # Update user using service
        user = UserService.update_user(user_id, data)
        
        return jsonify({
            'message': 'User updated successfully',
            'user': user.to_dict()
        }), 200
        
    except ValueError as e:
        return jsonify({'message': str(e)}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to update user: {str(e)}'}), 500

@user_bp.route('/<int:user_id>/deactivate', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
@log_actions('DEACTIVATE_USER')
def deactivate_user(user_id):
    """
    Deactivate user (set status as Inactive)
    """
    try:
        current_user = request.current_user
        
        # Get the user to be deactivated
        target_user = UserService.get_user_by_id(user_id, include_inactive=True)
        if not target_user:
            return jsonify({'message': 'User not found'}), 404
        
        # Validate permissions
        if current_user.role == UserRole.SCHOOL_ADMIN:
            # School admin can only deactivate users from their own school
            if target_user.school_id != current_user.school_id:
                return jsonify({'message': 'Cannot deactivate user from different school'}), 403
            
            # School admin cannot deactivate super admin or other school admins
            if target_user.role in [UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN]:
                return jsonify({'message': 'Insufficient permissions to deactivate this user'}), 403
        
        # Prevent self-deactivation
        if current_user.id == user_id:
            return jsonify({'message': 'Cannot deactivate your own account'}), 400
        
        # Deactivate user using service
        user = UserService.deactivate_user(user_id)
        
        return jsonify({
            'message': 'User deactivated successfully',
            'user': user.to_dict(),
            'status': 'success',
            'code': 200
        }), 200
        
    except ValueError as e:
        return jsonify({'message': str(e)}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to deactivate user: {str(e)}'}), 500

@user_bp.route('/<int:user_id>/activate', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
@log_actions('ACTIVATE_USER')
def activate_user(user_id):
    """
    Activate user (set status as Active)
    """
    try:
        current_user = request.current_user
        
        # Get the user to be activated
        target_user = UserService.get_user_by_id(user_id, include_inactive=True)
        if not target_user:
            return jsonify({'message': 'User not found'}), 404
        
        # Validate permissions
        if current_user.role == UserRole.SCHOOL_ADMIN:
            # School admin can only activate users from their own school
            if target_user.school_id != current_user.school_id:
                return jsonify({'message': 'Cannot activate user from different school'}), 403
            
            # School admin cannot activate super admin or other school admins
            if target_user.role in [UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN]:
                return jsonify({'message': 'Insufficient permissions to activate this user'}), 403
        
        # Activate user using service
        user = UserService.activate_user(user_id)
        
        return jsonify({
            'message': 'User activated successfully',
            'user': user.to_dict(),
            'status': 'success',
            'code': 200
        }), 200
        
    except ValueError as e:
        return jsonify({'message': str(e)}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to activate user: {str(e)}'}), 500

@user_bp.route('/super-admins', methods=['GET'])
@login_required(['SUPER_ADMIN'])
@log_actions('GET_SUPER_ADMINS')
def get_super_admins():
    """
    Get list of all super admin users
    """
    try:
        admins = UserService.get_super_admins()
        return jsonify({
            'data': admins,
            'status': 'success',
            'code': 200
        }), 200
    except Exception as e:
        return jsonify({'message': f'Failed to get super admins: {str(e)}'}), 500

@user_bp.route('/create-super-admin', methods=['POST'])
@login_required(['SUPER_ADMIN'])
@log_actions('CREATE_SUPER_ADMIN')
def create_super_admin():
    """
    Create a new super admin user
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No data provided'}), 400

        admin = UserService.create_super_admin(data)

        return jsonify({
            'message': 'System admin created successfully',
            'user': admin.to_dict(),
            'status': 'success',
            'code': 200
        }), 200

    except ValueError as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to create super admin: {str(e)}'}), 500

@user_bp.route('/list/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER'])
@log_actions('GET_USERS')
def get_school_users(skid):
    """
    Get paginated list of users in the specific school with filtering and sorting
    Query Parameters:
    - page: Page number (default: 1)
    - limit: Items per page (default: 10)
    - search: Search term for name, email, phone
    - gender: Filter by gender (Male, Female, Other)
    - role: Filter by role (super_admin, school_admin, principal, teacher, student, parent)
    - status: Filter by status (active, inactive)
    """
    try:
        if not skid:
            raise ValueError("School ID (skid) is required")

        # Get query parameters
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        search = request.args.get('search', '', type=str)
        gender = request.args.get('gender', '', type=str)
        role = request.args.get('role', '', type=str)
        status = request.args.get('status', '', type=str)

        # Validate pagination parameters
        page = max(1, page)
        limit = max(1, min(limit, 100))  # Limit max 100 items per page

        # Get users with pagination and filters
        result = UserService.get_users_by_school(
            skid=skid,
            page=page,
            limit=limit,
            search=search,
            gender=gender,
            role=role,
            status=status
        )

        return jsonify({
            'data': result['users'],
            'meta': {
                'total': result['total'],
                'page': result['page'],
                'limit': result['limit'],
                'totalPages': result['totalPages']
            },
            'status': 'success',
            'code': 200
        }), 200

    except Exception as e:
        return jsonify({'message': f'Failed to get users: {str(e)}'}), 500


@user_bp.route('/list/staff/<skid>', methods=['GET'])
@login_required(['SCHOOL_ADMIN'])
@log_actions('GET_STAFF')
def get_school_staff(skid):
    """
    Get list of staff in the specific school
    """
    try:
        if not skid:
            raise ValueError("School ID (skid) is required")

        staff = UserService.get_staff_by_school(skid)
        
        return jsonify({
            'staff': staff,
            'status': 'success',
            'code': 200
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to get users: {str(e)}'}), 500


@user_bp.route('/schoolAdmin/<skid>/<int:user_id>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
@log_actions('GET_USER')
def get_user(skid, user_id):
    """
    Get specific user information
    """
    try:
        print("coming here----")
        current_user = request.current_user
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        
        # Get user
        user = UserService.get_user_by_id(user_id, include_inactive)
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        # Validate permissions
        if current_user.role == UserRole.SCHOOL_ADMIN:
            # School admin can only view users from their own school
            if user.school_id != current_user.school_id:
                return jsonify({'message': 'Cannot view user from different school'}), 403
        
        return jsonify({
            'user': user.to_dict(),
            'status': 'success',
            'code': 200
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to get user: {str(e)}'}), 500


@user_bp.route('/provision-login', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
@log_actions('PROVISION_LOGIN')
def provision_login():
    """
    Create login access for a single school user (STUDENT/PARENT).
    Body: { school_user_id, skid, school_id, password }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No data provided'}), 400

        required = ['school_user_id', 'skid', 'school_id', 'password']
        for field in required:
            if not data.get(field):
                return jsonify({'message': f'Missing required field: {field}'}), 400

        current_user = request.current_user
        # School admin can only provision for their own school
        if current_user.role == UserRole.SCHOOL_ADMIN:
            if data['school_id'] != current_user.school_id:
                return jsonify({'message': 'Cannot provision login for different school'}), 403

        user = UserService.provision_single_login(
            school_user_id=data['school_user_id'],
            skid=data['skid'],
            school_id=data['school_id'],
            password=data['password']
        )

        return jsonify({
            'message': 'Login created successfully',
            'user': user.to_dict(),
            'status': 'success',
            'code': 200
        }), 200

    except ValueError as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to provision login: {str(e)}'}), 500


@user_bp.route('/provision-bulk-logins', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
@log_actions('PROVISION_BULK_LOGINS')
def provision_bulk_logins():
    """
    Bulk create login access for STUDENT/PARENT users in a school.
    Body: { skid, school_id, default_password, role_filter? }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No data provided'}), 400

        required = ['skid', 'school_id', 'default_password']
        for field in required:
            if not data.get(field):
                return jsonify({'message': f'Missing required field: {field}'}), 400

        current_user = request.current_user
        if current_user.role == UserRole.SCHOOL_ADMIN:
            if data['school_id'] != current_user.school_id:
                return jsonify({'message': 'Cannot provision logins for different school'}), 403

        result = UserService.provision_bulk_logins(
            skid=data['skid'],
            school_id=data['school_id'],
            default_password=data['default_password'],
            role_filter=data.get('role_filter')
        )

        return jsonify({
            'message': 'Bulk login provisioning completed',
            'data': result,
            'status': 'success',
            'code': 200
        }), 200

    except ValueError as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to provision bulk logins: {str(e)}'}), 500


@user_bp.route('/provisioning-report/<skid>/<int:school_id>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
@log_actions('GET_PROVISIONING_REPORT')
def get_provisioning_report(skid, school_id):
    """
    Get report of all users in a school with their login status.
    Used for export after provisioning.
    """
    try:
        current_user = request.current_user
        if current_user.role == UserRole.SCHOOL_ADMIN:
            if school_id != current_user.school_id:
                return jsonify({'message': 'Cannot view report for different school'}), 403

        result = UserService.get_provisioning_report(skid=skid, school_id=school_id)

        return jsonify({
            'data': result,
            'status': 'success',
            'code': 200
        }), 200

    except ValueError as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to get provisioning report: {str(e)}'}), 500

