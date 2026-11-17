import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .gemini_service import GeminiHomeworkService, HomeworkImage
from .models import HomeworkAssignment, StudentHomeworkSession, StudentQRSticker


class StickerAssignRequest(BaseModel):
    student_id: int
    qr_code_value: str | None = None
    is_active: bool = True


class AssignmentCreateRequest(BaseModel):
    class_id: int
    section_id: int
    subject: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    reference_answer_key: str | None = None
    expected_time_minutes: int = Field(default=15, ge=1, le=600)
    due_date: datetime | None = None


class SessionStartRequest(BaseModel):
    qr_code_value: str
    assignment_id: int


def _validate_role(user: Any, allowed_roles: set[str]) -> None:
    role = (getattr(user, "role", "") or "").upper()
    if role not in allowed_roles:
        raise HTTPException(status_code=403, detail="You do not have access to this action")


def _session_to_dict(session: StudentHomeworkSession) -> dict[str, Any]:
    return {
        "id": session.id,
        "student_id": session.student_id,
        "assignment_id": session.assignment_id,
        "status": session.status,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "last_resumed_at": session.last_resumed_at.isoformat() if session.last_resumed_at else None,
        "submitted_at": session.submitted_at.isoformat() if session.submitted_at else None,
        "active_duration_seconds": session.active_duration_seconds,
        "hints_used_count": session.hints_used_count,
        "submission_image_paths": session.submission_image_paths or [],
        "accuracy_score": session.accuracy_score,
        "efficiency_score": session.efficiency_score,
        "ai_feedback_json": session.ai_feedback_json or {},
    }


def _assignment_to_dict(
    assignment: HomeworkAssignment,
    session: StudentHomeworkSession | None = None,
) -> dict[str, Any]:
    payload = {
        "id": assignment.id,
        "skid": assignment.skid,
        "class_id": assignment.class_id,
        "section_id": assignment.section_id,
        "subject": assignment.subject,
        "title": assignment.title,
        "description": assignment.description,
        "reference_answer_key": assignment.reference_answer_key,
        "expected_time_minutes": assignment.expected_time_minutes,
        "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
        "created_by": assignment.created_by,
        "created_at": assignment.created_at.isoformat() if assignment.created_at else None,
        "current_session_status": session.status if session else None,
    }
    if session:
        payload["current_session"] = _session_to_dict(session)
    return payload


def _student_id_from_user(user: Any) -> int:
    value = getattr(user, "school_user_id", None)
    if value is None:
        raise HTTPException(status_code=400, detail="Current user has no school_user_id")
    return int(value)


def _finalize_active_duration(session: StudentHomeworkSession) -> None:
    if session.status == "in_progress" and session.last_resumed_at:
        elapsed = int((datetime.now(UTC) - session.last_resumed_at).total_seconds())
        if elapsed > 0:
            session.active_duration_seconds += elapsed
    session.last_resumed_at = None


def _compute_efficiency_score(
    *,
    accuracy_score: float,
    active_duration_seconds: int,
    expected_time_minutes: int,
    hints_used_count: int,
) -> float:
    expected_seconds = max(expected_time_minutes * 60, 1)
    time_ratio = active_duration_seconds / expected_seconds
    time_score = max(0.0, 100.0 - (abs(time_ratio - 1.0) * 60.0))
    hint_score = max(0.0, 100.0 - (hints_used_count * 8.0))
    weighted = (accuracy_score * 0.7) + (time_score * 0.2) + (hint_score * 0.1)
    return round(max(0.0, min(100.0, weighted)), 2)


def _guess_mime_type(filename: str | None) -> str:
    if not filename:
        return "image/jpeg"
    lower = filename.lower()
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".webp"):
        return "image/webp"
    if lower.endswith(".heic"):
        return "image/heic"
    return "image/jpeg"


def _save_upload_file(upload: UploadFile, base_dir: Path) -> str:
    base_dir.mkdir(parents=True, exist_ok=True)
    extension = Path(upload.filename or "").suffix or ".jpg"
    safe_name = f"{uuid.uuid4().hex}{extension.lower()}"
    destination = base_dir / safe_name
    content = upload.file.read()
    destination.write_bytes(content)
    return str(destination)


