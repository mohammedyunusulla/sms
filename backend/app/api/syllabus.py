# app/api/syllabus.py
from flask import Blueprint, request, jsonify
from app.services.syllabus_service import SyllabusService
from app.decorators import login_required
from app.decorators.auth import student_access_required
from app.utils.teaching_scope import check_syllabus_item
from flask_jwt_extended import get_jwt_identity

syllabus_bp = Blueprint('syllabus', __name__)

# ============== SYLLABUS ENDPOINTS ==============

@syllabus_bp.route('/get/list/<skid>', methods=['GET'])
@login_required(['SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER'], permission=('view_syllabus_and_progress', 'manage_syllabus'))
def fetch_all_syllabus(skid):
    """Fetch all syllabi for a school"""
    try:
        academic_year_id = request.args.get('academic_year_id', type=int)
        result = SyllabusService.get_all_syllabi(skid, academic_year_id)
        return jsonify({'status': 'success', 'data': result, 'code': 200}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 500}), 500



@syllabus_bp.route('/create/<skid>', methods=['POST'])
@login_required(['SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER'], permission='manage_syllabus')
def create_syllabus(skid):
    """Create new syllabus"""
    try:
        data = request.get_json()

        # Get user from request context (set by login_required)
        user = getattr(request, 'current_user', None)
        if not user:
            raise ValueError("User not authenticated")

        # Use school_user_id which links to the ID in the tenant's teachers table
        teacher_id = user.school_user_id
        print("tenant_teacher_id--------", teacher_id)
        # Validate required fields
        if not data.get('subject_id'):
            raise ValueError("Subject ID is required")
        if not data.get('academic_year_id'):
            raise ValueError("Academic Year ID is required")
        if not data.get('title'):
            raise ValueError("Title is required")

        result = SyllabusService.create_syllabus(skid, data, teacher_id)
        return jsonify({
            'status': 'success',
            'data': result,
            'message': 'Syllabus created successfully',
            'code': 201
        }), 201
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 400}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 500}), 500


@syllabus_bp.route('/get/<skid>/<int:syllabus_id>', methods=['GET'])
@login_required(['SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER'], permission=('view_syllabus_and_progress', 'manage_syllabus'))
def get_syllabus_by_id(skid, syllabus_id):
    """Get syllabus by ID with teacher-specific progress"""
    try:
        # Get user from request context
        user = getattr(request, 'current_user', None)
        if not user:
            raise ValueError("User not authenticated")

        user_role = user.role.value if hasattr(user.role, 'value') else user.role

        # Teachers always resolve to their own ID with merged section progress
        if user_role == 'TEACHER':
            teacher_id = user.school_user_id
            include_hierarchy = request.args.get('include_hierarchy', 'false').lower() == 'true'
            # their section's progress; section_id picks one when they teach it in several (QA B33)
            result = SyllabusService.get_syllabus_by_id(
                skid, syllabus_id, teacher_id, include_hierarchy, merge_section_progress=True,
                section_id=request.args.get('section_id', type=int)
            )
        else:
            # Admin/Principal can pass teacher_id (int) or 'combined'
            teacher_id_param = request.args.get('teacher_id', type=str)
            include_hierarchy = request.args.get('include_hierarchy', 'false').lower() == 'true'

            section_param = request.args.get('section_id', type=int)
            if section_param:
                # one section's progress (QA B33)
                result = SyllabusService.get_syllabus_by_id(
                    skid, syllabus_id, None, include_hierarchy, section_id=section_param)
            elif teacher_id_param == 'combined':
                teacher_ids_param = request.args.get('teacher_ids', type=str)
                teacher_ids = [int(x) for x in teacher_ids_param.split(',') if x.strip()] if teacher_ids_param else None
                result = SyllabusService.get_syllabus_combined_progress(skid, syllabus_id, teacher_ids)
            elif teacher_id_param:
                # Admin per-teacher view: that teacher's (first) section, read-only
                result = SyllabusService.get_syllabus_by_id(
                    skid, syllabus_id, int(teacher_id_param), include_hierarchy, merge_section_progress=False
                )
                result['is_read_only'] = True
            else:
                result = SyllabusService.get_syllabus_by_id(skid, syllabus_id, None, include_hierarchy)

        return jsonify({'status': 'success', 'data': result, 'code': 200}), 200
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 404}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 500}), 500


