from flask import Blueprint, request, jsonify
from app.decorators.auth import login_required
from app.decorators.logging import log_actions
from app.services.school_service import SchoolService
from app.models.main.User import UserRole
from app.models.main.School import School
import logging

logger = logging.getLogger(__name__)

school_bp = Blueprint('school', __name__)

@school_bp.route('/create', methods=['POST'])
@login_required(['SUPER_ADMIN'])
@log_actions('CREATE_SCHOOL')
def create_school():
    """Create a new school with database and initialize using models"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'message': 'No data provided'}), 400
        
        # Check if school with same code exists
        existing_school = School.query.filter_by(code=data.get('code')).first()
        if existing_school:
            return jsonify({
                'message': f"School with code '{data['code']}' already exists.",
                'status': 'error',
                'code': 409
            }), 200
        
        # Create school
        result = SchoolService.create_school(data)
        
        if result['success']:
            return jsonify({
                'message': result['message'],
                'school': result['data'],
                'status': 'success',
                'code': 200
            }), 200
        else:
            return jsonify({'message': result['message']}), 400
            
    except Exception as e:
        logger.error(f"Error creating school: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500


@school_bp.route('/update/<int:school_id>', methods=['PUT'])
@login_required(['SUPER_ADMIN'])
@log_actions('UPDATE_SCHOOL')
def update_school(school_id):
    """Update school"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'message': 'No data provided'}), 400
            
        result = SchoolService.update_school(school_id, data)
        
        if result['success']:
            return jsonify({
                'message': result['message'],
                'school': result['data'],
                'status': 'success',
                'code': 200
            }), 200
        else:
            status_code = 404 if 'not found' in result['message'].lower() else 400
            return jsonify({'message': result['message']}), status_code
            
    except Exception as e:
        logger.error(f"Error updating school {school_id}: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500


@school_bp.route('/list', methods=['GET'])
@login_required(['SUPER_ADMIN'])
@log_actions('GET_SCHOOLS')
def get_schools():
    """Get list of schools"""
    try:
        
        result = SchoolService.get_schools()
        
        if result['success']:
            return jsonify({
                'message': 'Schools retrieved successfully',
                'data': result['data'],
                'status': 'success',
                'code': 200
            }), 200
        else:
            return jsonify({'message': result['message']}), 400
        
    except Exception as e:
        logger.error(f"Error getting schools: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500


@school_bp.route('/dashboard/stats', methods=['GET'])
@login_required(['SUPER_ADMIN'])
@log_actions('GET_SUPER_ADMIN_DASHBOARD')
def get_super_admin_dashboard():
    """Get system-wide dashboard stats for super admin"""
    try:
        result = SchoolService.get_super_admin_dashboard_stats()

        if result['success']:
            return jsonify({
                'data': result['data'],
                'status': 'success',
                'code': 200
            }), 200
        else:
            return jsonify({
                'message': result.get('message', 'Failed to get dashboard stats'),
                'status': 'error',
                'code': 500
            }), 500

    except Exception as e:
        logger.error(f"Error getting super admin dashboard: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500


@school_bp.route('/<int:school_id>', methods=['GET'])
@login_required(['SUPER_ADMIN'])
@log_actions('GET_SCHOOL')
def get_school(school_id):
    """Get school by ID"""
    try:
        result = SchoolService.get_school_by_id(school_id)
        
        if result['success']:
            return jsonify({
                'message': 'School retrieved successfully',
                'school': result['data']
            }), 200
        else:
            return jsonify({'message': result['message']}), 404
            
    except Exception as e:
        logger.error(f"Error getting school {school_id}: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500


@school_bp.route('/<int:school_id>/users', methods=['GET'])
@login_required(['SUPER_ADMIN'])
@log_actions('GET_SCHOOL_USERS')
def get_school_users(school_id):
    """Get users for a specific school"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        role = request.args.get('role', '')
        
        if per_page > 100:
            per_page = 100
        
        result = SchoolService.get_school_users(school_id, page, per_page, role)
        
        if result['success']:
            return jsonify({
                'message': 'School users retrieved successfully',
                'data': result['data']
            }), 200
        else:
            return jsonify({'message': result['message']}), 404
            
    except Exception as e:
        logger.error(f"Error getting users for school {school_id}: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500


@school_bp.route('/list/school-admins', methods=['GET'])
@login_required(['SUPER_ADMIN'])
@log_actions('GET_SCHOOL_ADMINS')
def get_school_admins():
    """Get list of school admins"""
    try:
        result = SchoolService.get_school_admins()
        
        if result['success']:
            return jsonify({
                'message': 'School admins retrieved successfully',
                'data': result['data'],
                'status': 'success',
                'code': 200
            }), 200
        else:
            return jsonify({'message': result['message']}), 400
        
    except Exception as e:
        logger.error(f"Error getting school admins: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500


@school_bp.route('/school-admin/change-password/<int:admin_id>', methods=['PATCH'])
@login_required(['SUPER_ADMIN'])
@log_actions('CHANGE_ADMIN_PASSWORD')
def change_admin_password(admin_id):
    """Change password for a school admin"""
    try:
        data = request.get_json()
        
        if not data or 'new_password' not in data:
            return jsonify({'message': 'New password is required'}), 400
        
        new_password = data.get('new_password')
        
        result = SchoolService.change_admin_password(admin_id, new_password)
        
        if result['success']:
            return jsonify({
                'message': result['message'],
                'status': 'success',
                'code': 200
            }), 200
        else:
            return jsonify({'message': result['message']}), 400
            
    except Exception as e:
        logger.error(f"Error changing admin password {admin_id}: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500


@school_bp.route('/activate/<int:school_id>', methods=['PATCH'])
@login_required(['SUPER_ADMIN'])
@log_actions('ACTIVATE_SCHOOL')
def activate_school(school_id):
    """Activate school"""
    try:
        result = SchoolService.toggle_school_status(school_id, activate=True)
        
        if result['success']:
            return jsonify({
                'message': result['message'],
                'status': 'success',
                'code': 200
            }), 200
        else:
            return jsonify({'message': result['message']}), 404
            
    except Exception as e:
        logger.error(f"Error activating school {school_id}: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500


@school_bp.route('/deactivate/<int:school_id>', methods=['PATCH'])
@login_required(['SUPER_ADMIN'])
@log_actions('DEACTIVATE_SCHOOL')
def deactivate_school(school_id):
    """Deactivate school"""
    try:
        result = SchoolService.toggle_school_status(school_id, activate=False)
        
        if result['success']:
            return jsonify({
                'message': result['message'],
                'status': 'success',
                'code': 200
            }), 200
        else:
            return jsonify({'message': result['message']}), 404
            
    except Exception as e:
        logger.error(f"Error deactivating school {school_id}: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500
        

@school_bp.route('/delete/<int:school_id>', methods=['DELETE'])
@login_required(['SUPER_ADMIN'])
@log_actions('HARD_DELETE_SCHOOL')
def hard_delete_school(school_id):
    """Hard delete school - removes all users and drops database"""
    try:
        result = SchoolService.hard_delete_school(school_id)
        
        if result['success']:
            response = {
                'message': result['message'],
                'status': 'success',
                'code': 200
            }
            if 'warning' in result:
                response['warning'] = result['warning']
            
            return jsonify(response), 200
        else:
            return jsonify({'message': result['message']}), 404
            
    except Exception as e:
        logger.error(f"Error hard deleting school {school_id}: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500