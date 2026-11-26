import os
import shutil
import uuid
import tempfile
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.models.tenant import InstitutionUsers, Student
from app.models.tenant.Homework import Homework, StudentHomeworkSession
from app.models.tenant.Class import Class
from app.models.tenant.Sections import Section
from app.services.homework_gemini_service import HomeworkGeminiService
from app.utils.db_manager import switch_to_institution_db
from app.utils.qr_reader import QrReadError, read_qr_codes
from app.utils.teaching_scope import student_section_id, teacher_section_ids

# Upload limits (notebook pages, hint photos)
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_SUBMISSION_PAGES = 10
MAX_HOMEWORK_PHOTOS = 5
MAX_EXPECTED_MINUTES = 600

# File signatures of the image types we accept -> mime type
_IMAGE_SIGNATURES = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
)
_EXTENSIONS = {"image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif", "image/webp": ".webp", "image/heic": ".heic"}


def image_type(raw: bytes) -> Optional[str]:
    """The image's real type from its first bytes (not from the file name), or None if it isn't an image we accept."""
    for signature, mime in _IMAGE_SIGNATURES:
        if raw.startswith(signature):
            return mime
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "image/webp"
    if raw[4:8] == b"ftyp" and raw[8:12] in (b"heic", b"heix", b"mif1", b"msf1", b"hevc"):
        return "image/heic"
    return None


def _upload_root() -> Path:
    configured = os.getenv("HOMEWORK_UPLOAD_DIR", "").strip()
    if configured:
        return Path(configured).resolve()
    # Container-safe default (writable by non-root app user)
    return (Path(tempfile.gettempdir()) / "sms-homework").resolve()


_MIME_BY_EXT = {ext: mime for mime, ext in _EXTENSIONS.items()}


def _utc_iso(value: Optional[datetime]) -> Optional[str]:
    """A naive UTC datetime as ISO text marked UTC."""
    return value.isoformat() + "Z" if value else None


def page_fingerprint(raw: bytes) -> Optional[str]:
    """
    A 64-bit "difference hash" of a page photo: near-identical photos (the same picture re-sent, resized or
    re-saved) give nearly the same hash. A new photo of the same page from another angle usually doesn't.
    """
    try:
        from io import BytesIO
        from PIL import Image
        img = Image.open(BytesIO(raw)).convert("L").resize((9, 8))
        px = list(img.getdata())
        bits = 0
        for row in range(8):
            for col in range(8):
                bits = (bits << 1) | (1 if px[row * 9 + col] > px[row * 9 + col + 1] else 0)
        return f"{bits:016x}"
    except Exception:
        return None


