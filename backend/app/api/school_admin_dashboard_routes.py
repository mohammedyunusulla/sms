from flask import Blueprint, request, jsonify
from app.services.school_admin_dashboard_service import SchoolAdminDashboardService
from app.services.announcement_service import AnnouncementService
from app.decorators import login_required

school_admin_dashboard_bp = Blueprint('schoolAdminDashboard', __name__)

@school_admin_dashboard_bp.route('/stats/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL'], self_service=True)
def get_dashboard_stats(skid):
    """Get school admin dashboard stats"""
    try:
        academic_year_id = request.args.get('academic_year_id', type=int)
        
        if not academic_year_id:
            return jsonify({
                'code': 400,
                'status': 'error',
                'message': 'academic_year_id is required'
            }), 400
        
        stats = SchoolAdminDashboardService.get_dashboard_stats(
            skid, academic_year_id
        )
        
        return jsonify({
            'code': 200,
            'status': 'success',
            'data': stats
        }), 200
        
    except ValueError as e:
        return jsonify({
            'code': 400,
            'status': 'error',
            'message': str(e)
        }), 400
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'status': 'error',
            'message': str(e)
        }), 500


@school_admin_dashboard_bp.route('/announcements/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL'], self_service=True)
def get_announcements(skid):
    """Get announcements for school admin dashboard"""
    try:
        academic_year_id = request.args.get('academic_year_id', type=int)
        
        if not academic_year_id:
            return jsonify({
                'code': 400,
                'status': 'error',
                'message': 'academic_year_id is required'
            }), 400
        
        # Get user info from request context (set by decorator)
        user = request.current_user
        user_info = {
            'role': user.role.value if hasattr(user.role, 'value') else user.role,
            'school_user_id': user.school_user_id
        }
        
        announcements = AnnouncementService.get_announcements(
            skid, 
            academic_year_id, 
            user_info=user_info,
            filters={'limit': 5}  # Get latest 5 announcements
        )
        
        return jsonify({
            'code': 200,
            'status': 'success',
            'data': announcements
        }), 200
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'status': 'error',
            'message': str(e)
        }), 500


@school_admin_dashboard_bp.route('/breakdown/monthly/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL'], self_service=True)
def get_monthly_expense_breakdown(skid):
    try:
        academic_year_id = request.args.get('academic_year_id')
        month = request.args.get('month', type=int)
        if month is not None and not 1 <= month <= 12:
            return jsonify({'message': 'Choose a month from 1 to 12', 'status': 'error', 'code': 400}), 400

        breakdown = SchoolAdminDashboardService.get_monthly_expenses_by_category(
            skid, 
            academic_year_id, 
            month
        )
        
        return jsonify({
            'breakdown': breakdown,
            'status': 'success',
            'code': 200
        }), 200
    except Exception as e:
        return jsonify({'message': f'Failed to get expense breakdown: {str(e)}'}), 500


@school_admin_dashboard_bp.route('/attendance-overview/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL'], self_service=True)
def get_attendance_overview(skid):
    """Get attendance overview for the current week"""
    try:
        academic_year_id = request.args.get('academic_year_id', type=int)
        class_id = request.args.get('class_id', type=int)
        section_id = request.args.get('section_id', type=int)

        if not academic_year_id:
            return jsonify({
                'code': 400,
                'status': 'error',
                'message': 'academic_year_id is required'
            }), 400

        data = SchoolAdminDashboardService.get_attendance_overview(
            skid, academic_year_id, class_id=class_id, section_id=section_id
        )

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': data
        }), 200

    except Exception as e:
        return jsonify({
            'code': 500,
            'status': 'error',
            'message': str(e)
        }), 500


@school_admin_dashboard_bp.route('/finance-summary/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL'], self_service=True)
def get_finance_summary(skid):
    """Get finance summary for school admin dashboard"""
    try:
        academic_year_id = request.args.get('academic_year_id', type=int)

        if not academic_year_id:
            return jsonify({
                'code': 400,
                'status': 'error',
                'message': 'academic_year_id is required'
            }), 400

        data = SchoolAdminDashboardService.get_finance_summary(
            skid, academic_year_id
        )

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': data
        }), 200

    except Exception as e:
        return jsonify({
            'code': 500,
            'status': 'error',
            'message': str(e)
        }), 500


@school_admin_dashboard_bp.route('/timetable/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL'], self_service=True)
def get_timetable(skid):
    """Get timetable for a class and section"""
    try:
        academic_year_id = request.args.get('academic_year_id', type=int)
        class_id = request.args.get('class_id', type=int)
        section_id = request.args.get('section_id', type=int)
        
        if not academic_year_id:
            return jsonify({
                'code': 400,
                'status': 'error',
                'message': 'academic_year_id is required'
            }), 400
            
        timetable_data = SchoolAdminDashboardService.get_timetable(
            skid, 
            academic_year_id, 
            class_id, 
            section_id
        )
        
        return jsonify({
            'code': 200,
            'status': 'success',
            'data': timetable_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'status': 'error',
            'message': str(e)
        }), 500
