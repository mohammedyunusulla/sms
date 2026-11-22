from app.utils.db_manager import switch_to_school_db
from app.models.tenant.Assignment import Assignment
from app.models.tenant.AssignmentSubmission import AssignmentSubmission
from app.models.tenant.Student import Student
from app.models.tenant.SchoolUsers import SchoolUsers
from app.models.tenant.Subject import Subject
from app.models.tenant.Class import Class
from app.models.tenant.Sections import Section
from app.models.tenant.TimeTableEntry import TimetableEntry
from app.models.tenant.TimeTable import Timetable
from sqlalchemy import and_, distinct, func
from datetime import datetime


class AssignmentService:

    @staticmethod
    def get_teacher_class_subjects(skid, teacher_id):
        """
        Get unique class/section/subject combos assigned to a teacher via timetable.
        Returns a list of dicts with class, section, and subject info.
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                results = tenant_session.query(
                    Class.id.label('class_id'),
                    Class.class_name,
                    Section.id.label('section_id'),
                    Section.section_name,
                    Subject.id.label('subject_id'),
                    Subject.subject_name,
                ).select_from(
                    TimetableEntry
                ).join(
                    Timetable, TimetableEntry.timetable_id == Timetable.id
                ).join(
                    Class, Timetable.class_id == Class.id
                ).join(
                    Section, Timetable.section_id == Section.id
                ).join(
                    Subject, TimetableEntry.subject_id == Subject.id
                ).filter(
                    and_(
                        TimetableEntry.teacher_id == teacher_id,
                        TimetableEntry.is_active == True
                    )
                ).distinct().all()

                combos = []
                seen = set()
                for r in results:
                    key = (r.class_id, r.section_id, r.subject_id)
                    if key not in seen:
                        seen.add(key)
                        combos.append({
                            'class_id': r.class_id,
                            'class_name': r.class_name,
                            'section_id': r.section_id,
                            'section_name': r.section_name,
                            'subject_id': r.subject_id,
                            'subject_name': r.subject_name,
                        })

                return combos

        except Exception as e:
            raise Exception(f"Failed to fetch teacher class-subjects: {str(e)}")

    @staticmethod
    def create_assignment(data, skid):
        """Create a new assignment."""
        try:
            with switch_to_school_db(skid) as tenant_session:
                assignment = Assignment(
                    teacher_id=data['teacher_id'],
                    class_id=data['class_id'],
                    section_id=data['section_id'],
                    subject_id=data['subject_id'],
                    academic_year_id=data['academic_year_id'],
                    assignment_text=data.get('assignment_text', ''),
                    assignment_drawing=data.get('assignment_drawing'),
                    assignment_date=datetime.strptime(data['assignment_date'], '%Y-%m-%d').date(),
                )
                tenant_session.add(assignment)
                tenant_session.commit()
                tenant_session.refresh(assignment)

                # Fetch related names for response
                result = tenant_session.query(
                    Assignment,
                    Class.class_name,
                    Section.section_name,
                    Subject.subject_name,
                ).join(
                    Class, Assignment.class_id == Class.id
                ).join(
                    Section, Assignment.section_id == Section.id
                ).join(
                    Subject, Assignment.subject_id == Subject.id
                ).filter(
                    Assignment.id == assignment.id
                ).first()

                assignment_dict = result[0].to_dict()
                assignment_dict['class_name'] = result.class_name
                assignment_dict['section_name'] = result.section_name
                assignment_dict['subject_name'] = result.subject_name

                return assignment_dict

        except Exception as e:
            raise Exception(f"Failed to create assignment: {str(e)}")

    @staticmethod
    def update_assignment(skid, assignment_id, data):
        """Update an existing assignment's text."""
        try:
            with switch_to_school_db(skid) as tenant_session:
                assignment = tenant_session.query(Assignment).filter(
                    and_(Assignment.id == assignment_id, Assignment.is_active == True)
                ).first()

                if not assignment:
                    raise ValueError("Assignment not found")

                if 'assignment_text' in data:
                    assignment.assignment_text = data['assignment_text']
                if 'assignment_drawing' in data:
                    assignment.assignment_drawing = data['assignment_drawing']

                tenant_session.commit()
                tenant_session.refresh(assignment)

                # Fetch related names
                result = tenant_session.query(
                    Assignment,
                    Class.class_name,
                    Section.section_name,
                    Subject.subject_name,
                ).join(
                    Class, Assignment.class_id == Class.id
                ).join(
                    Section, Assignment.section_id == Section.id
                ).join(
                    Subject, Assignment.subject_id == Subject.id
                ).filter(
                    Assignment.id == assignment.id
                ).first()

                assignment_dict = result[0].to_dict()
                assignment_dict['class_name'] = result.class_name
                assignment_dict['section_name'] = result.section_name
                assignment_dict['subject_name'] = result.subject_name

                return assignment_dict

        except ValueError as ve:
            raise ve
        except Exception as e:
            raise Exception(f"Failed to update assignment: {str(e)}")

    @staticmethod
    def get_assignments_by_date(skid, teacher_id, date, academic_year_id):
        """Get all assignments for a teacher on a specific date."""
        try:
            with switch_to_school_db(skid) as tenant_session:
                assignment_date = datetime.strptime(date, '%Y-%m-%d').date()

                results = tenant_session.query(
                    Assignment,
                    Class.class_name,
                    Section.section_name,
                    Subject.subject_name,
                ).join(
                    Class, Assignment.class_id == Class.id
                ).join(
                    Section, Assignment.section_id == Section.id
                ).join(
                    Subject, Assignment.subject_id == Subject.id
                ).filter(
                    and_(
                        Assignment.teacher_id == teacher_id,
                        Assignment.assignment_date == assignment_date,
                        Assignment.academic_year_id == academic_year_id,
                        Assignment.is_active == True
                    )
                ).order_by(Assignment.created_at.desc()).all()

                assignments = []
                for row in results:
                    assignment_dict = row[0].to_dict()
                    assignment_dict['class_name'] = row.class_name
                    assignment_dict['section_name'] = row.section_name
                    assignment_dict['subject_name'] = row.subject_name

                    # Completion stats: the section's ACTIVE students only, both for "done" and the total
                    # (done counted rows from any section and the total included inactive students - QA D13)
                    from app.models.tenant.SchoolUsers import SchoolUsers
                    section_students = tenant_session.query(Student.user_id).join(
                        SchoolUsers, SchoolUsers.id == Student.user_id
                    ).filter(Student.section_id == row[0].section_id, SchoolUsers.is_active.is_(True))
                    student_count = section_students.count()
                    completed = tenant_session.query(func.count(AssignmentSubmission.id)).filter(
                        AssignmentSubmission.assignment_id == row[0].id,
                        AssignmentSubmission.is_completed == True,
                        AssignmentSubmission.student_id.in_(section_students.subquery().select()),
                    ).scalar() or 0

                    assignment_dict['completion_stats'] = {
                        'total': student_count,
                        'completed': completed,
                        'pending': student_count - completed,
                    }

                    assignments.append(assignment_dict)

                return assignments

        except Exception as e:
            raise Exception(f"Failed to fetch assignments: {str(e)}")

    @staticmethod
    def get_assignment_with_students(skid, assignment_id):
        """Get an assignment along with the student list and their submission status."""
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Get assignment details
                result = tenant_session.query(
                    Assignment,
                    Class.class_name,
                    Section.section_name,
                    Subject.subject_name,
                ).join(
                    Class, Assignment.class_id == Class.id
                ).join(
                    Section, Assignment.section_id == Section.id
                ).join(
                    Subject, Assignment.subject_id == Subject.id
                ).filter(
                    and_(Assignment.id == assignment_id, Assignment.is_active == True)
                ).first()

                if not result:
                    raise ValueError("Assignment not found")

                assignment = result[0]
                assignment_dict = assignment.to_dict()
                assignment_dict['class_name'] = result.class_name
                assignment_dict['section_name'] = result.section_name
                assignment_dict['subject_name'] = result.subject_name

                # Get students in the section
                students = tenant_session.query(
                    Student.user_id,
                    Student.roll_no,
                    SchoolUsers.first_name,
                    SchoolUsers.last_name,
                ).join(
                    SchoolUsers, Student.user_id == SchoolUsers.id
                ).filter(
                    and_(
                        Student.section_id == assignment.section_id,
                        SchoolUsers.is_active == True
                    )
                ).order_by(Student.roll_no).all()

                # Get existing submissions
                submissions = tenant_session.query(AssignmentSubmission).filter(
                    AssignmentSubmission.assignment_id == assignment_id
                ).all()
                submission_map = {s.student_id: s for s in submissions}

                student_list = []
                for student in students:
                    sub = submission_map.get(student.user_id)
                    student_list.append({
                        'student_id': student.user_id,
                        'student_name': f"{student.first_name} {student.last_name}",
                        'roll_no': student.roll_no or '',
                        'is_completed': sub.is_completed if sub else False,
                        'remarks': sub.remarks if sub else '',
                    })

                assignment_dict['students'] = student_list
                assignment_dict['completion_stats'] = {
                    'total': len(student_list),
                    'completed': sum(1 for s in student_list if s['is_completed']),
                    'pending': sum(1 for s in student_list if not s['is_completed']),
                }

                return assignment_dict

        except ValueError as ve:
            raise ve
        except Exception as e:
            raise Exception(f"Failed to fetch assignment details: {str(e)}")

    @staticmethod
    def update_submissions(skid, assignment_id, submissions_data, reviewer_id):
        """Bulk update student submission status and remarks."""
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Verify assignment exists
                assignment = tenant_session.query(Assignment).filter(
                    and_(Assignment.id == assignment_id, Assignment.is_active == True)
                ).first()

                if not assignment:
                    raise ValueError("Assignment not found")

                now = datetime.utcnow()

                # Only students of the assignment's section can be marked (any student used to be accepted - QA D13)
                from app.models.tenant.SchoolUsers import SchoolUsers
                in_section = {uid for (uid,) in tenant_session.query(Student.user_id).filter(
                    Student.section_id == assignment.section_id)}
                outside = [e.get('student_id') for e in submissions_data if int(e.get('student_id') or 0) not in in_section]
                if outside:
                    names = [f"{u.first_name} {u.last_name or ''}".strip() for u in
                             tenant_session.query(SchoolUsers).filter(SchoolUsers.id.in_([int(x or 0) for x in outside])).all()]
                    raise ValueError(f"Not in this assignment's section: {', '.join(names) or ', '.join(map(str, outside))}")

                for entry in submissions_data:
                    student_id = entry['student_id']
                    is_completed = entry.get('is_completed', False)
                    remarks = entry.get('remarks', '')

                    existing = tenant_session.query(AssignmentSubmission).filter(
                        and_(
                            AssignmentSubmission.assignment_id == assignment_id,
                            AssignmentSubmission.student_id == student_id
                        )
                    ).first()

                    if existing:
                        existing.is_completed = is_completed
                        existing.remarks = remarks
                        existing.reviewed_by = reviewer_id
                        existing.reviewed_at = now
                    else:
                        new_sub = AssignmentSubmission(
                            assignment_id=assignment_id,
                            student_id=student_id,
                            is_completed=is_completed,
                            remarks=remarks,
                            reviewed_by=reviewer_id,
                            reviewed_at=now,
                        )
                        tenant_session.add(new_sub)

                tenant_session.commit()
                return {'message': f'Updated submissions for {len(submissions_data)} students'}

        except ValueError as ve:
            raise ve
        except Exception as e:
            raise Exception(f"Failed to update submissions: {str(e)}")

    @staticmethod
    def get_student_assignments(skid, student_id, academic_year_id, date=None):
        """
        Get assignments for a student based on their class/section.
        Optionally filter by date. Returns most recent first.
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Get student's class and section
                student = tenant_session.query(Student).filter(
                    Student.user_id == student_id
                ).first()

                if not student:
                    raise ValueError("Student not found")

                if not student.section_id:
                    return []

                filters = [
                    Assignment.section_id == student.section_id,
                    Assignment.academic_year_id == academic_year_id,
                    Assignment.is_active == True,
                ]

                if date:
                    assignment_date = datetime.strptime(date, '%Y-%m-%d').date()
                    filters.append(Assignment.assignment_date == assignment_date)

                results = tenant_session.query(
                    Assignment,
                    Class.class_name,
                    Section.section_name,
                    Subject.subject_name,
                    SchoolUsers.first_name.label('teacher_first'),
                    SchoolUsers.last_name.label('teacher_last'),
                    AssignmentSubmission.is_completed,
                    AssignmentSubmission.remarks,
                ).join(
                    Class, Assignment.class_id == Class.id
                ).join(
                    Section, Assignment.section_id == Section.id
                ).join(
                    Subject, Assignment.subject_id == Subject.id
                ).outerjoin(
                    SchoolUsers, Assignment.teacher_id == SchoolUsers.id
                ).outerjoin(
                    AssignmentSubmission, and_(
                        AssignmentSubmission.assignment_id == Assignment.id,
                        AssignmentSubmission.student_id == student_id
                    )
                ).filter(
                    and_(*filters)
                ).order_by(Assignment.assignment_date.desc(), Assignment.created_at.desc()).all()

                assignments = []
                for row in results:
                    assignment_dict = row[0].to_dict()
                    assignment_dict['class_name'] = row.class_name
                    assignment_dict['section_name'] = row.section_name
                    assignment_dict['subject_name'] = row.subject_name
                    assignment_dict['teacher_name'] = f"{row.teacher_first} {row.teacher_last}" if row.teacher_first else ''
                    assignment_dict['is_completed'] = row.is_completed if row.is_completed is not None else False
                    assignment_dict['remarks'] = row.remarks or ''
                    assignments.append(assignment_dict)

                return assignments

        except ValueError as ve:
            raise ve
        except Exception as e:
            raise Exception(f"Failed to fetch student assignments: {str(e)}")

    @staticmethod
    def delete_assignment(skid, assignment_id):
        """Soft delete an assignment."""
        try:
            with switch_to_school_db(skid) as tenant_session:
                assignment = tenant_session.query(Assignment).filter(
                    and_(Assignment.id == assignment_id, Assignment.is_active == True)
                ).first()

                if not assignment:
                    raise ValueError("Assignment not found")

                assignment.is_active = False
                tenant_session.commit()
                return {'message': 'Assignment deleted successfully'}

        except ValueError as ve:
            raise ve
        except Exception as e:
            raise Exception(f"Failed to delete assignment: {str(e)}")