@syllabus_bp.route('/teachers-for-syllabus/<skid>/<int:syllabus_id>', methods=['GET'])
@login_required(['SCHOOL_ADMIN', 'PRINCIPAL'], permission='manage_syllabus')
def get_teachers_for_syllabus(skid, syllabus_id):
    """Get all teachers assigned to a syllabus's subject with their progress summary"""
    try:
        result = SyllabusService.get_teachers_for_syllabus(skid, syllabus_id)
        return jsonify({'status': 'success', 'data': result, 'code': 200}), 200
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 404}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 500}), 500


# ============== TEACHER ASSIGNMENT ENDPOINTS ==============


@syllabus_bp.route('/assign-teacher/<skid>/<int:syllabus_id>', methods=['POST'])
@login_required(['SCHOOL_ADMIN', 'PRINCIPAL'], permission='manage_syllabus')
def assign_teacher(skid, syllabus_id):
    """Assign a teacher to a syllabus for a specific section"""
    try:
        data = request.get_json()
        teacher_id = data.get('teacher_id')
        section_id = data.get('section_id')

        if not teacher_id or not section_id:
            return jsonify({'status': 'error', 'message': 'teacher_id and section_id are required', 'code': 400}), 400

        result = SyllabusService.assign_teacher_to_syllabus(skid, syllabus_id, teacher_id, section_id)
        return jsonify({'status': 'success', 'data': result, 'message': 'Teacher assigned successfully', 'code': 201}), 201
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 400}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 500}), 500


@syllabus_bp.route('/unassign-teacher/<skid>/<int:assignment_id>', methods=['PUT'])
@login_required(['SCHOOL_ADMIN', 'PRINCIPAL'], permission='manage_syllabus')
def unassign_teacher(skid, assignment_id):
    """Unassign a teacher from a syllabus section (preserves history)"""
    try:
        result = SyllabusService.unassign_teacher_from_syllabus(skid, assignment_id)
        return jsonify({'status': 'success', 'message': result['message'], 'code': 200}), 200
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 404}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 500}), 500


@syllabus_bp.route('/assignments/<skid>/<int:syllabus_id>', methods=['GET'])
@login_required(['SCHOOL_ADMIN', 'PRINCIPAL'], permission='manage_syllabus')
def get_syllabus_assignments(skid, syllabus_id):
    """Get all teacher assignments (active and former) for a syllabus"""
    try:
        result = SyllabusService.get_syllabus_assignments(skid, syllabus_id)
        return jsonify({'status': 'success', 'data': result, 'code': 200}), 200
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 404}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 500}), 500


@syllabus_bp.route('/teachers-by-subject/<skid>/<int:subject_id>', methods=['GET'])
@login_required(['SCHOOL_ADMIN', 'PRINCIPAL'], permission='manage_syllabus')
def get_teachers_by_subject(skid, subject_id):
    """Get all teachers assigned to a subject via TeacherSubject"""
    try:
        result = SyllabusService.get_teachers_by_subject(skid, subject_id)
        return jsonify({'status': 'success', 'data': result, 'code': 200}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 500}), 500


@syllabus_bp.route('/list/subject/<skid>/<int:subject_id>', methods=['GET'])
@login_required(['SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER'], permission=('view_syllabus_and_progress', 'manage_syllabus'))
def get_syllabi_by_subject(skid, subject_id):
    """Get all syllabi for a subject"""
    try:
        academic_year_id = request.args.get('academic_year_id', type=int)
        result = SyllabusService.get_syllabi_by_subject(skid, subject_id, academic_year_id)
        return jsonify({'status': 'success', 'data': result, 'code': 200}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 500}), 500


@syllabus_bp.route('/list/teacher/<skid>/<int:teacher_id>', methods=['GET'])
@login_required(['SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER'], permission=('view_syllabus_and_progress', 'manage_syllabus'))
def get_syllabi_by_teacher(skid, teacher_id):
    """Get all syllabi for a teacher"""
    try:
        academic_year_id = request.args.get('academic_year_id', type=int)
        result = SyllabusService.get_syllabi_by_teacher(skid, teacher_id, academic_year_id)
        return jsonify({'status': 'success', 'data': result, 'code': 200}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 500}), 500


