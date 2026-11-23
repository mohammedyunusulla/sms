from functools import wraps

from flask import Blueprint, current_app, jsonify, request, send_file

from app.decorators.auth import login_required
from app.services.homework_service import MAX_HOMEWORK_PHOTOS, MAX_SUBMISSION_PAGES, HomeworkService

homework_bp = Blueprint("homework", __name__)

TEACHER_ROLES = ["SUPER_ADMIN", "TEACHER", "PRINCIPAL", "SCHOOL_ADMIN"]
STUDENT_ROLES = ["STUDENT"]
ALL_HOMEWORK_ROLES = TEACHER_ROLES + STUDENT_ROLES

# Used when a student asks for a hint with only a photo of their work
PHOTO_ONLY_DOUBT = "I'm stuck. Please look at my work in the photo and give me a hint for the next step."


def _error(message, code):
    return jsonify({"message": message, "status": "error", "code": code}), code


def json_errors(view):
    """Unexpected errors come back as JSON (they used to be an HTML 500, shown as 'Network Error')."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        try:
            return view(*args, **kwargs)
        except Exception as exc:  # pragma: no cover - defensive
            current_app.logger.exception("Homework AI request failed")
            return _error(f"Something went wrong: {exc}", 500)
    return wrapper


def _int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


@homework_bp.route("/scope", methods=["GET"])
@login_required(TEACHER_ROLES, permission='manage_assignments')
@json_errors
def teaching_scope():
    """Classes/sections the teacher page may offer (teachers: only the sections they teach)."""
    body, status = HomeworkService.teaching_scope(request.current_user.skid, request.current_user)
    return jsonify(body), status


@homework_bp.route("/sections/<int:section_id>/subjects", methods=["GET"])
@login_required(TEACHER_ROLES, permission='manage_assignments')
@json_errors
def section_subjects(section_id: int):
    """Subjects for the Create Homework dropdown (teachers: only the ones they teach in that section)."""
    body, status = HomeworkService.section_subjects(request.current_user.skid, section_id, request.current_user)
    return jsonify(body), status


@homework_bp.route("/assignments", methods=["POST"])
@login_required(TEACHER_ROLES, permission='manage_assignments')
@json_errors
def create_assignment():
    # JSON, or multipart form when photos of the homework (e.g. the board) are attached
    photos = []
    if request.mimetype == "multipart/form-data":
        payload = request.form.to_dict()
        photos, error = HomeworkService.read_images(request.files.getlist("photos"), max_count=MAX_HOMEWORK_PHOTOS)
        if error:
            return _error(error, 422)
    else:
        payload = request.get_json(silent=True) or {}
    body, status = HomeworkService.create_assignment(request.current_user.skid, payload, request.current_user, photos=photos)
    return jsonify(body), status


@homework_bp.route("/assignments/<int:assignment_id>/photos/<int:index>", methods=["GET"])
@login_required(ALL_HOMEWORK_ROLES, permission='manage_assignments', own_roles=('STUDENT',))
@json_errors
def homework_photo(assignment_id: int, index: int):
    """One homework photo - only for that section's students and staff who may see the homework."""
    path, mime, error = HomeworkService.homework_photo(request.current_user.skid, assignment_id, index, request.current_user)
    if error:
        body, status = error
        return jsonify(body), status
    response = send_file(path, mimetype=mime, max_age=0)
    response.headers["Cache-Control"] = "private, no-store"
    return response


@homework_bp.route("/instructions-from-photo", methods=["POST"])
@login_required(TEACHER_ROLES, permission='manage_assignments')
@json_errors
def instructions_from_photo():
    """AI drafts the instructions text from photos of the homework; the teacher edits it before saving."""
    photos, error = HomeworkService.read_images(request.files.getlist("photos"), max_count=MAX_HOMEWORK_PHOTOS)
    if error:
        return _error(error, 422)
    body, status = HomeworkService.instructions_from_photos(photos, subject=(request.form.get("subject") or "").strip())
    return jsonify(body), status


@homework_bp.route("/assignments", methods=["GET"])
@login_required(ALL_HOMEWORK_ROLES, permission='manage_assignments', own_roles=('STUDENT',))
@json_errors
def list_assignments():
    class_id = request.args.get("class_id", type=int)
    section_id = request.args.get("section_id", type=int)
    body, status = HomeworkService.list_assignments(
        request.current_user.skid,
        request.current_user,
        class_id=class_id,
        section_id=section_id,
    )
    return jsonify(body), status


