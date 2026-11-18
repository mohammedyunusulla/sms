from flask import Blueprint, request, jsonify
from app.services.announcement_service import AnnouncementService
from app.decorators import login_required

announcement_bp = Blueprint('announcements', __name__)

@announcement_bp.route('/create/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER'])
def create_announcement(skid):
    """Create a new Announcement"""
    try:
        data = request.get_json()
        # Validate required fields
        required_fields = ['academic_year_id', 'title', 'description', 'announcement_type', 'target_audience']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'code': 400,
                    'status': 'error',
                    'message': f'Missing required field: {field}'
                }), 400
        
        Announcement = AnnouncementService.create_announcement(skid, data)
        
        return jsonify({
            'code': 201,
            'status': 'success',
            'message': 'Announcement created successfully',
            'data': Announcement
        }), 201
        
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

@announcement_bp.route('/get-by-id/<skid>/<int:announcement_id>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER'])
def get_announcement_by_id(skid, announcement_id):
    """Get a single announcement by ID"""
    try:
        announcement = AnnouncementService.get_announcement_by_id(skid, announcement_id)
        
        return jsonify({
            'code': 200,
            'status': 'success',
            'data': announcement
        }), 200
        
    except ValueError as e:
        return jsonify({
            'code': 404,
            'status': 'error',
            'message': str(e)
        }), 404
    except Exception as e:
        return jsonify({
            'code': 500,
            'status': 'error',
            'message': str(e)
        }), 500


@announcement_bp.route('/list/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER', 'STUDENT', 'PARENT'])
def get_announcements(skid):
    """Get announcements list"""
    try:
        academic_year_id = request.args.get('academic_year_id', type=int)
        announcement_type = request.args.get('announcement_type')
        priority = request.args.get('priority')
        
        # Get user info from query params (sent by frontend)
        user_role = request.args.get('user_role')
        school_user_id = request.args.get('school_user_id', type=int)
        
        if not academic_year_id:
            return jsonify({
                'code': 400,
                'status': 'error',
                'message': 'academic_year_id is required'
            }), 400
        
        filters = {}
        if announcement_type:
            filters['announcement_type'] = announcement_type
        if priority:
            filters['priority'] = priority
        
        # Pass user info to service
        user_info = {
            'role': user_role,
            'school_user_id': school_user_id
        } if user_role and school_user_id else None
        
        announcements = AnnouncementService.get_announcements(
            skid, 
            academic_year_id,
            user_info=user_info,
            filters=filters
        )
        
        return jsonify({
            'code': 200,
            'status': 'success',
            'data': announcements,
            'count': len(announcements)
        }), 200
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({
            'code': 500,
            'status': 'error',
            'message': str(e)
        }), 500


@announcement_bp.route('/update/<skid>/<int:announcement_id>', methods=['PUT'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER'])
def update_announcement(skid, announcement_id):
    """Update a Announcement"""
    try:
        data = request.get_json()
        
        Announcement = AnnouncementService.update_announcement(skid, announcement_id, data)
        
        return jsonify({
            'code': 200,
            'status': 'success',
            'message': 'Announcement updated successfully',
            'data': Announcement
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


@announcement_bp.route('/delete/<skid>/<int:announcement_id>', methods=['DELETE'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL'])
def delete_announcement(skid, announcement_id):
    """Delete a Announcement"""
    try:
        result = AnnouncementService.delete_announcement(skid, announcement_id)
        
        return jsonify({
            'code': 200,
            'status': 'success',
            'message': result['message']
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