@syllabus_bp.route('/update/<skid>/<int:syllabus_id>', methods=['PUT'])
@login_required(['SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER'], permission='manage_syllabus')
def update_syllabus(skid, syllabus_id):
    """Update syllabus"""
    try:
        denied = check_syllabus_item(skid, 'syllabus', syllabus_id)
        if denied:
            return denied
        data = request.get_json()
        result = SyllabusService.update_syllabus(skid, syllabus_id, data)
        return jsonify({
            'status': 'success',
            'data': result,
            'message': 'Syllabus updated successfully',
            'code': 200
        }), 200
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 400}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 500}), 500


@syllabus_bp.route('/delete/<skid>/<int:syllabus_id>', methods=['DELETE'])
@login_required(['SCHOOL_ADMIN', 'PRINCIPAL'], permission='manage_syllabus')
def delete_syllabus(skid, syllabus_id):
    """Delete syllabus"""
    try:
        result = SyllabusService.delete_syllabus(skid, syllabus_id)
        return jsonify({'status': 'success', 'message': result['message'], 'code': 200}), 200
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 404}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 500}), 500


# ============== LESSON ENDPOINTS ==============


@syllabus_bp.route('/lesson/create/<skid>/<int:syllabus_id>', methods=['POST'])
@login_required(['SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER'], permission='manage_syllabus')
def create_lesson_or_chapter(skid, syllabus_id):
    """Create new lesson"""
    try:
        denied = check_syllabus_item(skid, 'syllabus', syllabus_id)
        if denied:
            return denied
        data = request.get_json()

        if not data.get('title'):
            raise ValueError("Lesson title is required")

        result = SyllabusService.create_lesson_or_chapter(skid, syllabus_id, data)
        return jsonify({
            'status': 'success',
            'data': result,
            'message': 'Lesson created successfully',
            'code': 201
        }), 201
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 400}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 500}), 500


@syllabus_bp.route('/lesson/update/<skid>/<int:lesson_id>', methods=['PUT'])
@login_required(['SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER'], permission='manage_syllabus')
def update_lesson(skid, lesson_id):
    """Update lesson (Shared content or teacher-specific progress)"""
    try:
        denied = check_syllabus_item(skid, 'lesson', lesson_id)
        if denied:
            return denied
        user = getattr(request, 'current_user', None)
        if not user:
            raise ValueError("User not authenticated")

        user_role = user.role.value if hasattr(user.role, 'value') else user.role
        teacher_id = user.school_user_id if user_role == 'TEACHER' else None

        data = request.get_json()
        result = SyllabusService.update_lesson(skid, lesson_id, data, teacher_id)
        return jsonify({
            'status': 'success',
            'data': result,
            'message': 'Lesson updated successfully',
            'code': 200
        }), 200
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 400}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 500}), 500


@syllabus_bp.route('/lesson/delete/<skid>/<int:lesson_id>', methods=['DELETE'])
@login_required(['SCHOOL_ADMIN', 'PRINCIPAL'], permission='manage_syllabus')
def delete_lesson(skid, lesson_id):
    """Delete lesson"""
    try:
        result = SyllabusService.delete_lesson(skid, lesson_id)
        return jsonify({'status': 'success', 'message': result['message'], 'code': 200}), 200
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 404}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 500}), 500


# ============== TOPIC ENDPOINTS ==============


@syllabus_bp.route('/topic/create/<skid>/<int:lesson_id>', methods=['POST'])
@login_required(['SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER'], permission='manage_syllabus')
def create_topic(skid, lesson_id):
    """Create new topic"""
    try:
        denied = check_syllabus_item(skid, 'lesson', lesson_id)
        if denied:
            return denied
        data = request.get_json()

        if not data.get('title'):
            raise ValueError("Topic title is required")

        result = SyllabusService.create_topic(skid, lesson_id, data)
        return jsonify({
            'status': 'success',
            'data': result,
            'message': 'Topic created successfully',
            'code': 201
        }), 201
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 400}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 500}), 500