@homework_bp.route("/sessions/start", methods=["POST"])
@login_required(STUDENT_ROLES, self_service=True)
@json_errors
def start_session():
    """Multipart: assignment_id + start_photo (the blank notebook page with its QR sticker)."""
    if request.mimetype == "multipart/form-data":
        assignment_id = _int_or_none(request.form.get("assignment_id"))
        photos, error = HomeworkService.read_images(request.files.getlist("start_photo"), max_count=1)
        if error:
            return _error(error, 422)
    else:  # resuming an open session needs no photo
        assignment_id = _int_or_none((request.get_json(silent=True) or {}).get("assignment_id"))
        photos = []
    if not assignment_id:
        return _error("assignment_id is required", 422)
    body, status = HomeworkService.start_session(
        request.current_user.skid,
        request.current_user.school_user_id,
        assignment_id,
        photos[0] if photos else None,
    )
    return jsonify(body), status


@homework_bp.route("/sessions/latest", methods=["GET"])
@login_required(STUDENT_ROLES, self_service=True)
@json_errors
def latest_session():
    assignment_id = request.args.get("assignment_id", type=int)
    if not assignment_id:
        return _error("assignment_id is required", 422)
    body, status = HomeworkService.latest_session(
        request.current_user.skid,
        request.current_user.school_user_id,
        assignment_id,
    )
    return jsonify(body), status


@homework_bp.route("/sessions/<int:session_id>/toggle-pause", methods=["POST"])
@login_required(STUDENT_ROLES, self_service=True)
@json_errors
def toggle_pause(session_id: int):
    body, status = HomeworkService.toggle_pause(
        request.current_user.skid,
        request.current_user.school_user_id,
        session_id,
    )
    return jsonify(body), status


@homework_bp.route("/sessions/<int:session_id>/hint", methods=["POST"])
@login_required(STUDENT_ROLES, self_service=True)
@json_errors
def hint(session_id: int):
    student_doubt = request.form.get("doubt_text", "").strip() or request.form.get("student_doubt", "").strip()
    images, error = HomeworkService.read_images(request.files.getlist("file"), max_count=1)
    if error:
        return _error(error, 422)
    if not student_doubt and not images:
        return _error("Write your question or add a photo of your work", 422)
    body, status = HomeworkService.request_hint(
        request.current_user.skid,
        request.current_user.school_user_id,
        session_id,
        student_doubt or PHOTO_ONLY_DOUBT,
        student_images=images,
    )
    return jsonify(body), status


@homework_bp.route("/sessions/<int:session_id>/submit", methods=["POST"])
@login_required(STUDENT_ROLES, self_service=True)
@json_errors
def submit_session(session_id: int):
    """Multipart: files = the finished pages; the page the homework was started on (QR) must be one of them."""
    images, error = HomeworkService.read_images(request.files.getlist("files"), max_count=MAX_SUBMISSION_PAGES)
    if error:
        return _error(error, 422)
    body, status = HomeworkService.submit_session(
        request.current_user.skid,
        request.current_user.school_user_id,
        session_id,
        images,
    )
    return jsonify(body), status


@homework_bp.route("/sessions/<int:session_id>/photos/<kind>/<int:index>", methods=["GET"])
@login_required(ALL_HOMEWORK_ROLES, permission='manage_assignments', own_roles=('STUDENT',))
@json_errors
def session_photo(session_id: int, kind: str, index: int):
    """A session's start photo (kind=start) or finished page (kind=page) - for its student and the teachers."""
    path, mime, error = HomeworkService.session_photo(request.current_user.skid, session_id, kind, index, request.current_user)
    if error:
        body, status = error
        return jsonify(body), status
    response = send_file(path, mimetype=mime, max_age=0)
    response.headers["Cache-Control"] = "private, no-store"
    return response


@homework_bp.route("/analytics/assignment/<int:assignment_id>", methods=["GET"])
@login_required(TEACHER_ROLES, permission='manage_assignments')
@json_errors
def assignment_analytics(assignment_id: int):
    body, status = HomeworkService.assignment_analytics(request.current_user.skid, assignment_id, request.current_user)
    return jsonify(body), status
