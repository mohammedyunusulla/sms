"""
Teaching scope rules for TEACHER users.

What a teacher teaches is set by the school admin in two places:
  * Assign Subjects page -> teacher_subjects (teacher -> subject), combined with
    section_subjects (which subjects each section has)
  * a published timetable -> timetable_entries (teacher, subject) in a section's timetable

Admins, principals and super admins are never restricted by these rules.
"""
from flask import jsonify, request
from sqlalchemy import func

from app.utils.db_manager import switch_to_school_db
from app.models.tenant.StudentEnrollment import StudentEnrollment
from app.models.tenant.Sections import Section
from app.models.tenant.TeacherSubject import TeacherSubject
from app.models.tenant.SectionSubject import SectionSubject
from app.models.tenant.TimeTable import Timetable
from app.models.tenant.TimeTableEntry import TimetableEntry
from app.models.tenant.Student import Student
from app.models.tenant.Syllabus import Syllabus
from app.models.tenant.TeacherSyllabusAssignment import TeacherSyllabusAssignment
from app.models.tenant.Lesson import Lesson
from app.models.tenant.Topic import Topic
from app.models.tenant.Subtopic import Subtopic


def current_teacher_id():
    """school_user id of the logged-in user if they are a TEACHER, else None (unrestricted)."""
    user = getattr(request, 'current_user', None)
    if not user:
        return None
    role = user.role.value if hasattr(user.role, 'value') else str(user.role)
    return user.school_user_id if role == 'TEACHER' else None


def forbidden(message):
    return jsonify({'message': message, 'status': 'error', 'code': 403}), 403


def is_class_teacher(session, teacher_id, section_id):
    section = session.query(Section).filter_by(id=int(section_id)).first()
    return bool(section and section.teacher_id == int(teacher_id))


def teaches(session, teacher_id, section_id, subject_id):
    """Teacher teaches subject in section via Assign Subjects (+ section has it) or a published timetable."""
    teacher_id, section_id, subject_id = int(teacher_id), int(section_id), int(subject_id)
    assigned = session.query(TeacherSubject).filter_by(teacher_id=teacher_id, subject_id=subject_id).first()
    if assigned and session.query(SectionSubject).filter(
        SectionSubject.section_id == section_id,
        SectionSubject.subject_id == subject_id,
        SectionSubject.is_active.isnot(False),
    ).first():
        return True
    return session.query(TimetableEntry).join(Timetable, TimetableEntry.timetable_id == Timetable.id).filter(
        TimetableEntry.teacher_id == teacher_id,
        TimetableEntry.subject_id == subject_id,
        TimetableEntry.is_active.is_(True),
        Timetable.section_id == section_id,
        Timetable.is_active.is_(True),
        Timetable.is_draft.isnot(True),
    ).first() is not None


def student_section_id(session, student_id):
    """
    The student's current section: their active enrollment (what class lists are built from),
    falling back to students.section_id when there is no active enrollment.
    """
    if student_id is None:
        return None
    enrollment = session.query(StudentEnrollment).filter(
        StudentEnrollment.student_id == int(student_id),
        func.lower(StudentEnrollment.status) == 'active',
    ).order_by(StudentEnrollment.id.desc()).first()
    if enrollment and enrollment.section_id:
        return enrollment.section_id
    student = session.query(Student).filter_by(user_id=int(student_id)).first()
    return student.section_id if student else None


def syllabus_id_for_item(session, item_type, item_id):
    """Resolve a syllabus item (syllabus/lesson/topic/subtopic) to its syllabus id."""
    item_id = int(item_id)
    if item_type == 'syllabus':
        return item_id
    if item_type == 'lesson':
        lesson = session.query(Lesson).filter_by(id=item_id).first()
        return lesson.syllabus_id if lesson else None
    if item_type == 'topic':
        topic = session.query(Topic).filter_by(id=item_id).first()
        return syllabus_id_for_item(session, 'lesson', topic.lesson_id) if topic else None
    if item_type == 'subtopic':
        subtopic = session.query(Subtopic).filter_by(id=item_id).first()
        return syllabus_id_for_item(session, 'topic', subtopic.topic_id) if subtopic else None
    return None


def can_manage_syllabus(session, teacher_id, syllabus_id):
    """Teacher created the syllabus or is (actively) assigned to it."""
    if syllabus_id is None:
        return False
    syllabus = session.query(Syllabus).filter_by(id=int(syllabus_id)).first()
    if not syllabus:
        return False
    if syllabus.created_by == int(teacher_id):
        return True
    return session.query(TeacherSyllabusAssignment).filter_by(
        syllabus_id=int(syllabus_id), teacher_id=int(teacher_id), is_active=True
    ).first() is not None


def check_syllabus_item(skid, item_type, item_id):
    """Route guard: returns a 403 response if the current teacher may not manage this item, else None."""
    teacher_id = current_teacher_id()
    if teacher_id is None:
        return None
    try:
        with switch_to_school_db(skid) as session:
            allowed = can_manage_syllabus(session, teacher_id, syllabus_id_for_item(session, item_type, item_id))
    except (TypeError, ValueError):
        allowed = False
    if not allowed:
        return forbidden('You can only edit syllabi you created or are assigned to')
    return None