@syllabus_bp.route('/topic/update/<skid>/<int:topic_id>', methods=['PUT'])
@login_required(['SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER'], permission='manage_syllabus')
def update_topic(skid, topic_id):
    """Update topic (Shared content or teacher-specific progress)"""
    try:
        denied = check_syllabus_item(skid, 'topic', topic_id)
        if denied:
            return denied
        user = getattr(request, 'current_user', None)
        if not user:
            raise ValueError("User not authenticated")

        user_role = user.role.value if hasattr(user.role, 'value') else user.role
        teacher_id = user.school_user_id if user_role == 'TEACHER' else None

        data = request.get_json()
        result = SyllabusService.update_topic(skid, topic_id, data, teacher_id)
        return jsonify({
            'status': 'success',
            'data': result,
            'message': 'Topic updated successfully',
            'code': 200
        }), 200
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 400}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 500}), 500


@syllabus_bp.route('/topic/delete/<skid>/<int:topic_id>', methods=['DELETE'])
@login_required(['SCHOOL_ADMIN', 'PRINCIPAL'], permission='manage_syllabus')
def delete_topic(skid, topic_id):
    """Delete topic"""
    try:
        result = SyllabusService.delete_topic(skid, topic_id)
        return jsonify({'status': 'success', 'message': result['message'], 'code': 200}), 200
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 404}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 500}), 500


# ============== SUBTOPIC ENDPOINTS ==============


@syllabus_bp.route('/subtopic/create/<skid>/<int:topic_id>', methods=['POST'])
@login_required(['SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER'], permission='manage_syllabus')
def create_subtopic(skid, topic_id):
    """Create new subtopic"""
    try:
        denied = check_syllabus_item(skid, 'topic', topic_id)
        if denied:
            return denied
        data = request.get_json()

        if not data.get('title'):
            raise ValueError("Subtopic title is required")

        result = SyllabusService.create_subtopic(skid, topic_id, data)
        return jsonify({
            'status': 'success',
            'data': result,
            'message': 'Subtopic created successfully',
            'code': 201
        }), 201
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 400}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 500}), 500


@syllabus_bp.route('/subtopic/update/<skid>/<int:subtopic_id>', methods=['PUT'])
@login_required(['SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER'], permission='manage_syllabus')
def update_subtopic(skid, subtopic_id):
    """Update subtopic (Shared content or teacher-specific progress)"""
    try:
        denied = check_syllabus_item(skid, 'subtopic', subtopic_id)
        if denied:
            return denied
        user = getattr(request, 'current_user', None)
        if not user:
            raise ValueError("User not authenticated")

        user_role = user.role.value if hasattr(user.role, 'value') else user.role
        teacher_id = user.school_user_id if user_role == 'TEACHER' else None

        data = request.get_json()
        result = SyllabusService.update_subtopic(skid, subtopic_id, data, teacher_id)
        return jsonify({
            'status': 'success',
            'data': result,
            'message': 'Subtopic updated successfully',
            'code': 200
        }), 200
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 400}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 500}), 500


@syllabus_bp.route('/subtopic/delete/<skid>/<int:subtopic_id>', methods=['DELETE'])
@login_required(['SCHOOL_ADMIN', 'PRINCIPAL'], permission='manage_syllabus')
def delete_subtopic(skid, subtopic_id):
    """Delete subtopic"""
    try:
        result = SyllabusService.delete_subtopic(skid, subtopic_id)
        return jsonify({'status': 'success', 'message': result['message'], 'code': 200}), 200
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 404}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 500}), 500


# ============== ANALYTICS ENDPOINTS ==============


@syllabus_bp.route('/analytics/<skid>/<int:syllabus_id>', methods=['GET'])
@login_required(['SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER'], permission=('view_syllabus_and_progress', 'manage_syllabus'))
def get_syllabus_analytics(skid, syllabus_id):
    """Get syllabus analytics with teacher-specific progress"""
    try:
        user = getattr(request, 'current_user', None)
        if not user:
            raise ValueError("User not authenticated")

        user_role = user.role.value if hasattr(user.role, 'value') else user.role
        teacher_id = user.school_user_id if user_role == 'TEACHER' else None

        result = SyllabusService.get_syllabus_analytics(skid, syllabus_id, teacher_id,
                                                        section_id=request.args.get('section_id', type=int))
        return jsonify({'status': 'success', 'data': result, 'code': 200}), 200
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 404}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 500}), 500


