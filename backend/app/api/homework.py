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
@login_required(TEACHER_ROLES)
@json_errors
def teaching_scope():
    """Classes/sections the teacher page may offer (teachers: only the sections they teach)."""
    body, status = HomeworkService.teaching_scope(request.current_user.skid, request.current_user)
    return jsonify(body), status


@homework_bp.route("/sections/<int:section_id>/subjects", methods=["GET"])
@login_required(TEACHER_ROLES)
@json_errors
def section_subjects(section_id: int):
    """Subjects for the Create Homework dropdown (teachers: only the ones they teach in that section)."""
    body, status = HomeworkService.section_subjects(request.current_user.skid, section_id, request.current_user)
    return jsonify(body), status


@homework_bp.route("/stickers/assign", methods=["POST"])
@login_required(TEACHER_ROLES)
@json_errors
def assign_sticker():
    payload = request.get_json(silent=True) or {}
    student_id = _int_or_none(payload.get("student_id"))
    if not student_id:
        return _error("student_id is required", 422)
    body, status = HomeworkService.assign_sticker(request.current_user.skid, student_id, request.current_user)
    return jsonify(body), status


@homework_bp.route("/assignments", methods=["POST"])
@login_required(TEACHER_ROLES)
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
@login_required(ALL_HOMEWORK_ROLES)
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
@login_required(TEACHER_ROLES)
@json_errors
def instructions_from_photo():
    """AI drafts the instructions text from photos of the homework; the teacher edits it before saving."""
    photos, error = HomeworkService.read_images(request.files.getlist("photos"), max_count=MAX_HOMEWORK_PHOTOS)
    if error:
        return _error(error, 422)
    body, status = HomeworkService.instructions_from_photos(photos, subject=(request.form.get("subject") or "").strip())
    return jsonify(body), status


@homework_bp.route("/assignments", methods=["GET"])
@login_required(ALL_HOMEWORK_ROLES)
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


@homework_bp.route("/stickers", methods=["GET"])
@login_required(TEACHER_ROLES)
@json_errors
def list_stickers():
    class_id = request.args.get("class_id", type=int)
    section_id = request.args.get("section_id", type=int)
    body, status = HomeworkService.list_stickers(request.current_user.skid, class_id, section_id, request.current_user)
    return jsonify(body), status


@homework_bp.route("/sessions/start", methods=["POST"])
@login_required(STUDENT_ROLES)
@json_errors
def start_session():
    payload = request.get_json(silent=True) or {}
    assignment_id = _int_or_none(payload.get("assignment_id"))
    qr_code_value = payload.get("qr_code_value")
    if not assignment_id or not qr_code_value:
        return _error("assignment_id and qr_code_value are required", 422)
    body, status = HomeworkService.start_session(
        request.current_user.skid,
        request.current_user.school_user_id,
        assignment_id,
        str(qr_code_value).strip(),
    )
    return jsonify(body), status


@homework_bp.route("/sessions/<int:session_id>/toggle-pause", methods=["POST"])
@login_required(STUDENT_ROLES)
@json_errors
def toggle_pause(session_id: int):
    body, status = HomeworkService.toggle_pause(
        request.current_user.skid,
        request.current_user.school_user_id,
        session_id,
    )
    return jsonify(body), status


@homework_bp.route("/sessions/<int:session_id>/hint", methods=["POST"])
@login_required(STUDENT_ROLES)
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
@login_required(STUDENT_ROLES)
@json_errors
def submit_session(session_id: int):
    qr_code_value = (request.form.get("qr_code_value") or "").strip()
    if not qr_code_value:
        return _error("qr_code_value is required", 422)
    images, error = HomeworkService.read_images(request.files.getlist("files"), max_count=MAX_SUBMISSION_PAGES)
    if error:
        return _error(error, 422)
    body, status = HomeworkService.submit_session(
        request.current_user.skid,
        request.current_user.school_user_id,
        session_id,
        qr_code_value,
        images,
    )
    return jsonify(body), status


@homework_bp.route("/analytics/assignment/<int:assignment_id>", methods=["GET"])
@login_required(TEACHER_ROLES)
@json_errors
def assignment_analytics(assignment_id: int):
    body, status = HomeworkService.assignment_analytics(request.current_user.skid, assignment_id, request.current_user)
    return jsonify(body), status
