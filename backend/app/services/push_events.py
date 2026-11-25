"""
Which institution events send a push notification, to whom, and what it says.

Called right after the change is committed, with the caller's still-open tenant session.
Every function here is best-effort: it logs and swallows errors, so a notification problem
can never undo or fail the action itself (saving attendance, publishing results, ...).
"""
import functools
import logging
from datetime import datetime, timedelta

from flask import g

from app.services import push_service as push

_log = logging.getLogger(__name__)

STAFF_ROLES = ("INSTITUTION_ADMIN", "PRINCIPAL", "TEACHER", "CLERK", "BUS_STAFF")


def _best_effort(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            if push.is_configured():
                fn(*args, **kwargs)
        except Exception:
            _log.exception("Push notification for %s failed", fn.__name__)
    return wrapper


def _actor_id():
    """The signed-in user who caused the event: they don't need a notification about their own action."""
    user = getattr(g, "current_user", None)
    return getattr(user, "id", None)


def _send_to_students_and_parents(skid, tenant_session, student_ids, title, body, student_url, parent_url, tag):
    push.notify(push.main_user_ids_for(skid, student_ids), title, body, student_url, tag, exclude_user_id=_actor_id())
    parents = push.parents_of(tenant_session, student_ids)
    push.notify(push.main_user_ids_for(skid, parents), title, body, parent_url, tag, exclude_user_id=_actor_id())


# ---------------------------------------------------------------- announcements

def _audience(value):
    return str(value or "").strip().upper().replace(" ", "_")


@_best_effort
def announcement_published(skid, tenant_session, announcement):
    """Same audience rules as who can read the post (AnnouncementService._filter_by_user_access)."""
    if not announcement.is_published or not announcement.is_active:
        return
    if announcement.publish_date and announcement.publish_date > datetime.utcnow():
        return  # scheduled for later: no scheduler yet, so no notification for these
    audience = _audience(announcement.target_audience)
    title = f"📢 {announcement.title}"
    body = announcement.description
    tag = f"announcement-{announcement.id}"
    url = "/announcements"

    recipients = set()
    if audience in ("ALL", "ALL_USERS"):
        recipients |= push.main_user_ids_for(skid)
    elif audience == "ALL_STUDENTS":
        recipients |= push.main_user_ids_for(skid, roles=("STUDENT",))
    elif audience == "ALL_TEACHERS":
        recipients |= push.main_user_ids_for(skid, roles=("TEACHER",))
    elif audience == "ALL_PARENTS":
        recipients |= push.main_user_ids_for(skid, roles=("PARENT",))
    elif audience in ("SPECIFIC_CLASS", "SPECIFIC_CLASSES"):
        students = push.students_in_classes(tenant_session, announcement.target_classes or [])
        recipients |= push.main_user_ids_for(skid, students | push.parents_of(tenant_session, students))
    elif audience in ("SPECIFIC_SECTION", "SPECIFIC_SECTIONS"):
        students = push.students_in_sections(tenant_session, announcement.target_sections or [])
        recipients |= push.main_user_ids_for(skid, students | push.parents_of(tenant_session, students))
    if announcement.target_users:
        recipients |= push.main_user_ids_for(skid, announcement.target_users)

    push.notify(recipients, title, body, url, tag, exclude_user_id=_actor_id())


# ---------------------------------------------------------------- homework / assignments

@_best_effort
def assignment_created(skid, tenant_session, assignment, subject_name=None):
    """Classic assignment (Assignments page) for one section."""
    students = push.students_in_sections(tenant_session, [assignment.section_id])
    subject = subject_name or "a subject"
    _send_to_students_and_parents(
        skid, tenant_session, students,
        title=f"📝 New {subject} assignment",
        body=f"A new {subject} assignment has been set. Open EduSpyre to see it.",
        student_url="/assignments/my-assignments", parent_url="/parent/assignments",
        tag=f"assignment-{assignment.id}",
    )


@_best_effort
def homework_created(skid, tenant_session, homework):
    """AI homework for one section."""
    students = push.students_in_sections(tenant_session, [homework.section_id])
    _send_to_students_and_parents(
        skid, tenant_session, students,
        title=f"📝 New {homework.subject} homework",
        body=homework.title,
        student_url="/homework/student", parent_url="/dashboard",
        tag=f"homework-{homework.id}",
    )


# ---------------------------------------------------------------- exam results

@_best_effort
def results_published(skid, tenant_session, exam_type_id):
    from app.models.tenant.ExamModels import ExamType

    exam = tenant_session.query(ExamType).filter_by(id=exam_type_id).first()
    name = exam.exam_name if exam else "Exam"
    students = push.all_students(tenant_session)
    _send_to_students_and_parents(
        skid, tenant_session, students,
        title="📊 Results published",
        body=f"{name} results are now available.",  # no marks here: it shows on the lock screen
        student_url="/academics/my-results", parent_url="/parent/results",
        tag=f"results-{exam_type_id}",
    )


# ---------------------------------------------------------------- attendance

def _is_absent(status):
    return str(status or "").strip().upper() == "ABSENT"


@_best_effort
def students_marked_absent(skid, tenant_session, student_ids, day):
    """
    Tell parents their child was marked absent. Only for today / yesterday, so filling in or
    correcting old registers doesn't send a burst of stale alerts.
    """
    from app.models.tenant.InstitutionUsers import InstitutionUsers
    from app.models.tenant.StudentParent import StudentParent

    if not student_ids or day < push.today() - timedelta(days=1) or day > push.today():
        return
    # a day on approved leave isn't an absence to alert anyone about
    from app.services.leave_service import approved_student_leave
    on_leave = approved_student_leave(tenant_session, student_ids, day)
    student_ids = [s for s in student_ids if int(s) not in on_leave]
    if not student_ids:
        return
    names = dict(tenant_session.query(InstitutionUsers.id, InstitutionUsers.first_name).filter(
        InstitutionUsers.id.in_([int(s) for s in student_ids])
    ).all())
    links = tenant_session.query(StudentParent.student_user_id, StudentParent.parent_user_id).filter(
        StudentParent.student_user_id.in_([int(s) for s in student_ids])
    ).all()
    when = "today" if day == push.today() else "yesterday"
    for student_id, parent_id in links:
        name = (names.get(student_id) or "Your child").strip()
        push.notify(
            push.main_user_ids_for(skid, [parent_id]),
            title="Attendance",
            body=f"{name} was marked absent {when} ({day.strftime('%d %b')}).",
            url="/parent/attendance",
            tag=f"absent-{student_id}-{day.isoformat()}",
            urgency="high",
        )


def newly_absent(records_before, records_after):
    """Student ids that are ABSENT now and weren't before (both: {student_id: status})."""
    return [sid for sid, status in records_after.items()
            if _is_absent(status) and not _is_absent(records_before.get(sid))]


# ---------------------------------------------------------------- leave

def _short_range(start, end):
    if start == end:
        return start.strftime('%d %b')
    return f"{start.strftime('%d %b')} - {end.strftime('%d %b')}"


@_best_effort
def leave_requested(skid, tenant_session, leave):
    """New leave request -> the people who can decide it (class teacher, or admins / "approve_leave")."""
    from app.services.leave_service import approver_user_ids, _names
    approvers = approver_user_ids(tenant_session, leave)
    if not approvers:
        return
    names = _names(tenant_session, [leave.user_id, leave.applied_by])
    who = (names.get(leave.user_id) or "Someone").split(" ")[0]
    if leave.applicant_type == "STUDENT" and leave.applied_by != leave.user_id:
        who = f"{who}'s parent"
    days = (leave.to_date - leave.from_date).days + 1
    # no reason in the text: it shows on the lock screen
    push.notify(
        push.main_user_ids_for(skid, approvers),
        title="Leave request",
        body=f"{who} asked for leave: {_short_range(leave.from_date, leave.to_date)} ({days} day{'s' if days != 1 else ''}).",
        url="/leave/requests",
        tag=f"leave-request-{leave.id}",
        exclude_user_id=_actor_id(),
    )


@_best_effort
def leave_decided(skid, tenant_session, leave):
    """Approved / rejected -> the person on leave, whoever applied, and (student leave) the parents."""
    from app.services.leave_service import _names
    people = {leave.user_id, leave.applied_by}
    if leave.applicant_type == "STUDENT":
        people |= push.parents_of(tenant_session, [leave.user_id])
    name = (_names(tenant_session, [leave.user_id]).get(leave.user_id) or "").split(" ")[0]
    whose = "Your" if leave.applicant_type == "STAFF" else f"{name}'s" if name else "The"
    outcome = "approved ✅" if leave.status == "APPROVED" else "not approved"
    push.notify(
        push.main_user_ids_for(skid, people),
        title="Leave update",
        body=f"{whose} leave for {_short_range(leave.from_date, leave.to_date)} was {outcome}.",
        url="/leave/my",
        tag=f"leave-{leave.id}",
        exclude_user_id=_actor_id(),
    )
