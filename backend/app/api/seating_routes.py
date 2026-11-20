from flask import Blueprint, request, jsonify
from app.decorators import login_required
from app.services.seating_service import SeatingService

seating_bp = Blueprint('seating', __name__)


@seating_bp.route('/create/config/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL'], permission='manage_exams')
def create_config(skid):
    try:
        data = request.get_json()
        required = ['academic_year_id', 'exam_type_id', 'room_id', 'class_assignments',
                    'exam_date', 'start_time', 'end_time']
        missing = [f for f in required if f not in data]
        if missing:
            return jsonify({'message': f"Missing fields: {', '.join(missing)}", 'status': 'error', 'code': 400}), 400

        result = SeatingService.create_config(data, skid)
        return jsonify({'data': result, 'status': 'success', 'code': 200}), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500


@seating_bp.route('/fetch/configs/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER'], permission=('view_exams', 'manage_exams'))
def get_configs(skid):
    try:
        filters = {
            'academic_year_id': request.args.get('academic_year_id', type=int),
            'exam_type_id': request.args.get('exam_type_id', type=int),
            'exam_date': request.args.get('exam_date'),
        }
        filters = {k: v for k, v in filters.items() if v is not None}
        result = SeatingService.get_configs(skid, filters)
        return jsonify({'data': result, 'status': 'success', 'code': 200}), 200
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500


@seating_bp.route('/config/<int:config_id>/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER'], permission=('view_exams', 'manage_exams'))
def get_config(skid, config_id):
    try:
        result = SeatingService.get_config_by_id(config_id, skid)
        return jsonify({'data': result, 'status': 'success', 'code': 200}), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 404}), 404
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500


@seating_bp.route('/update/config/<skid>/<int:config_id>', methods=['PUT'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL'], permission='manage_exams')
def update_config(skid, config_id):
    try:
        data = request.get_json()
        result = SeatingService.update_config(config_id, data, skid)
        return jsonify({'data': result, 'status': 'success', 'code': 200}), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500


@seating_bp.route('/delete/config/<skid>/<int:config_id>', methods=['DELETE'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL'], permission='manage_exams')
def delete_config(skid, config_id):
    try:
        SeatingService.delete_config(config_id, skid)
        return jsonify({'message': 'Configuration deleted', 'status': 'success', 'code': 200}), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 404}), 404
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500


@seating_bp.route('/generate/<int:config_id>/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL'], permission='manage_exams')
def generate_seating(skid, config_id):
    try:
        result = SeatingService.generate_seating(config_id, skid)
        return jsonify({'data': result, 'status': 'success', 'code': 200}), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500


@seating_bp.route('/clear/<int:config_id>/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL'], permission='manage_exams')
def clear_seating(skid, config_id):
    try:
        result = SeatingService.clear_seating(config_id, skid)
        return jsonify({'data': result, 'status': 'success', 'code': 200}), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500


@seating_bp.route('/validate/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL'], permission='manage_exams')
def validate_config(skid):
    """
    Validate a config payload for conflicts before saving.
    Returns { valid: bool, errors: string[] }
    Query param: config_id (optional, for edit mode — exclude self from checks)
    """
    try:
        data = request.get_json()
        config_id = request.args.get('config_id', type=int)
        errors = SeatingService.validate_config(data, skid, config_id=config_id)
        return jsonify({
            'data': {'valid': len(errors) == 0, 'errors': errors},
            'status': 'success',
            'code': 200
        }), 200
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500


@seating_bp.route('/swap/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL'], permission='manage_exams')
def swap_seats(skid):
    """
    Move or swap students between seats.
    Body: { seat_a: {...}, seat_b: {...} }
    """
    try:
        data = request.get_json()
        if 'seat_a' not in data or 'seat_b' not in data:
            return jsonify({'message': 'seat_a and seat_b are required', 'status': 'error', 'code': 400}), 400
        result = SeatingService.swap_seats(data, skid)
        return jsonify({'data': result, 'status': 'success', 'code': 200}), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500