def create_homework_router(
    *,
    get_db_dep: Callable[[], Session],
    get_current_user_dep: Callable[..., Any],
    ok_response_fn: Callable[..., dict[str, Any]],
    resource_record_model: Any,
) -> APIRouter:
    router = APIRouter(prefix="/api/homework", tags=["homework"])

    @router.post("/stickers/assign")
    def assign_sticker(
        payload: StickerAssignRequest,
        db: Session = Depends(get_db_dep),
        current_user: Any = Depends(get_current_user_dep),
    ):
        _validate_role(current_user, {"SUPER_ADMIN", "SCHOOL_ADMIN", "PRINCIPAL", "TEACHER"})
        existing = db.scalar(
            select(StudentQRSticker).where(StudentQRSticker.student_id == payload.student_id)
        )
        qr_value = payload.qr_code_value or f"STU-{payload.student_id}-QR"
        while db.scalar(
            select(StudentQRSticker).where(
                StudentQRSticker.qr_code_value == qr_value,
                StudentQRSticker.student_id != payload.student_id,
            )
        ):
            qr_value = f"STU-{payload.student_id}-QR-{uuid.uuid4().hex[:6].upper()}"

        if existing:
            existing.qr_code_value = qr_value
            existing.is_active = payload.is_active
            sticker = existing
        else:
            sticker = StudentQRSticker(
                student_id=payload.student_id,
                qr_code_value=qr_value,
                is_active=payload.is_active,
            )
            db.add(sticker)
        db.commit()
        db.refresh(sticker)

        return ok_response_fn(
            code=201,
            message="Sticker assigned",
            data={
                "id": sticker.id,
                "student_id": sticker.student_id,
                "qr_code_value": sticker.qr_code_value,
                "is_active": sticker.is_active,
                "created_at": sticker.created_at.isoformat() if sticker.created_at else None,
                "printable": {
                    "label": f"STU-{sticker.student_id}",
                    "qr_code_value": sticker.qr_code_value,
                },
            },
        )

    @router.get("/stickers")
    def list_stickers(
        class_id: int | None = Query(default=None),
        section_id: int | None = Query(default=None),
        db: Session = Depends(get_db_dep),
        current_user: Any = Depends(get_current_user_dep),
    ):
        _validate_role(current_user, {"SUPER_ADMIN", "SCHOOL_ADMIN", "PRINCIPAL", "TEACHER"})

        students = list(
            db.scalars(select(resource_record_model).where(resource_record_model.resource == "students"))
        )
        filtered_students = []
        for student in students:
            payload = student.payload or {}
            if class_id is not None and int(payload.get("class_id", -1)) != class_id:
                continue
            if section_id is not None and int(payload.get("section_id", -1)) != section_id:
                continue
            filtered_students.append(payload)

        stickers = list(db.scalars(select(StudentQRSticker)))
        sticker_map = {st.student_id: st for st in stickers}
        rows = []
        for payload in filtered_students:
            sid = int(payload.get("school_user_id") or payload.get("student_id") or payload.get("id") or 0)
            if sid <= 0:
                continue
            sticker = sticker_map.get(sid)
            rows.append(
                {
                    "student_id": sid,
                    "name": payload.get("full_name") or payload.get("name") or "Student",
                    "roll_no": payload.get("roll_no"),
                    "class_id": payload.get("class_id"),
                    "section_id": payload.get("section_id"),
                    "qr_code_value": sticker.qr_code_value if sticker else None,
                    "sticker_assigned": bool(sticker),
                }
            )
        return ok_response_fn(data=rows)

    @router.post("/assignments")
    def create_assignment(
        payload: AssignmentCreateRequest,
        db: Session = Depends(get_db_dep),
        current_user: Any = Depends(get_current_user_dep),
    ):
        _validate_role(current_user, {"SCHOOL_ADMIN", "PRINCIPAL", "TEACHER"})
        assignment = HomeworkAssignment(
            skid=getattr(current_user, "skid", "SMS001"),
            class_id=payload.class_id,
            section_id=payload.section_id,
            subject=payload.subject,
            title=payload.title,
            description=payload.description,
            reference_answer_key=payload.reference_answer_key,
            expected_time_minutes=payload.expected_time_minutes,
            due_date=payload.due_date,
            created_by=int(getattr(current_user, "school_user_id", getattr(current_user, "id", 0))),
        )
        db.add(assignment)
        db.commit()
        db.refresh(assignment)
        return ok_response_fn(code=201, message="Assignment created", data=_assignment_to_dict(assignment))

    @router.get("/assignments")
    def list_assignments(
        class_id: int | None = Query(default=None),
        section_id: int | None = Query(default=None),
        student_id: int | None = Query(default=None),
        db: Session = Depends(get_db_dep),
        current_user: Any = Depends(get_current_user_dep),
    ):
        stmt = select(HomeworkAssignment).where(HomeworkAssignment.skid == getattr(current_user, "skid", "SMS001"))
        if class_id is not None:
            stmt = stmt.where(HomeworkAssignment.class_id == class_id)
        if section_id is not None:
            stmt = stmt.where(HomeworkAssignment.section_id == section_id)
        assignments = list(db.scalars(stmt.order_by(HomeworkAssignment.created_at.desc())))

        effective_student_id = student_id
        role = (getattr(current_user, "role", "") or "").upper()
        if role in {"STUDENT", "LEARNER"}:
            effective_student_id = _student_id_from_user(current_user)

        sessions_map: dict[int, StudentHomeworkSession] = {}
        if effective_student_id:
            sessions = list(
                db.scalars(
                    select(StudentHomeworkSession)
                    .where(StudentHomeworkSession.student_id == int(effective_student_id))
                    .order_by(StudentHomeworkSession.updated_at.desc())
                )
            )
            for sess in sessions:
                sessions_map.setdefault(sess.assignment_id, sess)

        data = [_assignment_to_dict(item, sessions_map.get(item.id)) for item in assignments]
        return ok_response_fn(data=data)

    @router.post("/sessions/start")
    def start_session(
        payload: SessionStartRequest,
        db: Session = Depends(get_db_dep),
        current_user: Any = Depends(get_current_user_dep),
    ):
        assignment = db.get(HomeworkAssignment, payload.assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        sticker = db.scalar(
            select(StudentQRSticker).where(
                StudentQRSticker.qr_code_value == payload.qr_code_value,
                StudentQRSticker.is_active.is_(True),
            )
        )
        if not sticker:
            raise HTTPException(status_code=404, detail="Sticker not found or inactive")

        current_student_id = _student_id_from_user(current_user)
        if sticker.student_id != current_student_id:
            raise HTTPException(status_code=403, detail="Sticker does not belong to current student")

        existing = db.scalar(
            select(StudentHomeworkSession).where(
                StudentHomeworkSession.student_id == sticker.student_id,
                StudentHomeworkSession.assignment_id == assignment.id,
                StudentHomeworkSession.status.in_(["in_progress", "paused"]),
            )
        )
        now = datetime.now(UTC)
        if existing:
            if existing.status == "paused":
                existing.status = "in_progress"
                existing.last_resumed_at = now
            db.add(existing)
            db.commit()
            db.refresh(existing)
            return ok_response_fn(message="Session resumed", data=_session_to_dict(existing))

        session = StudentHomeworkSession(
            student_id=sticker.student_id,
            assignment_id=assignment.id,
            status="in_progress",
            started_at=now,
            last_resumed_at=now,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return ok_response_fn(code=201, message="Session started", data=_session_to_dict(session))

    @router.post("/sessions/{session_id}/toggle-pause")
    def toggle_pause(
        session_id: int,
        db: Session = Depends(get_db_dep),
        current_user: Any = Depends(get_current_user_dep),
    ):
        session = db.get(StudentHomeworkSession, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session.student_id != _student_id_from_user(current_user):
            raise HTTPException(status_code=403, detail="Cannot modify another student's session")
        if session.status in {"submitted", "graded"}:
            raise HTTPException(status_code=400, detail="Submitted sessions cannot be modified")

        now = datetime.now(UTC)
        if session.status == "in_progress":
            _finalize_active_duration(session)
            session.status = "paused"
            message = "Session paused"
        else:
            session.status = "in_progress"
            session.last_resumed_at = now
            message = "Session resumed"

        db.add(session)
        db.commit()
        db.refresh(session)
        return ok_response_fn(message=message, data=_session_to_dict(session))

    @router.post("/sessions/{session_id}/hint")
    async def request_hint(
        session_id: int,
        doubt_text: str | None = Form(default=None),
        file: UploadFile | None = File(default=None),
        db: Session = Depends(get_db_dep),
        current_user: Any = Depends(get_current_user_dep),
    ):
        session = db.get(StudentHomeworkSession, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session.student_id != _student_id_from_user(current_user):
            raise HTTPException(status_code=403, detail="Cannot access another student's session")
        if session.status not in {"in_progress", "paused"}:
            raise HTTPException(status_code=400, detail="Hints are only available before submission")
        if not doubt_text and not file:
            raise HTTPException(status_code=400, detail="Provide either a text doubt or an image")

        assignment = db.get(HomeworkAssignment, session.assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        images: list[HomeworkImage] = []
        if file:
            content = await file.read()
            if content:
                images.append(HomeworkImage(mime_type=file.content_type or _guess_mime_type(file.filename), data=content))

        try:
            service = GeminiHomeworkService()
            hint = service.generate_socratic_hint(
                assignment_title=assignment.title,
                assignment_description=assignment.description,
                student_question=doubt_text or "",
                reference_answer_key=assignment.reference_answer_key,
                images=images,
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        session.hints_used_count += 1
        db.add(session)
        db.commit()
        db.refresh(session)
        return ok_response_fn(
            message="Hint generated",
            data={
                "hint": hint,
                "hints_used_count": session.hints_used_count,
                "session_id": session.id,
            },
        )

    @router.post("/sessions/{session_id}/submit")
    async def submit_homework(
        session_id: int,
        qr_code_value: str = Form(...),
        files: list[UploadFile] = File(...),
        db: Session = Depends(get_db_dep),
        current_user: Any = Depends(get_current_user_dep),
    ):
        session = db.get(StudentHomeworkSession, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session.student_id != _student_id_from_user(current_user):
            raise HTTPException(status_code=403, detail="Cannot submit another student's session")
        if session.status in {"submitted", "graded"}:
            raise HTTPException(status_code=400, detail="Session already submitted")

        sticker = db.scalar(
            select(StudentQRSticker).where(
                StudentQRSticker.qr_code_value == qr_code_value,
                StudentQRSticker.student_id == session.student_id,
                StudentQRSticker.is_active.is_(True),
            )
        )
        if not sticker:
            raise HTTPException(status_code=400, detail="Finish scan sticker does not match this student")
        if not files:
            raise HTTPException(status_code=400, detail="At least one notebook image is required")

        assignment = db.get(HomeworkAssignment, session.assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        _finalize_active_duration(session)
        session.status = "submitted"
        session.submitted_at = datetime.now(UTC)

        upload_root = Path(os.getenv("HOMEWORK_UPLOAD_DIR", "./uploads/homework")).resolve()
        session_dir = upload_root / str(session.id)
        image_paths: list[str] = []
        gemini_images: list[HomeworkImage] = []
        for upload in files:
            content = await upload.read()
            if not content:
                continue
            session_dir.mkdir(parents=True, exist_ok=True)
            extension = Path(upload.filename or "").suffix or ".jpg"
            file_name = f"{uuid.uuid4().hex}{extension.lower()}"
            file_path = session_dir / file_name
            file_path.write_bytes(content)
            image_paths.append(str(file_path))
            gemini_images.append(
                HomeworkImage(
                    mime_type=upload.content_type or _guess_mime_type(upload.filename),
                    data=content,
                )
            )
        if not gemini_images:
            raise HTTPException(status_code=400, detail="No valid image payloads found")
        session.submission_image_paths = image_paths

        try:
            service = GeminiHomeworkService()
            grading = service.grade_submission(
                assignment_title=assignment.title,
                assignment_description=assignment.description,
                reference_answer_key=assignment.reference_answer_key,
                expected_time_minutes=assignment.expected_time_minutes,
                active_duration_seconds=session.active_duration_seconds,
                hints_used_count=session.hints_used_count,
                images=gemini_images,
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        accuracy = float(grading.get("accuracy_score", 0))
        session.accuracy_score = max(0.0, min(100.0, accuracy))
        session.efficiency_score = _compute_efficiency_score(
            accuracy_score=session.accuracy_score,
            active_duration_seconds=session.active_duration_seconds,
            expected_time_minutes=assignment.expected_time_minutes,
            hints_used_count=session.hints_used_count,
        )
        session.ai_feedback_json = grading
        session.status = "graded"

        db.add(session)
        db.commit()
        db.refresh(session)

        return ok_response_fn(
            message="Homework submitted and graded",
            data={
                "session": _session_to_dict(session),
                "grading": grading,
            },
        )

    @router.get("/analytics/assignment/{assignment_id}")
    def assignment_analytics(
        assignment_id: int,
        db: Session = Depends(get_db_dep),
        current_user: Any = Depends(get_current_user_dep),
    ):
        _validate_role(current_user, {"SCHOOL_ADMIN", "PRINCIPAL", "TEACHER"})
        assignment = db.get(HomeworkAssignment, assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        sessions = list(
            db.scalars(
                select(StudentHomeworkSession).where(StudentHomeworkSession.assignment_id == assignment_id)
            )
        )
        submitted = [s for s in sessions if s.status in {"submitted", "graded"}]
        graded = [s for s in sessions if s.status == "graded"]
        total_sessions = len(sessions)
        completion_rate = round((len(submitted) / total_sessions) * 100, 2) if total_sessions else 0.0
        avg_time = round(sum(s.active_duration_seconds for s in submitted) / len(submitted), 2) if submitted else 0.0
        avg_accuracy = round(
            sum((s.accuracy_score or 0.0) for s in graded) / len(graded),
            2,
        ) if graded else 0.0
        avg_efficiency = round(
            sum((s.efficiency_score or 0.0) for s in graded) / len(graded),
            2,
        ) if graded else 0.0

        distribution = {"high": 0, "steady": 0, "needs_review": 0}
        mistakes_counter: dict[str, int] = {}
        rows = []
        for session in sessions:
            score = session.efficiency_score or 0
            if score >= 80:
                distribution["high"] += 1
            elif score >= 60:
                distribution["steady"] += 1
            else:
                distribution["needs_review"] += 1

            feedback = session.ai_feedback_json or {}
            mistakes = feedback.get("common_mistakes") or feedback.get("areas_to_improve") or []
            if isinstance(mistakes, list):
                for mistake in mistakes:
                    key = str(mistake).strip()
                    if key:
                        mistakes_counter[key] = mistakes_counter.get(key, 0) + 1

            rows.append(
                {
                    "session_id": session.id,
                    "student_id": session.student_id,
                    "status": session.status,
                    "active_duration_seconds": session.active_duration_seconds,
                    "hints_used_count": session.hints_used_count,
                    "accuracy_score": session.accuracy_score,
                    "efficiency_score": session.efficiency_score,
                    "submitted_at": session.submitted_at.isoformat() if session.submitted_at else None,
                    "ai_feedback_json": feedback,
                }
            )

        common_mistakes = [
            {"mistake": label, "count": count}
            for label, count in sorted(mistakes_counter.items(), key=lambda item: item[1], reverse=True)[:10]
        ]

        return ok_response_fn(
            data={
                "assignment": _assignment_to_dict(assignment),
                "total_sessions": total_sessions,
                "submitted_count": len(submitted),
                "completion_rate": completion_rate,
                "average_time_seconds": avg_time,
                "expected_time_minutes": assignment.expected_time_minutes,
                "average_accuracy_score": avg_accuracy,
                "average_efficiency_score": avg_efficiency,
                "efficiency_distribution": distribution,
                "common_conceptual_mistakes": common_mistakes,
                "students": rows,
            }
        )

    return router
