"""
One rule for a student's class/section placement.

Class lists, attendance and counts are built from the student's enrollment for the academic year,
while the student profile (students.class_id / section_id) holds the "current" placement. Every
action that changes a student's section goes through these helpers so the two always agree, and
only the CURRENT academic year's active enrollment is ever changed (older years are history).
Moving to another year is Promote's job (it also records promotion_history).
"""
from datetime import date

from sqlalchemy import func

from app.models.tenant.AcademicYear import AcademicYear
from app.models.tenant.Sections import Section
from app.models.tenant.StudentEnrollment import StudentEnrollment


def current_year_id(session):
    year = session.query(AcademicYear).filter_by(is_current=True).first()
    return year.id if year else None


def current_enrollment(session, student_id, year_id=None):
    """The student's active enrollment for the given (default: current) academic year, or None."""
    year_id = year_id if year_id is not None else current_year_id(session)
    query = session.query(StudentEnrollment).filter(
        StudentEnrollment.student_id == int(student_id),
        func.lower(StudentEnrollment.status) == "active",
    )
    if year_id is not None:
        query = query.filter(StudentEnrollment.academic_year_id == year_id)
    return query.order_by(StudentEnrollment.id.desc()).first()


def place_student(session, student, section_id, year_id=None):
    """
    Put the student in this section for the current year: update their current-year enrollment,
    or create one if they have none, and keep the profile in step. Returns the enrollment.
    """
    section = session.query(Section).filter_by(id=int(section_id)).first()
    if not section:
        raise ValueError("Section not found")
    year_id = year_id if year_id is not None else current_year_id(session)
    enrollment = current_enrollment(session, student.user_id, year_id)
    if not enrollment and year_id is not None:
        # Already promoted/detained out of this year: their placement for this year is closed
        closed = session.query(StudentEnrollment).filter(
            StudentEnrollment.student_id == student.user_id,
            StudentEnrollment.academic_year_id == year_id,
            func.lower(StudentEnrollment.status).in_(["promoted", "detained"]),
        ).first()
        if closed:
            raise ValueError(
                "This student was already promoted out of the current academic year. "
                "Change their section in the new year's class list instead."
            )
    if enrollment:
        enrollment.class_id = section.class_id
        enrollment.section_id = section.id
    else:
        enrollment = StudentEnrollment(
            student_id=student.user_id,
            class_id=section.class_id,
            section_id=section.id,
            academic_year_id=year_id,
            enrollment_date=date.today(),
            status="active",
        )
        session.add(enrollment)
    student.class_id = section.class_id
    student.section_id = section.id
    return enrollment


def unplace_student(session, student, section_id=None, year_id=None, keep_class=False):
    """
    Take the student out of their current-year section (only that enrollment; older years stay).
    With section_id, only if they are in that section. keep_class: they stay in their class with no section
    (Remove from section used to clear the class too, so the student vanished from it - QA A30).
    Returns True if anything changed.
    """
    enrollment = current_enrollment(session, student.user_id, year_id)
    changed = False
    if enrollment and (section_id is None or enrollment.section_id == int(section_id)):
        session.delete(enrollment)
        changed = True
    if section_id is None or student.section_id == int(section_id):
        if student.section_id is not None or (student.class_id is not None and not keep_class):
            changed = True
        if not keep_class:
            student.class_id = None
        student.section_id = None
    return changed


def current_section_count(session, section_id, year_id=None):
    """
    Students enrolled in this section for the current year - the same rule as the class list
    (which also shows students promoted/detained at the end of that year).
    """
    year_id = year_id if year_id is not None else current_year_id(session)
    query = session.query(func.count(func.distinct(StudentEnrollment.student_id))).filter(
        StudentEnrollment.section_id == int(section_id),
    )
    if year_id is not None:
        query = query.filter(StudentEnrollment.academic_year_id == year_id)
    return query.scalar() or 0
