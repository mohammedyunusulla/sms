from flask import Blueprint, jsonify, request

from app.decorators.auth import login_required
from app.services.homework_service import HomeworkService

homework_bp = Blueprint("homework", __name__)

TEACHER_ROLES = ["SUPER_ADMIN", "TEACHER", "PRINCIPAL", "SCHOOL_ADMIN"]
STUDENT_ROLES = ["STUDENT"]
ALL_HOMEWORK_ROLES = TEACHER_ROLES + STUDENT_ROLES


@homework_bp.route("/stickers/assign", methods=["POST"])
@login_required(TEACHER_ROLES)
def assign_sticker():
    payload = request.get_json(silent=True) or {}
    student_id = payload.get("student_id")
    if not student_id:
        return jsonify({"message": "student_id is required", "status": "error", "code": 422}), 422
    body, status = HomeworkService.assign_sticker(request.current_user.skid, int(student_id))
    return jsonify(body), status


@homework_bp.route("/assignments", methods=["POST"])
@login_required(TEACHER_ROLES)
def create_assignment():
    payload = request.get_json(silent=True) or {}
    body, status = HomeworkService.create_assignment(
        request.current_user.skid,
        payload,
        request.current_user.school_user_id,
    )
    return jsonify(body), status


@homework_bp.route("/assignments", methods=["GET"])
@login_required(ALL_HOMEWORK_ROLES)
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
def list_stickers():
    class_id = request.args.get("class_id", type=int)
    section_id = request.args.get("section_id", type=int)
    body, status = HomeworkService.list_stickers(request.current_user.skid, class_id, section_id)
    return jsonify(body), status


@homework_bp.route("/sessions/start", methods=["POST"])
@login_required(STUDENT_ROLES)
def start_session():
    payload = request.get_json(silent=True) or {}
    assignment_id = payload.get("assignment_id")
    qr_code_value = payload.get("qr_code_value")
    if not assignment_id or not qr_code_value:
        return jsonify({"message": "assignment_id and qr_code_value are required", "status": "error", "code": 422}), 422
    body, status = HomeworkService.start_session(
        request.current_user.skid,
        request.current_user.school_user_id,
        int(assignment_id),
        str(qr_code_value).strip(),
    )
    return jsonify(body), status


@homework_bp.route("/sessions/<int:session_id>/toggle-pause", methods=["POST"])
@login_required(STUDENT_ROLES)
def toggle_pause(session_id: int):
    body, status = HomeworkService.toggle_pause(
        request.current_user.skid,
        request.current_user.school_user_id,
        session_id,
    )
    return jsonify(body), status


@homework_bp.route("/sessions/<int:session_id>/hint", methods=["POST"])
@login_required(STUDENT_ROLES)
def hint(session_id: int):
    student_doubt = request.form.get("doubt_text", "").strip() or request.form.get("student_doubt", "").strip()
    if not student_doubt:
        return jsonify({"message": "student_doubt is required", "status": "error", "code": 422}), 422
    image = request.files.get("file")
    image_bytes = image.read() if image else None
    body, status = HomeworkService.request_hint(
        request.current_user.skid,
        request.current_user.school_user_id,
        session_id,
        student_doubt,
        image_bytes=image_bytes,
    )
    return jsonify(body), status


@homework_bp.route("/sessions/<int:session_id>/submit", methods=["POST"])
@login_required(STUDENT_ROLES)
def submit_session(session_id: int):
    qr_code_value = (request.form.get("qr_code_value") or "").strip()
    files = request.files.getlist("files")
    if not qr_code_value:
        return jsonify({"message": "qr_code_value is required", "status": "error", "code": 422}), 422
    body, status = HomeworkService.submit_session(
        request.current_user.skid,
        request.current_user.school_user_id,
        session_id,
        qr_code_value,
        files,
    )
    return jsonify(body), status


@homework_bp.route("/analytics/assignment/<int:assignment_id>", methods=["GET"])
@login_required(TEACHER_ROLES)
def assignment_analytics(assignment_id: int):
    body, status = HomeworkService.assignment_analytics(request.current_user.skid, assignment_id)
    return jsonify(body), status
