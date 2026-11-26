from flask import Blueprint, request, jsonify
from app.decorators.auth import login_required
from app.decorators.logging import log_actions
from app.services.institution_service import InstitutionService
from app.models.main.User import UserRole
from app.models.main.Institution import Institution
import logging

logger = logging.getLogger(__name__)

institution_bp = Blueprint('institution', __name__)

@institution_bp.route('/create', methods=['POST'])
@login_required(['SUPER_ADMIN'])
@log_actions('CREATE_INSTITUTION')
def create_institution():
    """Create a new institution with database and initialize using models"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'message': 'No data provided'}), 400
        
        # Check if institution with same code exists
        existing_institution = Institution.query.filter_by(code=data.get('code')).first()
        if existing_institution:
            return jsonify({
                'message': f"Institution with code '{data['code']}' already exists.",
                'status': 'error',
                'code': 409
            }), 409
        
        # Create institution
        result = InstitutionService.create_institution(data)
        
        if result['success']:
            return jsonify({
                'message': result['message'],
                'institution': result['data'],
                'status': 'success',
                'code': 200
            }), 200
        else:
            return jsonify({'message': result['message']}), 400
            
    except Exception as e:
        logger.error(f"Error creating institution: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500


@institution_bp.route('/update/<int:institution_id>', methods=['PUT'])
@login_required(['SUPER_ADMIN'])
@log_actions('UPDATE_INSTITUTION')
def update_institution(institution_id):
    """Update institution"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'message': 'No data provided'}), 400
            
        result = InstitutionService.update_institution(institution_id, data)
        
        if result['success']:
            return jsonify({
                'message': result['message'],
                'institution': result['data'],
                'status': 'success',
                'code': 200
            }), 200
        else:
            status_code = 404 if 'not found' in result['message'].lower() else 400
            return jsonify({'message': result['message']}), status_code
            
    except Exception as e:
        logger.error(f"Error updating institution {institution_id}: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500


@institution_bp.route('/<int:institution_id>/features', methods=['GET'])
@login_required(['SUPER_ADMIN'])
def get_institution_features(institution_id):
    """An institution's feature and sign-in switches, with the list of switches there are."""
    result = InstitutionService.get_feature_settings(institution_id)
    if not result['success']:
        return jsonify({'message': result['message']}), 404
    return jsonify({'data': result['data'], 'status': 'success'}), 200


@institution_bp.route('/<int:institution_id>/features', methods=['PUT'])
@login_required(['SUPER_ADMIN'])
@log_actions('UPDATE_INSTITUTION_FEATURES')
def update_institution_features(institution_id):
    """Body: { features?: [key], login_roles?: [role code] }"""
    result = InstitutionService.update_feature_settings(institution_id, request.get_json(silent=True) or {})
    if not result['success']:
        return jsonify({'message': result['message']}), 404 if result['message'] == 'Institution not found' else 400
    return jsonify({'message': result['message'], 'data': result['data'], 'status': 'success'}), 200


@institution_bp.route('/list', methods=['GET'])
@login_required(['SUPER_ADMIN'])
@log_actions('GET_INSTITUTIONS')
def get_institutions():
    """Get list of institutions"""
    try:
        
        result = InstitutionService.get_institutions()
        
        if result['success']:
            return jsonify({
                'message': 'Institutions retrieved successfully',
                'data': result['data'],
                'status': 'success',
                'code': 200
            }), 200
        else:
            return jsonify({'message': result['message']}), 400
        
    except Exception as e:
        logger.error(f"Error getting institutions: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500


@institution_bp.route('/dashboard/stats', methods=['GET'])
@login_required(['SUPER_ADMIN'])
@log_actions('GET_SUPER_ADMIN_DASHBOARD')
def get_super_admin_dashboard():
    """Get system-wide dashboard stats for super admin"""
    try:
        result = InstitutionService.get_super_admin_dashboard_stats()

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


@institution_bp.route('/<int:institution_id>', methods=['GET'])
@login_required(['SUPER_ADMIN'])
@log_actions('GET_INSTITUTION')
def get_institution(institution_id):
    """Get institution by ID"""
    try:
        result = InstitutionService.get_institution_by_id(institution_id)
        
        if result['success']:
            return jsonify({
                'message': 'Institution retrieved successfully',
                'institution': result['data']
            }), 200
        else:
            return jsonify({'message': result['message']}), 404
            
    except Exception as e:
        logger.error(f"Error getting institution {institution_id}: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500


@institution_bp.route('/<int:institution_id>/users', methods=['GET'])
@login_required(['SUPER_ADMIN'])
@log_actions('GET_INSTITUTION_USERS')
def get_institution_users(institution_id):
    """Get users for a specific institution"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        role = request.args.get('role', '')
        
        if per_page > 100:
            per_page = 100
        
        result = InstitutionService.get_institution_users(institution_id, page, per_page, role)
        
        if result['success']:
            return jsonify({
                'message': 'Institution users retrieved successfully',
                'data': result['data']
            }), 200
        else:
            return jsonify({'message': result['message']}), 404
            
    except Exception as e:
        logger.error(f"Error getting users for institution {institution_id}: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500


@institution_bp.route('/list/institution-admins', methods=['GET'])
@login_required(['SUPER_ADMIN'])
@log_actions('GET_INSTITUTION_ADMINS')
def get_institution_admins():
    """Get list of institution admins"""
    try:
        result = InstitutionService.get_institution_admins()
        
        if result['success']:
            return jsonify({
                'message': 'Institution admins retrieved successfully',
                'data': result['data'],
                'status': 'success',
                'code': 200
            }), 200
        else:
            return jsonify({'message': result['message']}), 400
        
    except Exception as e:
        logger.error(f"Error getting institution admins: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500


@institution_bp.route('/institution-admin/change-password/<int:admin_id>', methods=['PATCH'])
@login_required(['SUPER_ADMIN'])
@log_actions('CHANGE_ADMIN_PASSWORD')
def change_admin_password(admin_id):
    """Change password for an institution admin"""
    try:
        data = request.get_json()
        
        if not data or 'new_password' not in data:
            return jsonify({'message': 'New password is required'}), 400
        
        new_password = data.get('new_password')
        
        result = InstitutionService.change_admin_password(admin_id, new_password)
        
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


@institution_bp.route('/activate/<int:institution_id>', methods=['PATCH'])
@login_required(['SUPER_ADMIN'])
@log_actions('ACTIVATE_INSTITUTION')
def activate_institution(institution_id):
    """Activate institution"""
    try:
        result = InstitutionService.toggle_institution_status(institution_id, activate=True)
        
        if result['success']:
            return jsonify({
                'message': result['message'],
                'status': 'success',
                'code': 200
            }), 200
        else:
            return jsonify({'message': result['message']}), 404
            
    except Exception as e:
        logger.error(f"Error activating institution {institution_id}: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500


@institution_bp.route('/deactivate/<int:institution_id>', methods=['PATCH'])
@login_required(['SUPER_ADMIN'])
@log_actions('DEACTIVATE_INSTITUTION')
def deactivate_institution(institution_id):
    """Deactivate institution"""
    try:
        result = InstitutionService.toggle_institution_status(institution_id, activate=False)
        
        if result['success']:
            return jsonify({
                'message': result['message'],
                'status': 'success',
                'code': 200
            }), 200
        else:
            return jsonify({'message': result['message']}), 404
            
    except Exception as e:
        logger.error(f"Error deactivating institution {institution_id}: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500
        

@institution_bp.route('/delete/<int:institution_id>', methods=['DELETE'])
@login_required(['SUPER_ADMIN'])
@log_actions('HARD_DELETE_INSTITUTION')
def hard_delete_institution(institution_id):
    """Hard delete institution - removes all users and drops database"""
    try:
        # the institution's code must be typed back, so a stray request or double click can't drop an institution (QA S14)
        institution = Institution.query.get(institution_id)
        if not institution:
            return jsonify({'message': 'Institution not found', 'status': 'error', 'code': 404}), 404
        typed = str((request.get_json(silent=True) or {}).get('confirm_code') or '').strip().lower()
        if typed != (institution.code or '').strip().lower():
            return jsonify({'message': "Type the institution's code to confirm the delete", 'status': 'error', 'code': 400}), 400

        result = InstitutionService.hard_delete_institution(institution_id)
        
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
        logger.error(f"Error hard deleting institution {institution_id}: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500