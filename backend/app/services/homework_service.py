import os
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.models.tenant import HomeworkAssignment, SchoolUsers, Student, StudentHomeworkSession, StudentQRSticker
from app.services.homework_gemini_service import HomeworkGeminiService
from app.utils.db_manager import switch_to_school_db


class HomeworkService:
    STUDENT_ROLE = "STUDENT"

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    @staticmethod
    def _response(message: str, data: Optional[Any] = None, code: int = 200):
        payload = {"message": message, "status": "success", "code": code}
        if data is not None:
            payload["data"] = data
        return payload, code

    @staticmethod
    def _error(message: str, code: int = 400):
        return {"message": message, "status": "error", "code": code}, code

    @staticmethod
    def _session_to_dict(session: StudentHomeworkSession) -> Dict[str, Any]:
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

    @staticmethod
    def _assignment_to_dict(assignment: HomeworkAssignment, session_status: Optional[str] = None) -> Dict[str, Any]:
        return {
            "id": assignment.id,
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
            "current_session_status": session_status,
        }

    @staticmethod
    def _ensure_tables(tenant_session) -> None:
        StudentQRSticker.__table__.create(bind=tenant_session.bind, checkfirst=True)
        HomeworkAssignment.__table__.create(bind=tenant_session.bind, checkfirst=True)
        StudentHomeworkSession.__table__.create(bind=tenant_session.bind, checkfirst=True)

    @classmethod
    def assign_sticker(cls, skid: str, student_id: int):
        with switch_to_school_db(skid) as tenant_session:
            cls._ensure_tables(tenant_session)
            student = tenant_session.query(Student).filter_by(user_id=student_id).first()
            if not student:
                return cls._error("Student not found", 404)

            sticker = tenant_session.query(StudentQRSticker).filter_by(student_id=student_id).first()
            if sticker:
                sticker.is_active = True
            else:
                sticker = StudentQRSticker(
                    student_id=student_id,
                    qr_code_value=f"STU-{student_id}-QR-{uuid.uuid4().hex[:6].upper()}",
                    is_active=True,
                )
                tenant_session.add(sticker)
            tenant_session.commit()
            return cls._response(
                "Sticker assigned successfully",
                {"student_id": student_id, "qr_code_value": sticker.qr_code_value},
            )

    @classmethod
    def list_stickers(cls, skid: str, class_id: Optional[int], section_id: Optional[int]):
        with switch_to_school_db(skid) as tenant_session:
            cls._ensure_tables(tenant_session)
            query = (
                tenant_session.query(Student, SchoolUsers, StudentQRSticker)
                .join(SchoolUsers, SchoolUsers.id == Student.user_id)
                .outerjoin(StudentQRSticker, StudentQRSticker.student_id == Student.user_id)
            )
            if class_id:
                query = query.filter(Student.class_id == class_id)
            if section_id:
                query = query.filter(Student.section_id == section_id)

            rows = query.all()
            result = []
            for student, user, sticker in rows:
                result.append(
                    {
                        "student_id": student.user_id,
                        "name": f"{user.first_name} {user.last_name}".strip(),
                        "roll_no": student.roll_no,
                        "class_id": student.class_id,
                        "section_id": student.section_id,
                        "qr_code_value": sticker.qr_code_value if sticker else None,
                        "sticker_assigned": bool(sticker and sticker.is_active),
                    }
                )
            return cls._response("Stickers fetched successfully", result)

    @classmethod
    def create_assignment(cls, skid: str, payload: Dict[str, Any], created_by: int):
        required = ["class_id", "section_id", "subject", "title", "description"]
        missing = [field for field in required if not payload.get(field)]
        if missing:
            return cls._error(f"Missing required fields: {', '.join(missing)}", 422)

        due_date = None
        if payload.get("due_date"):
            due_date = datetime.fromisoformat(payload["due_date"].replace("Z", "+00:00")).replace(tzinfo=None)

        with switch_to_school_db(skid) as tenant_session:
            cls._ensure_tables(tenant_session)
            assignment = HomeworkAssignment(
                class_id=int(payload["class_id"]),
                section_id=int(payload["section_id"]),
                subject=str(payload["subject"]).strip(),
                title=str(payload["title"]).strip(),
                description=str(payload["description"]).strip(),
                reference_answer_key=payload.get("reference_answer_key"),
                expected_time_minutes=int(payload.get("expected_time_minutes", 15)),
                due_date=due_date,
                created_by=created_by,
                is_active=True,
            )
            tenant_session.add(assignment)
            tenant_session.commit()
            tenant_session.refresh(assignment)
            return cls._response("Assignment created successfully", cls._assignment_to_dict(assignment), 201)

    @classmethod
    def list_assignments(
        cls,
        skid: str,
        current_user,
        class_id: Optional[int] = None,
        section_id: Optional[int] = None,
    ):
        with switch_to_school_db(skid) as tenant_session:
            cls._ensure_tables(tenant_session)
            query = tenant_session.query(HomeworkAssignment).filter_by(is_active=True).order_by(HomeworkAssignment.created_at.desc())
            if class_id:
                query = query.filter(HomeworkAssignment.class_id == class_id)
            if section_id:
                query = query.filter(HomeworkAssignment.section_id == section_id)

            if current_user.role.value == cls.STUDENT_ROLE:
                student = tenant_session.query(Student).filter_by(user_id=current_user.school_user_id).first()
                if student:
                    query = query.filter_by(class_id=student.class_id, section_id=student.section_id)
                else:
                    query = query.filter(HomeworkAssignment.id == -1)

            assignments = query.all()
            student_sessions: Dict[int, StudentHomeworkSession] = {}
            if current_user.role.value == cls.STUDENT_ROLE:
                rows = tenant_session.query(StudentHomeworkSession).filter_by(student_id=current_user.school_user_id).all()
                student_sessions = {row.assignment_id: row for row in rows}

            data = []
            for assignment in assignments:
                session_status = student_sessions.get(assignment.id).status if assignment.id in student_sessions else None
                data.append(cls._assignment_to_dict(assignment, session_status))
            return cls._response("Assignments fetched successfully", data)

    @classmethod
    def start_session(cls, skid: str, student_user_id: int, assignment_id: int, qr_code_value: str):
        with switch_to_school_db(skid) as tenant_session:
            cls._ensure_tables(tenant_session)
            sticker = tenant_session.query(StudentQRSticker).filter_by(student_id=student_user_id, is_active=True).first()
            if not sticker or sticker.qr_code_value != qr_code_value:
                return cls._error("Invalid sticker QR code", 403)

            assignment = tenant_session.query(HomeworkAssignment).filter_by(id=assignment_id, is_active=True).first()
            if not assignment:
                return cls._error("Assignment not found", 404)

            now = cls._utc_now()
            session = (
                tenant_session.query(StudentHomeworkSession)
                .filter_by(student_id=student_user_id, assignment_id=assignment_id, is_active=True)
                .order_by(StudentHomeworkSession.id.desc())
                .first()
            )
            if session and session.status in ("in_progress", "paused"):
                if session.status == "paused":
                    session.status = "in_progress"
                    session.last_resumed_at = now
                tenant_session.commit()
                tenant_session.refresh(session)
                return cls._response("Session resumed successfully", cls._session_to_dict(session))

            session = StudentHomeworkSession(
                student_id=student_user_id,
                assignment_id=assignment_id,
                status="in_progress",
                started_at=now,
                last_resumed_at=now,
                active_duration_seconds=0,
                hints_used_count=0,
                submission_image_paths=[],
                ai_feedback_json={},
                is_active=True,
            )
            tenant_session.add(session)
            tenant_session.commit()
            tenant_session.refresh(session)
            return cls._response("Session started successfully", cls._session_to_dict(session), 201)

    @classmethod
    def toggle_pause(cls, skid: str, student_user_id: int, session_id: int):
        with switch_to_school_db(skid) as tenant_session:
            cls._ensure_tables(tenant_session)
            session = tenant_session.query(StudentHomeworkSession).filter_by(
                id=session_id, student_id=student_user_id, is_active=True
            ).first()
            if not session:
                return cls._error("Session not found", 404)
            if session.status not in ("in_progress", "paused"):
                return cls._error("Session is not active", 400)

            now = cls._utc_now()
            if session.status == "in_progress":
                if session.last_resumed_at:
                    session.active_duration_seconds += int((now - session.last_resumed_at).total_seconds())
                session.status = "paused"
                session.last_resumed_at = None
                action = "paused"
            else:
                session.status = "in_progress"
                session.last_resumed_at = now
                action = "resumed"
            tenant_session.commit()
            tenant_session.refresh(session)
            return cls._response(f"Session {action} successfully", cls._session_to_dict(session))

    @classmethod
    def request_hint(
        cls,
        skid: str,
        student_user_id: int,
        session_id: int,
        student_doubt: str,
        image_bytes: Optional[bytes] = None,
    ):
        with switch_to_school_db(skid) as tenant_session:
            cls._ensure_tables(tenant_session)
            session = tenant_session.query(StudentHomeworkSession).filter_by(
                id=session_id, student_id=student_user_id, is_active=True
            ).first()
            if not session:
                return cls._error("Session not found", 404)
            if session.status not in ("in_progress", "paused"):
                return cls._error("Hints are available only for active sessions", 400)

            assignment = tenant_session.query(HomeworkAssignment).filter_by(id=session.assignment_id, is_active=True).first()
            if not assignment:
                return cls._error("Assignment not found", 404)

            try:
                hint_text = HomeworkGeminiService.generate_socratic_hint(
                    assignment_title=assignment.title,
                    assignment_description=assignment.description,
                    student_doubt=student_doubt,
                    image_bytes=image_bytes,
                )
            except Exception as exc:
                return cls._error(f"Hint generation failed: {exc}", 500)

            session.hints_used_count += 1
            tenant_session.commit()
            return cls._response(
                "Hint generated successfully",
                {"hint": hint_text, "hints_used_count": session.hints_used_count},
            )

    @staticmethod
    def _compute_efficiency_score(
        accuracy_score: float,
        expected_time_minutes: int,
        active_duration_seconds: int,
        hints_used_count: int,
    ) -> float:
        expected_seconds = max(60, expected_time_minutes * 60)
        ratio = active_duration_seconds / expected_seconds if expected_seconds else 1

        if ratio <= 1:
            time_score = 100 - (1 - ratio) * 20
        else:
            time_score = max(40, 100 - min((ratio - 1) * 45, 60))

        hint_penalty = min(20, hints_used_count * 5)
        efficiency = (accuracy_score * 0.7) + (time_score * 0.3) - hint_penalty
        return round(max(0.0, min(100.0, efficiency)), 2)

    @classmethod
    def submit_session(
        cls,
        skid: str,
        student_user_id: int,
        session_id: int,
        qr_code_value: str,
        files,
    ):
        with switch_to_school_db(skid) as tenant_session:
            cls._ensure_tables(tenant_session)
            session = tenant_session.query(StudentHomeworkSession).filter_by(
                id=session_id, student_id=student_user_id, is_active=True
            ).first()
            if not session:
                return cls._error("Session not found", 404)
            if session.status not in ("in_progress", "paused"):
                return cls._error("Session is already submitted", 400)

            sticker = tenant_session.query(StudentQRSticker).filter_by(student_id=student_user_id, is_active=True).first()
            if not sticker or sticker.qr_code_value != qr_code_value:
                return cls._error("Invalid sticker QR code", 403)

            assignment = tenant_session.query(HomeworkAssignment).filter_by(id=session.assignment_id, is_active=True).first()
            if not assignment:
                return cls._error("Assignment not found", 404)

            now = cls._utc_now()
            if session.status == "in_progress" and session.last_resumed_at:
                session.active_duration_seconds += int((now - session.last_resumed_at).total_seconds())

            upload_root = Path(os.getenv("HOMEWORK_UPLOAD_DIR", "uploads/homework")).resolve()
            session_dir = upload_root / str(skid) / str(session.id)
            session_dir.mkdir(parents=True, exist_ok=True)

            image_bytes_list: List[bytes] = []
            saved_paths: List[str] = []
            for file_obj in files:
                raw = file_obj.read()
                if not raw:
                    continue
                image_bytes_list.append(raw)
                suffix = Path(file_obj.filename or "page.jpg").suffix or ".jpg"
                saved_name = f"{uuid.uuid4().hex}{suffix.lower()}"
                full_path = session_dir / saved_name
                full_path.write_bytes(raw)
                saved_paths.append(str(full_path))

            if not image_bytes_list:
                return cls._error("At least one image is required", 422)

            try:
                grading = HomeworkGeminiService.grade_submission(
                    assignment={
                        "title": assignment.title,
                        "subject": assignment.subject,
                        "description": assignment.description,
                        "reference_answer_key": assignment.reference_answer_key,
                        "expected_time_minutes": assignment.expected_time_minutes,
                    },
                    image_bytes_list=image_bytes_list,
                    active_duration_seconds=session.active_duration_seconds,
                    hints_used_count=session.hints_used_count,
                )
            except Exception as exc:
                return cls._error(f"AI grading failed: {exc}", 500)

            accuracy_score = max(0.0, min(100.0, float(grading.get("accuracy_score", 0))))
            efficiency_score = cls._compute_efficiency_score(
                accuracy_score,
                assignment.expected_time_minutes,
                session.active_duration_seconds,
                session.hints_used_count,
            )

            session.status = "graded"
            session.submitted_at = now
            session.last_resumed_at = None
            session.submission_image_paths = saved_paths
            session.accuracy_score = round(accuracy_score, 2)
            session.efficiency_score = efficiency_score
            session.ai_feedback_json = grading
            tenant_session.commit()
            tenant_session.refresh(session)

            return cls._response(
                "Homework submitted and graded successfully",
                {"session": cls._session_to_dict(session), "grading": grading},
            )

    @classmethod
    def assignment_analytics(cls, skid: str, assignment_id: int):
        with switch_to_school_db(skid) as tenant_session:
            cls._ensure_tables(tenant_session)
            assignment = tenant_session.query(HomeworkAssignment).filter_by(id=assignment_id, is_active=True).first()
            if not assignment:
                return cls._error("Assignment not found", 404)

            sessions = tenant_session.query(StudentHomeworkSession).filter_by(assignment_id=assignment_id, is_active=True).all()
            total = len(sessions)
            submitted = [s for s in sessions if s.status in ("submitted", "graded")]
            graded = [s for s in sessions if s.status == "graded"]
            completed = len(submitted)

            avg_active = round(sum(s.active_duration_seconds for s in sessions) / total, 2) if total else 0
            avg_accuracy = round(sum((s.accuracy_score or 0) for s in graded) / len(graded), 2) if graded else 0
            avg_efficiency = round(sum((s.efficiency_score or 0) for s in graded) / len(graded), 2) if graded else 0

            buckets = {"high": 0, "steady": 0, "needs_review": 0}
            mistakes: Counter = Counter()
            for session in graded:
                score = session.efficiency_score or 0
                if score >= 80:
                    buckets["high"] += 1
                elif score >= 60:
                    buckets["steady"] += 1
                else:
                    buckets["needs_review"] += 1

                feedback = session.ai_feedback_json or {}
                for item in feedback.get("common_mistakes", []):
                    mistakes[str(item).strip()] += 1

            return cls._response(
                "Assignment analytics fetched successfully",
                {
                    "assignment": cls._assignment_to_dict(assignment),
                    "assignment_id": assignment_id,
                    "total_sessions": total,
                    "submitted_count": completed,
                    "completion_rate": round((completed / total) * 100, 2) if total else 0,
                    "expected_time_minutes": assignment.expected_time_minutes,
                    "average_time_seconds": avg_active,
                    "average_accuracy_score": avg_accuracy,
                    "average_efficiency_score": avg_efficiency,
                    "efficiency_distribution": buckets,
                    "students": [
                        {
                            "session_id": s.id,
                            "student_id": s.student_id,
                            "status": s.status,
                            "active_duration_seconds": s.active_duration_seconds,
                            "hints_used_count": s.hints_used_count,
                            "accuracy_score": s.accuracy_score,
                            "efficiency_score": s.efficiency_score,
                            "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
                            "ai_feedback_json": s.ai_feedback_json or {},
                        }
                        for s in sessions
                    ],
                    "common_conceptual_mistakes": [
                        {"mistake": key, "count": value} for key, value in mistakes.most_common(10)
                    ],
                },
            )