@syllabus_bp.route('/analytics/teacher/<skid>/<int:teacher_id>', methods=['GET'])
@login_required(['SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER'], permission=('view_syllabus_and_progress', 'manage_syllabus'))
def get_teacher_progress_summary(skid, teacher_id):
    """Get teacher progress summary"""
    try:
        academic_year_id = request.args.get('academic_year_id', type=int)
        if not academic_year_id:
            return jsonify({'status': 'error', 'message': 'academic_year_id is required', 'code': 400}), 400

        result = SyllabusService.get_teacher_progress_summary(skid, teacher_id, academic_year_id)
        return jsonify({'status': 'success', 'data': result, 'code': 200}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 500}), 500


# ============== TIMELINE CONFIGURATION ENDPOINTS ==============


@syllabus_bp.route('/progress/configure/<skid>', methods=['POST'])
@login_required(['TEACHER'], self_service=True)
def configure_timeline(skid):
    """Configure planned dates and notes for a syllabus item"""
    try:
        denied = check_syllabus_item(skid, (request.get_json(silent=True) or {}).get('item_type'), (request.get_json(silent=True) or {}).get('item_id'))
        if denied:
            return denied
        user = getattr(request, 'current_user', None)
        if not user:
            raise ValueError("User not authenticated")

        teacher_id = user.school_user_id
        data = request.get_json()

        item_type = data.get('item_type')
        item_id = data.get('item_id')

        if not item_type or not item_id:
            return jsonify({'status': 'error', 'message': 'item_type and item_id are required', 'code': 400}), 400

        if item_type not in ('lesson', 'topic', 'subtopic'):
            return jsonify({'status': 'error', 'message': 'item_type must be lesson, topic, or subtopic', 'code': 400}), 400

        if not data.get('planned_start_date') or not data.get('planned_end_date'):
            return jsonify({'status': 'error', 'message': 'planned_start_date and planned_end_date are required', 'code': 400}), 400

        result = SyllabusService.configure_timeline(skid, teacher_id, item_type, item_id, data,
                                                    section_id=data.get('section_id'))
        return jsonify({'status': 'success', 'data': result, 'code': 200}), 200
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 400}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 500}), 500


@syllabus_bp.route('/progress/start/<skid>', methods=['POST'])
@login_required(['TEACHER'], self_service=True)
def start_item(skid):
    """Start teaching a syllabus item (must be configured first)"""
    try:
        denied = check_syllabus_item(skid, (request.get_json(silent=True) or {}).get('item_type'), (request.get_json(silent=True) or {}).get('item_id'))
        if denied:
            return denied
        user = getattr(request, 'current_user', None)
        if not user:
            raise ValueError("User not authenticated")

        teacher_id = user.school_user_id
        data = request.get_json()

        item_type = data.get('item_type')
        item_id = data.get('item_id')

        if not item_type or not item_id:
            return jsonify({'status': 'error', 'message': 'item_type and item_id are required', 'code': 400}), 400

        if item_type not in ('lesson', 'topic', 'subtopic'):
            return jsonify({'status': 'error', 'message': 'item_type must be lesson, topic, or subtopic', 'code': 400}), 400

        result = SyllabusService.start_item(skid, teacher_id, item_type, item_id, section_id=data.get('section_id'))
        return jsonify({'status': 'success', 'data': result, 'code': 200}), 200
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 400}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 500}), 500


# ============== PROGRESS MARK ENDPOINT ==============