def _fingerprint_distance(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


SAME_PHOTO_MAX_DISTANCE = 5     # out of 64 bits
FAST_SHARE_OF_MEDIAN = 0.35     # finished in under 35% of the class's usual time
FAST_SHARE_OF_EXPECTED = 0.25   # (fewer than 3 others to compare with: 25% of the expected time)


def load_images(paths) -> List[Tuple[bytes, str]]:
    """Read stored photos back as (bytes, mime); missing files are skipped."""
    images = []
    for path in paths or []:
        try:
            raw = Path(path).read_bytes()
        except OSError:
            continue
        images.append((raw, image_type(raw) or _MIME_BY_EXT.get(Path(path).suffix.lower(), "image/jpeg")))
    return images


class HomeworkService:
    STUDENT_ROLE = "STUDENT"
    STAFF_UNRESTRICTED = ("SUPER_ADMIN", "INSTITUTION_ADMIN", "PRINCIPAL")

    @staticmethod
    def _is_late(homework, session) -> bool:
        """Submitted after the due date. Due dates are entered in local (India) time, submissions are stored in UTC."""
        if not homework.due_date or not session.submitted_at:
            return False
        return session.submitted_at + timedelta(hours=5, minutes=30) > homework.due_date

    @staticmethod
    def _local_today() -> date:
        """Today in India (the server's clock is UTC: before 5:30 am IST it would still be yesterday)."""
        return (datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)).date()

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
    def _role(current_user) -> str:
        return current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)

    @classmethod
    def _teacher_sections(cls, tenant_session, current_user) -> Optional[set]:
        """None = unrestricted (admin / principal / super admin); otherwise the sections this teacher works in."""
        if cls._role(current_user) in cls.STAFF_UNRESTRICTED:
            return None
        return teacher_section_ids(tenant_session, current_user.institution_user_id)

    @staticmethod
    def read_images(files, max_count: int) -> Tuple[Optional[List[Tuple[bytes, str]]], Optional[str]]:
        """Validate uploaded images: real image type, size limit, count. Returns (images, error)."""
        images: List[Tuple[bytes, str]] = []
        for file_obj in files or []:
            raw = file_obj.read()
            if not raw:
                continue
            mime = image_type(raw)
            if not mime:
                return None, f"'{file_obj.filename or 'file'}' is not a photo. Use JPG, PNG, WEBP or HEIC images."
            if len(raw) > MAX_IMAGE_BYTES:
                return None, f"'{file_obj.filename or 'photo'}' is larger than {MAX_IMAGE_BYTES // (1024 * 1024)} MB."
            images.append((raw, mime))
        if len(images) > max_count:
            return None, f"At most {max_count} photos can be uploaded at once."
        return images, None

    @staticmethod
    def _session_to_dict(session: StudentHomeworkSession) -> Dict[str, Any]:
        return {
            "id": session.id,
            "student_id": session.student_id,
            "homework_id": session.homework_id,
            "status": session.status,
            # stored in UTC: marked as such ("Z") so browsers show local time and the live timer is right
            # (without it an Indian browser read them as local time and the timer started at 5:30:00)
            "started_at": _utc_iso(session.started_at),
            "last_resumed_at": _utc_iso(session.last_resumed_at),
            "submitted_at": _utc_iso(session.submitted_at),
            "active_duration_seconds": session.active_duration_seconds,
            "hints_used_count": session.hints_used_count,
            # file names only (not the server's full paths)
            "submission_image_paths": [Path(p).name for p in (session.submission_image_paths or [])],
            "accuracy_score": session.accuracy_score,
            "efficiency_score": session.efficiency_score,
            "ai_feedback_json": session.ai_feedback_json or {},
            "has_start_photo": bool(session.start_image_path),
            "page_qr_code": session.page_qr_code,
            "integrity": session.integrity_json or {},
        }

    @staticmethod
    def _homework_to_dict(
        homework: Homework,
        session_status: Optional[str] = None,
        include_answer_key: bool = True,
        hide_questions: bool = False,
    ) -> Dict[str, Any]:
        data = {
            "id": homework.id,
            "class_id": homework.class_id,
            "section_id": homework.section_id,
            "subject": homework.subject,
            "title": homework.title,
            "description": homework.description,
            "expected_time_minutes": homework.expected_time_minutes,
            "due_date": homework.due_date.isoformat() if homework.due_date else None,
            "homework_date": homework.homework_date.isoformat() if homework.homework_date else None,
            # photos are fetched one by one from /homework/items/<id>/photos/<index>
            "photo_count": len(homework.instruction_image_paths or []),
            "created_by": homework.created_by,
            "created_at": homework.created_at.isoformat() if homework.created_at else None,
            "current_session_status": session_status,
            # students see only the title, subject, time and due date until they press Start
            "questions_hidden": hide_questions,
        }
        if hide_questions:
            data["description"] = None
            data["photo_count"] = 0
        # The answer key / rubric is for teachers and the AI grader only, never for students
        if include_answer_key:
            data["reference_answer_key"] = homework.reference_answer_key
        return data

    @staticmethod
    def _ensure_tables(tenant_session) -> None:
        Homework.__table__.create(bind=tenant_session.bind, checkfirst=True)
        StudentHomeworkSession.__table__.create(bind=tenant_session.bind, checkfirst=True)
        from sqlalchemy import text as sql_text
        for statement in (
            "ALTER TABLE homeworks ADD COLUMN IF NOT EXISTS instruction_image_paths JSON DEFAULT '[]'",
            # the notebook page (QR sticker) a session was started on
            "ALTER TABLE student_homework_sessions ADD COLUMN IF NOT EXISTS page_qr_code VARCHAR(255)",
            "ALTER TABLE student_homework_sessions ADD COLUMN IF NOT EXISTS start_image_path VARCHAR(500)",
            "ALTER TABLE student_homework_sessions ADD COLUMN IF NOT EXISTS integrity_json JSON DEFAULT '{}'",
            # homework is per day: existing homework gets the day it was created
            "ALTER TABLE homeworks ADD COLUMN IF NOT EXISTS homework_date DATE",
            "UPDATE homeworks SET homework_date = created_at::date WHERE homework_date IS NULL",
            "CREATE INDEX IF NOT EXISTS ix_homeworks_homework_date ON homeworks (homework_date)",
            "CREATE INDEX IF NOT EXISTS ix_student_homework_sessions_page_qr_code ON student_homework_sessions (page_qr_code)",
        ):
            tenant_session.execute(sql_text(statement))

    # ------------------------------------------------------------------ homework
    @classmethod
    def _validate_new_homework(cls, tenant_session, payload: Dict[str, Any], has_photos: bool = False):
        """Returns (cleaned_values, error_response). Instructions are optional when photos are attached."""
        text = {k: str(payload.get(k) or "").strip() for k in ("subject", "title", "description")}
        missing = []
        if not payload.get("class_id"):
            missing.append("Class")
        if not payload.get("section_id"):
            missing.append("Section")
        missing += [label for key, label in (("subject", "Subject"), ("title", "Title")) if not text[key]]
        if not text["description"] and not has_photos:
            missing.append("Instructions (or a photo of the homework)")
        if missing:
            return None, cls._error(f"{', '.join(missing)} {'is' if len(missing) == 1 else 'are'} required", 422)

        try:
            class_id, section_id = int(payload["class_id"]), int(payload["section_id"])
        except (TypeError, ValueError):
            return None, cls._error("Class and section must be valid", 422)
        if not tenant_session.query(Class).filter_by(id=class_id).first():
            return None, cls._error("Class not found", 404)
        section = tenant_session.query(Section).filter_by(id=section_id).first()
        if not section:
            return None, cls._error("Section not found", 404)
        if section.class_id != class_id:
            return None, cls._error("That section doesn't belong to the selected class", 422)

        try:
            minutes = int(payload.get("expected_time_minutes") or 15)
        except (TypeError, ValueError):
            return None, cls._error("Expected minutes must be a whole number", 422)
        if not 1 <= minutes <= MAX_EXPECTED_MINUTES:
            return None, cls._error(f"Expected minutes must be between 1 and {MAX_EXPECTED_MINUTES}", 422)

        # The day the homework is for (default today); it replaces the old due date
        homework_date = cls._local_today()
        if payload.get("homework_date"):
            try:
                homework_date = date.fromisoformat(str(payload["homework_date"])[:10])
            except ValueError:
                return None, cls._error("Homework date is not a valid date", 422)
            if homework_date < cls._local_today():
                return None, cls._error("Homework date can't be in the past", 422)
            if homework_date > cls._local_today() + timedelta(days=60):
                return None, cls._error("Homework date can be at most 60 days ahead", 422)

        return {
            "class_id": class_id,
            "section_id": section_id,
            "subject": text["subject"],
            "title": text["title"],
            "description": text["description"],
            "reference_answer_key": (str(payload.get("reference_answer_key") or "").strip() or None),
            "expected_time_minutes": minutes,
            "due_date": None,
            "homework_date": homework_date,
        }, None

    @classmethod
    def create_homework(cls, skid: str, payload: Dict[str, Any], current_user, photos: Optional[Sequence[Tuple[bytes, str]]] = None):
        photos = list(photos or [])
        with switch_to_institution_db(skid) as tenant_session:
            cls._ensure_tables(tenant_session)
            values, error = cls._validate_new_homework(tenant_session, payload, has_photos=bool(photos))
            if error:
                return error
            allowed = cls._teacher_sections(tenant_session, current_user)
            if allowed is not None and values["section_id"] not in allowed:
                return cls._error("You can only create homework for sections you teach", 403)
            # The subject must be one of the section's subjects (for a teacher: one they teach there)
            offered = {s["subject_name"].lower(): s["subject_name"] for s in cls._section_subjects(tenant_session, values["section_id"], current_user)}
            if values["subject"].lower() not in offered:
                return cls._error("Pick a subject taught in the selected section", 422)
            values["subject"] = offered[values["subject"].lower()]

            homework = Homework(**values, created_by=current_user.institution_user_id, is_active=True, instruction_image_paths=[])
            tenant_session.add(homework)
            tenant_session.flush()  # need the id for the photo folder

            if photos:
                photo_dir = _upload_root() / str(skid) / "homework" / str(homework.id)
                try:
                    photo_dir.mkdir(parents=True, exist_ok=True)
                    paths = []
                    for raw, mime in photos:
                        path = photo_dir / f"{uuid.uuid4().hex}{_EXTENSIONS.get(mime, '.jpg')}"
                        path.write_bytes(raw)
                        paths.append(str(path))
                except OSError as exc:
                    shutil.rmtree(photo_dir, ignore_errors=True)
                    tenant_session.rollback()
                    return cls._error(f"Couldn't save the photos: {exc}", 500)
                homework.instruction_image_paths = paths

            tenant_session.commit()
            tenant_session.refresh(homework)
            from app.services import push_events
            push_events.homework_created(skid, tenant_session, homework)
            return cls._response("Homework created successfully", cls._homework_to_dict(homework), 201)

    @classmethod
    def homework_photo(cls, skid: str, homework_id: int, index: int, current_user):
        """Path + mime of one homework photo, if this user may see the homework. Returns (path, mime, error)."""
        with switch_to_institution_db(skid) as tenant_session:
            cls._ensure_tables(tenant_session)
            homework = tenant_session.query(Homework).filter_by(id=homework_id, is_active=True).first()
            if not homework:
                return None, None, cls._error("Homework not found", 404)
            if cls._role(current_user) == cls.STUDENT_ROLE:
                if homework.section_id != student_section_id(tenant_session, current_user.institution_user_id):
                    return None, None, cls._error("This homework isn't for your class", 403)
                started = tenant_session.query(StudentHomeworkSession.id).filter_by(
                    student_id=current_user.institution_user_id, homework_id=homework_id, is_active=True).first()
                is_past = bool(homework.homework_date and homework.homework_date < cls._local_today())
                if not started and not is_past:  # the questions stay hidden until the student presses Start
                    return None, None, cls._error("Start the homework to see it", 403)
            else:
                allowed = cls._teacher_sections(tenant_session, current_user)
                if allowed is not None and homework.section_id not in allowed:
                    return None, None, cls._error("You can only view homework for sections you teach", 403)
            paths = homework.instruction_image_paths or []
            if not 0 <= index < len(paths) or not Path(paths[index]).is_file():
                return None, None, cls._error("Photo not found", 404)
            raw_head = Path(paths[index]).read_bytes()[:16]
            return paths[index], image_type(raw_head) or "image/jpeg", None

    @classmethod
    def instructions_from_photos(cls, photos: Sequence[Tuple[bytes, str]], subject: str = ""):
        if not photos:
            return cls._error("Add at least one photo", 422)
        try:
            text = HomeworkGeminiService.extract_instructions(photos, subject=subject)
        except Exception as exc:
            return cls._error(f"Couldn't read the photo: {exc}", 500)
        if not text:
            return cls._error("No text could be read from the photo", 422)
        return cls._response("Instructions drafted from the photo", {"instructions": text})

    @classmethod
    def list_homework(
        cls,
        skid: str,
        current_user,
        class_id: Optional[int] = None,
        section_id: Optional[int] = None,
        on_date: Optional[str] = None,
    ):
        is_student = cls._role(current_user) == cls.STUDENT_ROLE
        today = cls._local_today()
        day = None
        if on_date:
            try:
                day = date.fromisoformat(str(on_date)[:10])
            except ValueError:
                return cls._error("Date is not valid", 422)
        with switch_to_institution_db(skid) as tenant_session:
            cls._ensure_tables(tenant_session)
            query = tenant_session.query(Homework).filter_by(is_active=True).order_by(
                Homework.homework_date.desc().nullslast(), Homework.created_at.desc())
            if day:
                query = query.filter(Homework.homework_date == day)
            if is_student:  # homework for a later day stays hidden until that day
                query = query.filter((Homework.homework_date <= today) | Homework.homework_date.is_(None))
            if class_id:
                query = query.filter(Homework.class_id == class_id)
            if section_id:
                query = query.filter(Homework.section_id == section_id)

            if is_student:
                # the student's current section (active enrollment first)
                own_section = student_section_id(tenant_session, current_user.institution_user_id)
                query = query.filter(Homework.section_id == (own_section if own_section else -1))
            else:
                allowed = cls._teacher_sections(tenant_session, current_user)
                if allowed is not None:
                    query = query.filter(Homework.section_id.in_(allowed or [-1]))

            homework_list = query.all()
            student_sessions: Dict[int, StudentHomeworkSession] = {}
            if is_student:
                rows = (
                    tenant_session.query(StudentHomeworkSession)
                    .filter_by(student_id=current_user.institution_user_id)
                    .order_by(StudentHomeworkSession.id.desc())
                    .all()
                )
                for row in rows:
                    if row.homework_id not in student_sessions:
                        student_sessions[row.homework_id] = row

            started_counts: Dict[int, int] = {}
            if not is_student and homework_list:
                from sqlalchemy import func as sa_func
                started_counts = dict(tenant_session.query(StudentHomeworkSession.homework_id, sa_func.count(StudentHomeworkSession.id)).filter(
                    StudentHomeworkSession.homework_id.in_([a.id for a in homework_list]),
                    StudentHomeworkSession.is_active.is_(True)).group_by(StudentHomeworkSession.homework_id).all())

            data = []
            for homework in homework_list:
                mine = student_sessions.get(homework.id)
                session_status = mine.status if mine else None
                is_past = bool(homework.homework_date and homework.homework_date < today)
                row = cls._homework_to_dict(
                    homework, session_status, include_answer_key=not is_student,
                    # before Start the questions are hidden; a past day's homework is view only, so it shows them
                    hide_questions=is_student and session_status is None and not is_past)
                row["is_past"] = is_past
                if is_student:
                    row["my_accuracy_score"] = mine.accuracy_score if mine else None
                    row["my_efficiency_score"] = mine.efficiency_score if mine else None
                else:
                    row["started_count"] = started_counts.get(homework.id, 0)
                data.append(row)
            return cls._response("Homework fetched successfully", data)

    @classmethod
    def delete_homework(cls, skid: str, homework_id: int, current_user):
        """Remove a homework nobody has started yet (e.g. made by mistake)."""
        with switch_to_institution_db(skid) as tenant_session:
            cls._ensure_tables(tenant_session)
            homework = tenant_session.query(Homework).filter_by(id=homework_id, is_active=True).first()
            if not homework:
                return cls._error("Homework not found", 404)
            allowed = cls._teacher_sections(tenant_session, current_user)
            if allowed is not None and homework.section_id not in allowed:
                return cls._error("You can only delete homework of sections you teach", 403)
            if tenant_session.query(StudentHomeworkSession.id).filter_by(homework_id=homework_id, is_active=True).first():
                return cls._error("Students have already started this homework, so it can't be deleted", 409)
            homework.is_active = False
            tenant_session.commit()
            return cls._response("Homework deleted", {"id": homework_id})

    # ------------------------------------------------------------------ student sessions
    @classmethod
    def start_session(cls, skid: str, student_user_id: int, homework_id: int, start_image: Optional[Tuple[bytes, str]]):
        """
        Start (or resume) a homework. Students only see the questions once they start, so the timer measures the
        real work: no page photo or QR sticker is needed (start_image is ignored; older app versions still send one).
        A homework can be started once; opening it again resumes the same session.
        """
        with switch_to_institution_db(skid) as tenant_session:
            cls._ensure_tables(tenant_session)
            homework = tenant_session.query(Homework).filter_by(id=homework_id, is_active=True).first()
            if not homework:
                return cls._error("Homework not found", 404)
            if homework.section_id != student_section_id(tenant_session, student_user_id):
                return cls._error("This homework isn't for your class", 403)

            now = cls._utc_now()
            session = (
                tenant_session.query(StudentHomeworkSession)
                .filter_by(student_id=student_user_id, homework_id=homework_id, is_active=True)
                .order_by(StudentHomeworkSession.id.desc())
                .first()
            )
            if session and session.status in ("in_progress", "paused"):
                if session.status == "paused":
                    session.status = "in_progress"
                    session.last_resumed_at = now
                tenant_session.commit()
                tenant_session.refresh(session)
                return cls._response("Session resumed successfully", cls._with_questions(session, homework))
            if session and session.status in ("submitted", "graded"):
                return cls._response(
                    "Homework already submitted. You can view your result but cannot edit this session.",
                    cls._with_questions(session, homework),
                )

            today = cls._local_today()
            if homework.homework_date and homework.homework_date < today:
                return cls._error(f"This homework was for {homework.homework_date.strftime('%d %b')}. Past homework can only be viewed.", 403)
            if homework.homework_date and homework.homework_date > today:
                return cls._error(f"This homework opens on {homework.homework_date.strftime('%d %b')}.", 403)

            session = StudentHomeworkSession(
                student_id=student_user_id,
                homework_id=homework_id,
                status="in_progress",
                started_at=now,
                last_resumed_at=now,
                active_duration_seconds=0,
                hints_used_count=0,
                submission_image_paths=[],
                ai_feedback_json={},
                integrity_json={},
                is_active=True,
            )
            tenant_session.add(session)
            tenant_session.commit()
            tenant_session.refresh(session)
            return cls._response("Session started successfully", cls._with_questions(session, homework), 201)

    @classmethod
    def _with_questions(cls, session, homework) -> Dict[str, Any]:
        """The session plus the homework's questions (shown from the moment the student starts)."""
        data = cls._session_to_dict(session)
        data["homework"] = cls._homework_to_dict(homework, session.status, include_answer_key=False)
        return data

    @classmethod
    def toggle_pause(cls, skid: str, student_user_id: int, session_id: int):
        with switch_to_institution_db(skid) as tenant_session:
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
        student_images: Optional[Sequence[Tuple[bytes, str]]] = None,
    ):
        with switch_to_institution_db(skid) as tenant_session:
            cls._ensure_tables(tenant_session)
            session = tenant_session.query(StudentHomeworkSession).filter_by(
                id=session_id, student_id=student_user_id, is_active=True
            ).first()
            if not session:
                return cls._error("Session not found", 404)
            if session.status not in ("in_progress", "paused"):
                return cls._error("Hints are available only for active sessions", 400)
            if session.status == "paused":  # hints used to work while paused (QA D15)
                return cls._error("Resume the homework to ask for a hint", 400)

            homework = tenant_session.query(Homework).filter_by(id=session.homework_id, is_active=True).first()
            if not homework:
                return cls._error("Homework not found", 404)

            try:
                hint_text = HomeworkGeminiService.generate_socratic_hint(
                    homework_title=homework.title,
                    homework_description=homework.description,
                    student_doubt=student_doubt,
                    student_images=student_images,
                    instruction_images=load_images(homework.instruction_image_paths),
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
        images: Sequence[Tuple[bytes, str]],
    ):
        with switch_to_institution_db(skid) as tenant_session:
            cls._ensure_tables(tenant_session)
            session = tenant_session.query(StudentHomeworkSession).filter_by(
                id=session_id, student_id=student_user_id, is_active=True
            ).first()
            if not session:
                return cls._error("Session not found", 404)
            if session.status not in ("in_progress", "paused"):
                return cls._error("Session is already submitted", 400)

            homework = tenant_session.query(Homework).filter_by(id=session.homework_id, is_active=True).first()
            if not homework:
                return cls._error("Homework not found", 404)
            if not images:
                return cls._error("At least one image is required", 422)

            # The finished pages must include the page the homework was started on (same QR sticker).
            # Sessions started before page QRs existed have none and skip this check.
            qr_matched = None
            if session.page_qr_code:
                found = set()
                for raw, _mime in images:
                    try:
                        found.update(read_qr_codes(raw))
                    except QrReadError:
                        continue
                if session.page_qr_code not in found:
                    if found:
                        return cls._error("This isn't the page you started on: the QR sticker in your photos is different. Upload the page you photographed at the start.", 403)
                    return cls._error("Couldn't find the page's QR sticker in your photos. Include a clear photo of the page you started on, with the whole sticker visible.", 403)
                qr_matched = True
            start_image = load_images([session.start_image_path]) if session.start_image_path else []

            # Work out the final active time without touching the session yet: if grading fails,
            # nothing is saved (this used to add the time again on every failed retry).
            now = cls._utc_now()
            active_seconds = session.active_duration_seconds
            if session.status == "in_progress" and session.last_resumed_at:
                active_seconds += int((now - session.last_resumed_at).total_seconds())

            try:
                grading = HomeworkGeminiService.grade_submission(
                    homework={
                        "title": homework.title,
                        "subject": homework.subject,
                        "description": homework.description,
                        "reference_answer_key": homework.reference_answer_key,
                        "expected_time_minutes": homework.expected_time_minutes,
                    },
                    images=images,
                    active_duration_seconds=active_seconds,
                    hints_used_count=session.hints_used_count,
                    instruction_images=load_images(homework.instruction_image_paths),
                    start_image=start_image[0] if start_image else None,
                )
            except Exception as exc:
                return cls._error(f"AI grading failed: {exc}", 500)

            # Page checks: the QR is checked above; the AI says whether the page was blank at the start and
            # whether the finished page is the same page. Those two don't block - they flag it for the teacher.
            blank_at_start = grading.pop("page_blank_at_start", None) if start_image else None
            same_page = grading.pop("same_page_as_start", None) if start_image else None
            notes = grading.pop("page_check_notes", "") if start_image else ""
            integrity = {
                # fingerprints of the submitted pages, for the teacher's "same photo as another student" check
                "page_hashes": [h for h in (page_fingerprint(raw) for raw, _m in images) if h],
                "qr_matched": qr_matched,
                "page_blank_at_start": blank_at_start,
                "same_page_as_start": same_page,
                "notes": notes,
                "flagged": blank_at_start is False or same_page is False,
            }

            # Only now save the pages (no orphaned files when grading fails)
            session_dir = _upload_root() / str(skid) / str(session.id)
            saved_paths: List[str] = []
            try:
                session_dir.mkdir(parents=True, exist_ok=True)
                for raw, mime in images:
                    full_path = session_dir / f"{uuid.uuid4().hex}{_EXTENSIONS.get(mime, '.jpg')}"
                    full_path.write_bytes(raw)
                    saved_paths.append(str(full_path))
            except OSError as exc:
                shutil.rmtree(session_dir, ignore_errors=True)
                return cls._error(f"Couldn't save the uploaded pages: {exc}", 500)

            accuracy_score = max(0.0, min(100.0, float(grading.get("accuracy_score", 0))))
            efficiency_score = cls._compute_efficiency_score(
                accuracy_score,
                homework.expected_time_minutes,
                active_seconds,
                session.hints_used_count,
            )

            session.active_duration_seconds = active_seconds
            session.status = "graded"
            session.submitted_at = now
            session.last_resumed_at = None
            session.submission_image_paths = saved_paths
            session.accuracy_score = round(accuracy_score, 2)
            session.efficiency_score = efficiency_score
            session.ai_feedback_json = grading
            session.integrity_json = integrity
            tenant_session.commit()
            tenant_session.refresh(session)

            return cls._response(
                "Homework submitted and graded successfully",
                {"session": cls._session_to_dict(session), "grading": grading},
            )

    @classmethod
    def latest_session(cls, skid: str, student_user_id: int, homework_id: int):
        with switch_to_institution_db(skid) as tenant_session:
            cls._ensure_tables(tenant_session)
            homework = tenant_session.query(Homework).filter_by(id=homework_id, is_active=True).first()
            if not homework:
                return cls._error("Homework not found", 404)
            if homework.section_id != student_section_id(tenant_session, student_user_id):
                return cls._error("This homework isn't for your class", 403)
            session = (
                tenant_session.query(StudentHomeworkSession)
                .filter_by(student_id=student_user_id, homework_id=homework_id, is_active=True)
                .order_by(StudentHomeworkSession.id.desc())
                .first()
            )
            if not session:
                return cls._response("No homework session found", None)
            return cls._response("Latest session fetched successfully", cls._with_questions(session, homework))

    @classmethod
    def session_photo(cls, skid: str, session_id: int, kind: str, index: int, current_user):
        """
        A session's photo: kind 'start' (the blank page) or 'page' (finished pages, by index).
        For the student who owns it, and for staff who may see that section. Returns (path, mime, error).
        """
        with switch_to_institution_db(skid) as tenant_session:
            cls._ensure_tables(tenant_session)
            session = tenant_session.query(StudentHomeworkSession).filter_by(id=session_id, is_active=True).first()
            if not session:
                return None, None, cls._error("Session not found", 404)
            if cls._role(current_user) == cls.STUDENT_ROLE:
                if session.student_id != current_user.institution_user_id:
                    return None, None, cls._error("Session not found", 404)
            else:
                homework = tenant_session.query(Homework).filter_by(id=session.homework_id).first()
                allowed = cls._teacher_sections(tenant_session, current_user)
                if allowed is not None and (not homework or homework.section_id not in allowed):
                    return None, None, cls._error("You can only view homework of sections you teach", 403)
            if kind == "start":
                path = session.start_image_path if index == 0 else None
            elif kind == "page":
                paths = session.submission_image_paths or []
                path = paths[index] if 0 <= index < len(paths) else None
            else:
                path = None
            if not path:
                return None, None, cls._error("Photo not found", 404)
            full = Path(path).resolve()
            if _upload_root() not in full.parents or not full.is_file():
                return None, None, cls._error("Photo not found", 404)
            raw = full.read_bytes()[:16]
            return str(full), image_type(raw) or _MIME_BY_EXT.get(full.suffix.lower(), "image/jpeg"), None

    # ------------------------------------------------------------------ analytics
    @classmethod
    def homework_analytics(cls, skid: str, homework_id: int, current_user):
        with switch_to_institution_db(skid) as tenant_session:
            cls._ensure_tables(tenant_session)
            homework = tenant_session.query(Homework).filter_by(id=homework_id, is_active=True).first()
            if not homework:
                return cls._error("Homework not found", 404)
            allowed = cls._teacher_sections(tenant_session, current_user)
            if allowed is not None and homework.section_id not in allowed:
                return cls._error("You can only view analytics for sections you teach", 403)

            sessions = tenant_session.query(StudentHomeworkSession).filter_by(homework_id=homework_id, is_active=True).all()
            names = {u.id: f"{u.first_name} {u.last_name or ''}".strip() for u in tenant_session.query(InstitutionUsers).filter(
                InstitutionUsers.id.in_([s.student_id for s in sessions] or [-1])).all()}
            total = len(sessions)
            submitted = [s for s in sessions if s.status in ("submitted", "graded")]
            graded = [s for s in sessions if s.status == "graded"]
            completed = len(submitted)

            avg_active = round(sum(s.active_duration_seconds for s in sessions) / total, 2) if total else 0
            avg_accuracy = round(sum((s.accuracy_score or 0) for s in graded) / len(graded), 2) if graded else 0
            avg_efficiency = round(sum((s.efficiency_score or 0) for s in graded) / len(graded), 2) if graded else 0

            flags = cls._integrity_flags(homework, sessions, names)

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
                "Homework analytics fetched successfully",
                {
                    "homework": cls._homework_to_dict(homework),
                    "homework_id": homework_id,
                    "total_sessions": total,
                    "submitted_count": completed,
                    "completion_rate": round((completed / total) * 100, 2) if total else 0,
                    "expected_time_minutes": homework.expected_time_minutes,
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
                            "submitted_at": _utc_iso(s.submitted_at),
                            "ai_feedback_json": s.ai_feedback_json or {},
                            "student_name": names.get(s.student_id),
                            "has_start_photo": bool(s.start_image_path),
                            "page_count": len(s.submission_image_paths or []),
                            "integrity": {**{k: v for k, v in (s.integrity_json or {}).items() if k != "page_hashes"},
                                          **flags.get(s.id, {})},
                            # handed in after the due date: accepted, but flagged (owner's choice - QA D15)
                            "is_late": cls._is_late(homework, s),
                        }
                        for s in sessions
                    ],
                    "common_conceptual_mistakes": [
                        {"mistake": key, "count": value} for key, value in mistakes.most_common(10)
                    ],
                },
            )

    @classmethod
    def _integrity_flags(cls, homework, sessions, names) -> Dict[int, Dict[str, Any]]:
        """
        Per handed-in session: fast_finish (far quicker than the class usually takes) and same_photo_with
        (names of students whose page photo is nearly identical). Both only flag for the teacher.
        """
        done = [s for s in sessions if s.status in ("submitted", "graded")]
        out: Dict[int, Dict[str, Any]] = {}
        for s in done:
            others = [s2.active_duration_seconds or 0 for s2 in done if s2.id != s.id]
            if len(others) >= 3:
                others.sort()
                median = others[len(others) // 2]
                limit = median * FAST_SHARE_OF_MEDIAN
                basis = f"the class usually takes about {max(1, round(median / 60))} min"
            else:
                limit = (homework.expected_time_minutes or 15) * 60 * FAST_SHARE_OF_EXPECTED
                basis = f"expected about {homework.expected_time_minutes} min"
            fast = (s.active_duration_seconds or 0) < limit
            same = []
            mine = (s.integrity_json or {}).get("page_hashes") or []
            for s2 in done:
                if s2.id == s.id or s2.student_id == s.student_id:
                    continue
                theirs = (s2.integrity_json or {}).get("page_hashes") or []
                if any(_fingerprint_distance(a, b) <= SAME_PHOTO_MAX_DISTANCE for a in mine for b in theirs):
                    same.append(names.get(s2.student_id) or "another student")
            entry: Dict[str, Any] = {}
            if fast:
                entry["fast_finish"] = True
                entry["fast_finish_note"] = f"Finished in {max(1, round((s.active_duration_seconds or 0) / 60))} min; {basis}"
            if same:
                entry["same_photo_with"] = sorted(set(same))
            if entry:
                entry["flagged"] = True
            out[s.id] = entry
        return out

    # ------------------------------------------------------------------ subjects of a section
    @classmethod
    def _section_subjects(cls, tenant_session, section_id: int, current_user) -> List[Dict[str, Any]]:
        """
        Subjects of a section: the ones added to it (Class Management) plus any taught there in a
        published timetable. A teacher only gets the subjects they teach in that section.
        """
        from app.models.tenant.SectionSubject import SectionSubject
        from app.models.tenant.Subject import Subject
        from app.models.tenant.TimeTable import Timetable
        from app.models.tenant.TimeTableEntry import TimetableEntry
        from app.utils.teaching_scope import teaches

        ids = {sid for (sid,) in tenant_session.query(SectionSubject.subject_id).filter(
            SectionSubject.section_id == section_id, SectionSubject.is_active.isnot(False))}
        ids |= {sid for (sid,) in tenant_session.query(TimetableEntry.subject_id).join(
            Timetable, TimetableEntry.timetable_id == Timetable.id
        ).filter(
            Timetable.section_id == section_id,
            Timetable.is_active.is_(True),
            Timetable.is_draft.isnot(True),
            TimetableEntry.is_active.is_(True),
            TimetableEntry.subject_id.isnot(None),
        )}
        if cls._role(current_user) not in cls.STAFF_UNRESTRICTED:
            ids = {sid for sid in ids if teaches(tenant_session, current_user.institution_user_id, section_id, sid)}
        subjects = tenant_session.query(Subject).filter(Subject.id.in_(ids or [-1])).order_by(Subject.subject_name).all()
        return [{"id": s.id, "subject_name": s.subject_name, "subject_code": s.subject_code} for s in subjects]

    @classmethod
    def section_subjects(cls, skid: str, section_id: int, current_user):
        with switch_to_institution_db(skid) as tenant_session:
            if not tenant_session.query(Section).filter_by(id=section_id).first():
                return cls._error("Section not found", 404)
            allowed = cls._teacher_sections(tenant_session, current_user)
            if allowed is not None and section_id not in allowed:
                return cls._error("You can only create homework for sections you teach", 403)
            return cls._response("Subjects fetched successfully", cls._section_subjects(tenant_session, section_id, current_user))

    # ------------------------------------------------------------------ scope for the teacher page
    @classmethod
    def teaching_scope(cls, skid: str, current_user):
        """Which classes/sections this user may use on the teacher page (all, for admins)."""
        with switch_to_institution_db(skid) as tenant_session:
            allowed = cls._teacher_sections(tenant_session, current_user)
            query = tenant_session.query(Section, Class).join(Class, Class.id == Section.class_id)
            if allowed is not None:
                query = query.filter(Section.id.in_(allowed or [-1]))
            rows = [
                {"class_id": c.id, "class_name": c.class_name, "section_id": s.id, "section_name": s.section_name}
                for s, c in query.order_by(Class.class_name, Section.section_name).all()
            ]
            return cls._response("Scope fetched successfully", {"all": allowed is None, "sections": rows})
