from flask import Blueprint, request, jsonify
from app.decorators import login_required, log_actions
from app.services.academic_year_service import AcademicYearService

# If you don't have a separate blueprint, add to your existing classes_bp
academic_year_bp = Blueprint('academic-years', __name__)

@academic_year_bp.route('/get/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN'], permission=('manage_academic_years', 'manage_students'))
def get_academic_years(skid):
    """
    Get all academic years for an institution
    """
    try:
        if not skid:
            return jsonify({'message': 'Institution ID is required'}), 400
        
        academic_years = AcademicYearService.get_all_academic_years(skid)
        
        return jsonify({
            'message': 'Academic years retrieved successfully',
            'data': academic_years,
            'status': 'success',
            'code': 200
        }), 200
        
    except ValueError as e:
        return jsonify({'message': str(e)}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to fetch academic years: {str(e)}'}), 500


@academic_year_bp.route('/create/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN'], permission='manage_academic_years')
@log_actions('CREATE_ACADEMIC_YEAR')
def create_academic_year(skid):
    """
    Create a new academic year
    
    Request Body:
    {
        "year_name": "2027-2028",
        "start_date": "2027-04-01",
        "end_date": "2028-03-31",
        "is_current": false,
        "is_active": true
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'message': 'No data provided'}), 400
            
        if not skid:
            return jsonify({'message': 'Institution ID is required'}), 400
        
        # Validate required fields
        required_fields = ['year_name', 'start_date', 'end_date']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({
                'message': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Create academic year
        academic_year = AcademicYearService.create_academic_year(data, skid)
        
        return jsonify({
            'message': 'Academic year created successfully',
            'data': academic_year,
            'status': 'success',
            'code': 200
        }), 200
        
    except ValueError as e:
        return jsonify({'message': str(e)}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to create academic year: {str(e)}'}), 500


@academic_year_bp.route('/update/<skid>/<int:year_id>', methods=['PUT'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN'], permission='manage_academic_years')
@log_actions('UPDATE_ACADEMIC_YEAR')
def update_academic_year(skid, year_id):
    """
    Update an existing academic year
    
    Request Body:
    {
        "year_name": "2027-2028",
        "start_date": "2027-04-01",
        "end_date": "2028-03-31"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'message': 'No data provided'}), 400
            
        if not skid:
            return jsonify({'message': 'Institution ID is required'}), 400
        
        # Update academic year
        academic_year = AcademicYearService.update_academic_year(data, skid, year_id)
        
        return jsonify({
            'message': 'Academic year updated successfully',
            'data': academic_year,
            'status': 'success',
            'code': 200
        }), 200
        
    except ValueError as e:
        return jsonify({'message': str(e)}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to update academic year: {str(e)}'}), 500


@academic_year_bp.route('/delete/<skid>/<int:year_id>', methods=['DELETE'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN'], permission='manage_academic_years')
@log_actions('DELETE_ACADEMIC_YEAR')
def delete_academic_year(skid, year_id):
    """
    Soft-delete an academic year. Refuses to delete the current year.
    """
    try:
        if not skid:
            return jsonify({'message': 'Institution ID is required'}), 400

        result = AcademicYearService.delete_academic_year(skid, year_id)

        return jsonify({
            'message': 'Academic year deleted successfully',
            'data': result,
            'status': 'success',
            'code': 200
        }), 200

    except ValueError as e:
        return jsonify({'message': str(e)}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to delete academic year: {str(e)}'}), 500


@academic_year_bp.route('/patch/<skid>/<int:year_id>/set-current', methods=['PATCH'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN'], permission='manage_academic_years')
@log_actions('SET_CURRENT_ACADEMIC_YEAR')
def set_current_academic_year(skid, year_id):
    """
    Mark an academic year as current
    This will set all other years as not current
    """
    try:
        if not skid:
            return jsonify({'message': 'Institution ID is required'}), 400
        
        # Set as current
        result = AcademicYearService.set_current_academic_year(skid, year_id)
        
        return jsonify({
            'message': 'Current academic year updated successfully',
            'data': result,
            'status': 'success',
            'code': 200
        }), 200
        
    except ValueError as e:
        return jsonify({'message': str(e)}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to set current academic year: {str(e)}'}), 500