@syllabus_bp.route('/progress/mark/<skid>', methods=['POST'])
@login_required(['TEACHER'], self_service=True)
def mark_progress(skid):
    """Mark a syllabus item as complete/incomplete with bidirectional cascade"""
    try:
        denied = check_syllabus_item(skid, (request.get_json(silent=True) or {}).get('item_type'), (request.get_json(silent=True) or {}).get('item_id'))
        if denied:
            return denied
        user = getattr(request, 'current_user', None)
        if not user:
            raise ValueError("User not authenticated")

        teacher_id = user.school_user_id
        data = request.get_json()

        item_type = data.get('item_type')
        item_id = data.get('item_id')
        is_completed = data.get('is_completed', False)

        if not item_type or not item_id:
            return jsonify({'status': 'error', 'message': 'item_type and item_id are required', 'code': 400}), 400

        if item_type not in ('lesson', 'topic', 'subtopic'):
            return jsonify({'status': 'error', 'message': 'item_type must be lesson, topic, or subtopic', 'code': 400}), 400

        result = SyllabusService.mark_progress(skid, teacher_id, item_type, item_id, is_completed,
                                               section_id=data.get('section_id'))
        return jsonify({'status': 'success', 'data': result, 'code': 200}), 200
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 400}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 500}), 500


# ============== STUDENT VIEW ENDPOINTS ==============


@syllabus_bp.route('/student-view/<skid>', methods=['GET'])
@login_required(['STUDENT', 'SCHOOL_ADMIN', 'PRINCIPAL', 'PARENT', 'TEACHER'], permission=('view_syllabus_and_progress', 'view_child_syllabus', 'manage_syllabus'), own_roles=('STUDENT', 'PARENT'))
@student_access_required('student_user_id', source='query')
def get_student_syllabus_view(skid):
    """Get syllabus progress view. Teachers see their own syllabi; students resolve via timetable."""
    try:
        user = getattr(request, 'current_user', None)
        if not user:
            raise ValueError("User not authenticated")

        user_role = user.role.value if hasattr(user.role, 'value') else user.role
        academic_year_id = request.args.get('academic_year_id', type=int)

        if not academic_year_id:
            return jsonify({'status': 'error', 'message': 'academic_year_id is required', 'code': 400}), 400

        # Teachers get their own syllabi progress
        if user_role == 'TEACHER':
            result = SyllabusService.get_teacher_syllabus_progress_view(skid, user.school_user_id, academic_year_id)
            return jsonify({'status': 'success', 'data': result, 'code': 200}), 200

        # Students auto-resolve; others must pass student_user_id
        if user_role == 'STUDENT':
            student_user_id = user.school_user_id
        else:
            student_user_id = request.args.get('student_user_id', type=int)
            if not student_user_id:
                return jsonify({'status': 'error', 'message': 'student_user_id is required for non-student users', 'code': 400}), 400

        result = SyllabusService.get_student_syllabus_view(skid, student_user_id, academic_year_id)
        return jsonify({'status': 'success', 'data': result, 'code': 200}), 200
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 400}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 500}), 500


@syllabus_bp.route('/student-view/<skid>/<int:syllabus_id>', methods=['GET'])
@login_required(['STUDENT', 'SCHOOL_ADMIN', 'PRINCIPAL', 'PARENT', 'TEACHER'], permission=('view_syllabus_and_progress', 'view_child_syllabus', 'manage_syllabus'), own_roles=('STUDENT', 'PARENT'))
def get_student_syllabus_detail(skid, syllabus_id):
    """Get full syllabus hierarchy with teacher's progress overlay"""
    try:
        teacher_id = request.args.get('teacher_id', type=int)
        section_id = request.args.get('section_id', type=int)
        # a student always sees their own section's progress (QA B33)
        user = getattr(request, 'current_user', None)
        role = getattr(getattr(user, 'role', None), 'value', getattr(user, 'role', None))
        if role == 'STUDENT':
            from app.utils.db_manager import switch_to_school_db
            from app.models.tenant import Student
            with switch_to_school_db(skid) as session:
                me = session.query(Student).filter_by(user_id=user.school_user_id).first()
                section_id = me.section_id if me else None
        if not teacher_id and not section_id:
            return jsonify({'status': 'error', 'message': 'teacher_id or section_id query parameter is required', 'code': 400}), 400

        result = SyllabusService.get_student_syllabus_detail(skid, syllabus_id, teacher_id, section_id)
        return jsonify({'status': 'success', 'data': result, 'code': 200}), 200
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 404}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'code': 500}), 500
