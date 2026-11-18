from datetime import date as date_type
from flask import Blueprint, request, jsonify
from app.decorators.auth import login_required
from app.services.bus_scan_service import BusScanService, search_students_for_bus

bus_scan_bp = Blueprint('bus_scan', __name__)

ALLOWED_ROLES = ['SCHOOL_ADMIN', 'PRINCIPAL', 'BUS_STAFF']


@bus_scan_bp.route('/scan/<skid>', methods=['POST'])
@login_required(allowed_roles=ALLOWED_ROLES)
def record_scan(skid):
    """Record a bus check-in or check-out scan."""
    data = request.get_json() or {}
    required = ['student_user_id', 'scan_type']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'message': f'Missing fields: {", ".join(missing)}'}), 400

    if data['scan_type'] not in ('CHECK_IN', 'CHECK_OUT'):
        return jsonify({'message': 'scan_type must be CHECK_IN or CHECK_OUT'}), 400

    # Attach scanned_by from the authenticated user's school_user_id
    data['scanned_by'] = request.current_user.school_user_id

    result = BusScanService.record_scan(skid, data)
    return jsonify({'message': 'Scan recorded', 'data': result}), 201


@bus_scan_bp.route('/scan-qr/<skid>', methods=['POST'])
@login_required(allowed_roles=ALLOWED_ROLES)
def scan_qr(skid):
    """Resolve a QR code payload and record the scan."""
    data = request.get_json() or {}
    qr_data = data.get('qr_data')
    scan_type = data.get('scan_type', 'CHECK_IN')

    if not qr_data:
        return jsonify({'message': 'qr_data is required'}), 400

    if scan_type not in ('CHECK_IN', 'CHECK_OUT'):
        return jsonify({'message': 'scan_type must be CHECK_IN or CHECK_OUT'}), 400

    student_user_id = BusScanService.lookup_student_by_qr(skid, qr_data)

    scan_payload = {
        'student_user_id': student_user_id,
        'scan_type': scan_type,
        'scanned_by': request.current_user.school_user_id,
        'academic_year_id': data.get('academic_year_id'),
        'location': data.get('location'),
    }
    result = BusScanService.record_scan(skid, scan_payload)
    return jsonify({'message': 'Scan recorded', 'student_user_id': student_user_id, 'data': result}), 201


@bus_scan_bp.route('/today/<skid>', methods=['GET'])
@login_required(allowed_roles=['SCHOOL_ADMIN', 'PRINCIPAL', 'BUS_STAFF', 'PARENT', 'TEACHER'])
def get_today(skid):
    """Get all bus scan records for a given date (defaults to today)."""
    academic_year_id = request.args.get('academic_year_id', type=int)
    date_str = request.args.get('date')
    for_date = None
    if date_str:
        try:
            for_date = date_type.fromisoformat(date_str)
        except ValueError:
            return jsonify({'message': 'Invalid date format, use YYYY-MM-DD'}), 400
    records = BusScanService.get_today_records(skid, academic_year_id, for_date)
    return jsonify({'data': records, 'total': len(records)}), 200


@bus_scan_bp.route('/status/<skid>', methods=['GET'])
@login_required(allowed_roles=['SCHOOL_ADMIN', 'PRINCIPAL', 'BUS_STAFF', 'PARENT', 'TEACHER'])
def get_status(skid):
    """Get current bus status — last scan per student today."""
    academic_year_id = request.args.get('academic_year_id', type=int)
    records = BusScanService.get_current_bus_status(skid, academic_year_id)
    return jsonify({'data': records, 'total': len(records)}), 200


@bus_scan_bp.route('/student/<skid>/<int:student_user_id>', methods=['GET'])
@login_required(allowed_roles=['SCHOOL_ADMIN', 'PRINCIPAL', 'BUS_STAFF', 'PARENT', 'TEACHER'])
def get_student_history(skid, student_user_id):
    """Get bus scan history for a specific student."""
    limit = request.args.get('limit', 50, type=int)
    records = BusScanService.get_student_history(skid, student_user_id, limit)
    return jsonify({'data': records, 'total': len(records)}), 200


@bus_scan_bp.route('/search-students/<skid>', methods=['GET'])
@login_required(allowed_roles=['SCHOOL_ADMIN', 'PRINCIPAL', 'BUS_STAFF'])
def search_students(skid):
    """Search students by name or admission number for manual scan entry."""
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify({'data': []}), 200
    results = search_students_for_bus(skid, q)
    return jsonify({'data': results}), 200
