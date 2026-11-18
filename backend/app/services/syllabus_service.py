# app/services/syllabus_service.py
from sqlalchemy.orm import joinedload
from sqlalchemy import distinct
from app.models.tenant import (
    Syllabus, Lesson, Topic, Subtopic, Subject, AcademicYear,
    TeacherSubject, SyllabusProgressTracking, TeacherSyllabusAssignment,
    Student, Timetable, TimetableEntry, Teacher, SchoolUsers,
    Class, Section
)
from app.utils.db_manager import switch_to_school_db
from datetime import datetime, date
from decimal import Decimal


class SyllabusService:

    # ============== HELPER METHODS ==============

    @staticmethod
    def _get_or_create_progress(session, teacher_id, item_type, item_id):
        """Get or create teacher-specific progress tracking record"""
        progress = session.query(SyllabusProgressTracking).filter_by(
            teacher_id=teacher_id,
            item_type=item_type,
            item_id=item_id,
            is_active=True
        ).first()

        if not progress:
            progress = SyllabusProgressTracking(
                teacher_id=teacher_id,
                item_type=item_type,
                item_id=item_id,
                status='planned',
                completion_percentage=0.00
            )
            session.add(progress)
            session.flush()

        return progress

    @staticmethod
    def _apply_teacher_progress_to_dict(data, progress):
        """Overlay teacher-specific progress data onto the item dict"""
        if not progress:
            return data

        override_fields = [
            'planned_start_date', 'planned_end_date', 'actual_start_date',
            'actual_end_date', 'planned_completion_date', 'actual_completion_date',
            'status', 'completion_percentage', 'is_completed', 'teacher_notes'
        ]

        p_dict = progress.to_dict()
        for field in override_fields:
            if field in p_dict and p_dict[field] is not None:
                data[field] = p_dict[field]

        return data

    @staticmethod
    def _cascade_complete_down(session, teacher_id, item_type, item_id, is_completed):
        """Cascade completion status down to children.
        When completing: set children to completed with 100%.
        When un-completing: revert children to in_progress with 0%.
        """
        if is_completed:
            status = 'completed'
            percentage = Decimal('100.00')
        else:
            status = 'in_progress'
            percentage = Decimal('0.00')

        if item_type == 'lesson':
            topics = session.query(Topic).filter_by(lesson_id=item_id, is_active=True).all()
            for topic in topics:
                tp = SyllabusService._get_or_create_progress(session, teacher_id, 'topic', topic.id)
                tp.status = status
                tp.completion_percentage = percentage
                if is_completed and not tp.actual_end_date:
                    tp.actual_end_date = date.today()
                elif not is_completed:
                    tp.actual_end_date = None
                # Cascade further into subtopics
                SyllabusService._cascade_complete_down(session, teacher_id, 'topic', topic.id, is_completed)

        elif item_type == 'topic':
            subtopics = session.query(Subtopic).filter_by(topic_id=item_id, is_active=True).all()
            for subtopic in subtopics:
                sp = SyllabusService._get_or_create_progress(session, teacher_id, 'subtopic', subtopic.id)
                sp.status = status
                sp.is_completed = is_completed
                sp.completion_percentage = percentage
                if is_completed and not sp.actual_completion_date:
                    sp.actual_completion_date = date.today()
                elif not is_completed:
                    sp.actual_completion_date = None

    @staticmethod
    def _get_section_teacher_ids(session, syllabus_id, teacher_id):
        """Get all teacher IDs assigned to the same section(s) for this syllabus.
        Only includes section-mates if the teacher has an ACTIVE assignment.
        Former teachers get only their own ID back (they see their own progress).
        """
        active_assignment = session.query(TeacherSyllabusAssignment).filter_by(
            syllabus_id=syllabus_id,
            teacher_id=teacher_id,
            is_active=True
        ).first()

        if not active_assignment:
            return {teacher_id}

        # Get all section IDs this teacher is assigned to for this syllabus
        my_section_ids = [a.section_id for a in session.query(TeacherSyllabusAssignment).filter_by(
            syllabus_id=syllabus_id,
            teacher_id=teacher_id
        ).all()]

        # Get all teachers (active + former) in those sections
        all_assignments = session.query(TeacherSyllabusAssignment).filter(
            TeacherSyllabusAssignment.syllabus_id == syllabus_id,
            TeacherSyllabusAssignment.section_id.in_(my_section_ids)
        ).all()

        return set(a.teacher_id for a in all_assignments)

    @staticmethod
    def _compute_combined_syllabus_pct(session, syllabus_id, teacher_ids):
        """Compute combined completion percentage for a syllabus by counting
        unique subtopics completed by ANY of the specified teachers."""
        if not teacher_ids:
            return 0, 'planned'

        # Get all subtopic IDs for this syllabus
        subtopic_rows = session.query(Subtopic.id).join(
            Topic, Subtopic.topic_id == Topic.id
        ).join(
            Lesson, Topic.lesson_id == Lesson.id
        ).filter(
            Lesson.syllabus_id == syllabus_id,
            Lesson.is_active == True,
            Topic.is_active == True,
            Subtopic.is_active == True
        ).all()

        total = len(subtopic_rows)
        if total == 0:
            # No subtopics — take the MAX progress among teachers
            max_progress = session.query(SyllabusProgressTracking).filter(
                SyllabusProgressTracking.teacher_id.in_(teacher_ids),
                SyllabusProgressTracking.item_type == 'syllabus',
                SyllabusProgressTracking.item_id == syllabus_id,
                SyllabusProgressTracking.is_active == True
            ).order_by(
                SyllabusProgressTracking.completion_percentage.desc()
            ).first()
            if max_progress:
                return float(max_progress.completion_percentage), max_progress.status
            return 0, 'planned'

        subtopic_id_list = [s[0] for s in subtopic_rows]

        # Count unique subtopics completed by any of the teachers
        completed_rows = session.query(
            distinct(SyllabusProgressTracking.item_id)
        ).filter(
            SyllabusProgressTracking.teacher_id.in_(teacher_ids),
            SyllabusProgressTracking.item_type == 'subtopic',
            SyllabusProgressTracking.item_id.in_(subtopic_id_list),
            SyllabusProgressTracking.is_active == True,
            SyllabusProgressTracking.is_completed == True
        ).all()

        completed = len(completed_rows)
        pct = round((completed / total) * 100, 2)

        if pct >= 100:
            status = 'completed'
        elif pct > 0:
            status = 'in_progress'
        else:
            status = 'planned'

        return pct, status

    @staticmethod
    def configure_timeline(skid, teacher_id, item_type, item_id, data):
        """Configure planned dates and notes for a syllabus item (Configure step)."""
        try:
            with switch_to_school_db(skid) as session:
                # Validate item exists
                if item_type == 'lesson':
                    item = session.query(Lesson).filter_by(id=item_id, is_active=True).first()
                elif item_type == 'topic':
                    item = session.query(Topic).filter_by(id=item_id, is_active=True).first()
                elif item_type == 'subtopic':
                    item = session.query(Subtopic).filter_by(id=item_id, is_active=True).first()
                else:
                    raise ValueError(f"Invalid item_type: {item_type}")

                if not item:
                    raise ValueError(f"{item_type.capitalize()} not found")

                progress = SyllabusService._get_or_create_progress(session, teacher_id, item_type, item_id)

                # Set planned dates
                progress.planned_start_date = data.get('planned_start_date')
                progress.planned_end_date = data.get('planned_end_date')

                if data.get('teacher_notes') is not None:
                    progress.teacher_notes = data['teacher_notes']

                # For subtopics, also set planned_completion_date for backward compat
                if item_type == 'subtopic':
                    progress.planned_completion_date = data.get('planned_end_date')

                # Only set status to 'planned' if not already in_progress or completed
                if progress.status not in ('in_progress', 'completed'):
                    progress.status = 'planned'

                session.commit()

                return {
                    'item_type': item_type,
                    'item_id': item_id,
                    'status': progress.status,
                    'planned_start_date': str(progress.planned_start_date) if progress.planned_start_date else None,
                    'planned_end_date': str(progress.planned_end_date) if progress.planned_end_date else None,
                    'teacher_notes': progress.teacher_notes,
                    'message': f'{item_type.capitalize()} timeline configured successfully'
                }

        except Exception as e:
            raise Exception(f"Failed to configure timeline: {str(e)}")

    @staticmethod
    def start_item(skid, teacher_id, item_type, item_id):
        """Start teaching a syllabus item (Start step). Requires item to be configured first."""
        try:
            with switch_to_school_db(skid) as session:
                # Get tracking record — must exist
                progress = session.query(SyllabusProgressTracking).filter_by(
                    teacher_id=teacher_id,
                    item_type=item_type,
                    item_id=item_id,
                    is_active=True
                ).first()

                if not progress:
                    raise ValueError(f"{item_type.capitalize()} must be configured before starting")

                if progress.status == 'in_progress':
                    raise ValueError(f"{item_type.capitalize()} is already started")

                if progress.status == 'completed':
                    raise ValueError(f"{item_type.capitalize()} is already completed")

                # Must be 'planned' to start
                if progress.status != 'planned':
                    raise ValueError(f"{item_type.capitalize()} must be configured (planned) before starting")

                # Hierarchy check: parent must be started
                if item_type == 'topic':
                    topic = session.query(Topic).filter_by(id=item_id, is_active=True).first()
                    if not topic:
                        raise ValueError("Topic not found")
                    parent_progress = session.query(SyllabusProgressTracking).filter_by(
                        teacher_id=teacher_id,
                        item_type='lesson',
                        item_id=topic.lesson_id,
                        is_active=True
                    ).first()
                    if not parent_progress or parent_progress.status not in ('in_progress', 'completed'):
                        raise ValueError("Parent lesson must be started first")

                elif item_type == 'subtopic':
                    subtopic = session.query(Subtopic).filter_by(id=item_id, is_active=True).first()
                    if not subtopic:
                        raise ValueError("Subtopic not found")
                    parent_progress = session.query(SyllabusProgressTracking).filter_by(
                        teacher_id=teacher_id,
                        item_type='topic',
                        item_id=subtopic.topic_id,
                        is_active=True
                    ).first()
                    if not parent_progress or parent_progress.status not in ('in_progress', 'completed'):
                        raise ValueError("Parent topic must be started first")

                # Set to in_progress
                progress.status = 'in_progress'
                progress.actual_start_date = date.today()

                session.commit()

                return {
                    'item_type': item_type,
                    'item_id': item_id,
                    'status': 'in_progress',
                    'actual_start_date': str(progress.actual_start_date),
                    'message': f'{item_type.capitalize()} started successfully'
                }

        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to start item: {str(e)}")

    @staticmethod
    def mark_progress(skid, teacher_id, item_type, item_id, is_completed):
        """Mark a syllabus item as complete/incomplete with bidirectional cascade.
        - Cascade DOWN: bulk-complete or revert children
        - Cascade UP: recalculate parent percentages
        Requires item to be started (in_progress or completed) unless grandfathered.
        """
        try:
            with switch_to_school_db(skid) as session:
                # Validate item exists
                if item_type == 'lesson':
                    item = session.query(Lesson).filter_by(id=item_id, is_active=True).first()
                elif item_type == 'topic':
                    item = session.query(Topic).filter_by(id=item_id, is_active=True).first()
                elif item_type == 'subtopic':
                    item = session.query(Subtopic).filter_by(id=item_id, is_active=True).first()
                else:
                    raise ValueError(f"Invalid item_type: {item_type}")

                if not item:
                    raise ValueError(f"{item_type.capitalize()} not found")

                # Gate: check if item is started
                existing_progress = session.query(SyllabusProgressTracking).filter_by(
                    teacher_id=teacher_id,
                    item_type=item_type,
                    item_id=item_id,
                    is_active=True
                ).first()

                if existing_progress:
                    if existing_progress.status == 'planned':
                        raise ValueError(f"{item_type.capitalize()} must be started before marking progress. Use the Start button first.")
                # If no record exists, this is legacy/grandfathered data — allow and auto-set in_progress

                # Update the target item's progress
                progress = SyllabusService._get_or_create_progress(session, teacher_id, item_type, item_id)
                if is_completed:
                    progress.status = 'completed'
                    progress.completion_percentage = Decimal('100.00')
                    progress.is_completed = True
                    if item_type == 'subtopic' and not progress.actual_completion_date:
                        progress.actual_completion_date = date.today()
                    elif item_type in ('lesson', 'topic') and not progress.actual_end_date:
                        progress.actual_end_date = date.today()
                else:
                    progress.status = 'in_progress'
                    progress.completion_percentage = Decimal('0.00')
                    progress.is_completed = False
                    if item_type == 'subtopic':
                        progress.actual_completion_date = None
                    elif item_type in ('lesson', 'topic'):
                        progress.actual_end_date = None

                session.flush()

                # Cascade DOWN (only for lesson/topic — subtopics have no children)
                if item_type in ('lesson', 'topic'):
                    SyllabusService._cascade_complete_down(session, teacher_id, item_type, item_id, is_completed)

                session.flush()

                # Cascade UP: recalculate parent completion percentages
                if item_type == 'subtopic':
                    SyllabusService._recalculate_teacher_topic_completion(session, teacher_id, item.topic_id)
                elif item_type == 'topic':
                    SyllabusService._recalculate_teacher_lesson_completion(session, teacher_id, item.lesson_id)
                elif item_type == 'lesson':
                    SyllabusService._recalculate_teacher_syllabus_completion(session, teacher_id, item.syllabus_id)

                session.commit()

                return {
                    'item_type': item_type,
                    'item_id': item_id,
                    'is_completed': is_completed,
                    'message': f'{item_type.capitalize()} {"completed" if is_completed else "reverted"} successfully'
                }

        except Exception as e:
            raise Exception(f"Failed to mark progress: {str(e)}")

    # ============== STUDENT SYLLABUS VIEW ==============

    @staticmethod
    def get_student_syllabus_view(skid, student_user_id, academic_year_id):
        """Get syllabus progress view for a student, resolved via timetable linkage."""
        try:
            with switch_to_school_db(skid) as session:
                # Get student's class and section
                student = session.query(Student).filter_by(user_id=student_user_id).first()
                if not student:
                    raise ValueError("Student not found")
                if not student.class_id or not student.section_id:
                    raise ValueError("Student is not assigned to a class/section")

                # Find timetable for this class/section/academic_year
                timetable = session.query(Timetable).filter_by(
                    class_id=student.class_id,
                    section_id=student.section_id,
                    academic_year_id=academic_year_id,
                    is_active=True
                ).first()

                if not timetable:
                    return []

                # Get distinct (teacher_id, subject_id) from timetable entries
                pairs = session.query(
                    distinct(TimetableEntry.teacher_id),
                    TimetableEntry.subject_id
                ).filter_by(
                    timetable_id=timetable.id,
                    is_active=True
                ).all()

                if not pairs:
                    return []

                results = []
                for teacher_id, subject_id in pairs:
                    # Find syllabus for this subject + academic year
                    syllabus = session.query(Syllabus).filter_by(
                        subject_id=subject_id,
                        academic_year_id=academic_year_id,
                        is_active=True
                    ).first()

                    if not syllabus:
                        continue

                    # Get teacher info
                    teacher = session.query(Teacher).filter_by(user_id=teacher_id).first()
                    teacher_user = session.query(SchoolUsers).filter_by(id=teacher_id).first() if teacher else None
                    teacher_name = teacher_user.full_name if teacher_user else 'Unknown'

                    # Get subject info
                    subject = session.query(Subject).filter_by(id=subject_id).first()
                    subject_name = subject.subject_name if subject else 'Unknown'

                    # Get combined progress for the student's section
                    section_assignments = session.query(TeacherSyllabusAssignment).filter(
                        TeacherSyllabusAssignment.syllabus_id == syllabus.id,
                        TeacherSyllabusAssignment.section_id == student.section_id
                    ).all()

                    if section_assignments:
                        section_tids = set(a.teacher_id for a in section_assignments)
                        completion_pct, status = SyllabusService._compute_combined_syllabus_pct(
                            session, syllabus.id, section_tids
                        )
                    else:
                        # No assignments yet — fall back to individual teacher progress
                        syllabus_progress = session.query(SyllabusProgressTracking).filter_by(
                            teacher_id=teacher_id,
                            item_type='syllabus',
                            item_id=syllabus.id,
                            is_active=True
                        ).first()
                        completion_pct = float(syllabus_progress.completion_percentage) if syllabus_progress else 0
                        status = syllabus_progress.status if syllabus_progress else syllabus.status

                    results.append({
                        'syllabus': syllabus.to_dict(),
                        'teacher_id': teacher_id,
                        'teacher_name': teacher_name,
                        'subject_id': subject_id,
                        'subject_name': subject_name,
                        'completion_percentage': completion_pct,
                        'status': status
                    })

                return results

        except Exception as e:
            raise Exception(f"Failed to get student syllabus view: {str(e)}")

    @staticmethod
    def get_teacher_syllabus_progress_view(skid, teacher_id, academic_year_id):
        """Get syllabus progress view for a teacher — shows their own assigned syllabi with progress."""
        try:
            with switch_to_school_db(skid) as session:
                # Get subjects assigned to teacher
                teacher_subjects = session.query(TeacherSubject).filter_by(teacher_id=teacher_id).all()
                if not teacher_subjects:
                    return []

                subject_ids = [ts.subject_id for ts in teacher_subjects]

                # Get syllabi for those subjects in this academic year
                syllabi = session.query(Syllabus).filter(
                    Syllabus.subject_id.in_(subject_ids),
                    Syllabus.academic_year_id == academic_year_id,
                    Syllabus.is_active == True
                ).all()

                if not syllabi:
                    return []

                # Get teacher info
                teacher_user = session.query(SchoolUsers).filter_by(id=teacher_id).first()
                teacher_name = teacher_user.full_name if teacher_user else 'Unknown'

                # Get syllabus-level progress for this teacher
                syllabus_ids = [s.id for s in syllabi]
                progress_list = session.query(SyllabusProgressTracking).filter(
                    SyllabusProgressTracking.teacher_id == teacher_id,
                    SyllabusProgressTracking.item_type == 'syllabus',
                    SyllabusProgressTracking.item_id.in_(syllabus_ids),
                    SyllabusProgressTracking.is_active == True
                ).all()
                progress_map = {p.item_id: p for p in progress_list}

                results = []
                for syllabus in syllabi:
                    subject = session.query(Subject).filter_by(id=syllabus.subject_id).first()
                    subject_name = subject.subject_name if subject else 'Unknown'

                    # Use combined progress if there are section-mates
                    section_tids = SyllabusService._get_section_teacher_ids(
                        session, syllabus.id, teacher_id
                    )
                    if len(section_tids) > 1:
                        completion_pct, status = SyllabusService._compute_combined_syllabus_pct(
                            session, syllabus.id, section_tids
                        )
                    else:
                        sp = progress_map.get(syllabus.id)
                        completion_pct = float(sp.completion_percentage) if sp else 0
                        status = sp.status if sp else 'planned'

                    results.append({
                        'syllabus': syllabus.to_dict(),
                        'teacher_id': teacher_id,
                        'teacher_name': teacher_name,
                        'subject_id': syllabus.subject_id,
                        'subject_name': subject_name,
                        'completion_percentage': completion_pct,
                        'status': status
                    })

                return results

        except Exception as e:
            raise Exception(f"Failed to get teacher syllabus progress view: {str(e)}")

    @staticmethod
    def get_student_syllabus_detail(skid, syllabus_id, teacher_id):
        """Get full syllabus hierarchy with a specific teacher's progress overlay (read-only for students)."""
        try:
            return SyllabusService.get_syllabus_by_id(
                skid, syllabus_id, teacher_id, include_hierarchy=True, merge_section_progress=True
            )
        except Exception as e:
            raise Exception(f"Failed to get student syllabus detail: {str(e)}")

    # ============== SYLLABUS OPERATIONS ==============

    @staticmethod
    def create_syllabus(skid, data, teacher_id):
        """Create a new syllabus for a subject"""
        try:
            with switch_to_school_db(skid) as session:
                # Validate subject and academic year exist
                subject = session.query(Subject).filter_by(id=data['subject_id']).first()
                if not subject:
                    raise ValueError("Subject not found")

                academic_year = session.query(AcademicYear).filter_by(id=data['academic_year_id']).first()
                if not academic_year:
                    raise ValueError("Academic year not found")

                # Check for duplicate syllabus
                existing = session.query(Syllabus).filter_by(
                    subject_id=data['subject_id'],
                    academic_year_id=data['academic_year_id'],
                    is_active=True
                ).first()
                if existing:
                    raise ValueError("Syllabus already exists for this subject and academic year")

                syllabus = Syllabus(
                    subject_id=data['subject_id'],
                    academic_year_id=data['academic_year_id'],
                    created_by=teacher_id,
                    title=data['title'],
                    description=data.get('description'),
                    estimated_duration_hours=data.get('estimated_duration_hours', 0)
                )

                session.add(syllabus)
                session.commit()
                session.refresh(syllabus)

                return syllabus.to_dict()

        except Exception as e:
            raise Exception(f"Failed to create syllabus: {str(e)}")

    @staticmethod
    def get_syllabus_by_id(skid, syllabus_id, teacher_id=None, include_hierarchy=False, merge_section_progress=False):
        """Get syllabus by ID with optional full hierarchy and teacher-specific progress.
        When teacher_id is provided, adds assignment-aware metadata:
        - is_read_only: True if the teacher has no active assignment (former teacher)
        - Per item: editable (bool), completed_by (str or None)
        When merge_section_progress=True, includes progress from section-mates
        (used for teacher's own view and student view). When False, shows only
        the specified teacher's individual progress (used for admin per-teacher view).
        """
        try:
            with switch_to_school_db(skid) as session:
                query = session.query(Syllabus).filter_by(id=syllabus_id, is_active=True)

                if include_hierarchy:
                    query = query.options(
                        joinedload(Syllabus.lessons).joinedload(Lesson.topics).joinedload(Topic.subtopics)
                    )

                syllabus = query.first()
                if not syllabus:
                    raise ValueError("Syllabus not found")

                syllabus_dict = syllabus.to_dict(include_lessons=include_hierarchy)

                if teacher_id:
                    # Check assignment status for this teacher
                    active_assignment = session.query(TeacherSyllabusAssignment).filter_by(
                        syllabus_id=syllabus_id,
                        teacher_id=teacher_id,
                        is_active=True
                    ).first()
                    is_read_only = active_assignment is None

                    syllabus_dict['is_read_only'] = is_read_only

                    # Determine section-mates: all teachers assigned to the same
                    # section(s) for this syllabus (for merged progress view)
                    other_progress_map = {}  # {(item_type, item_id): {teacher_id: progress}}
                    other_teacher_names = {}
                    section_teacher_ids = set()

                    if active_assignment and merge_section_progress:
                        # Get all teachers (active + former) for this teacher's section(s)
                        my_section_ids = [a.section_id for a in session.query(TeacherSyllabusAssignment).filter_by(
                            syllabus_id=syllabus_id,
                            teacher_id=teacher_id
                        ).all()]

                        section_assignments = session.query(TeacherSyllabusAssignment).filter(
                            TeacherSyllabusAssignment.syllabus_id == syllabus_id,
                            TeacherSyllabusAssignment.section_id.in_(my_section_ids),
                            TeacherSyllabusAssignment.teacher_id != teacher_id
                        ).all()
                        section_teacher_ids = set(a.teacher_id for a in section_assignments)

                        if section_teacher_ids:
                            # Load names
                            other_teachers = session.query(SchoolUsers).filter(
                                SchoolUsers.id.in_(section_teacher_ids)
                            ).all()
                            other_teacher_names = {t.id: t.full_name for t in other_teachers}

                            # Load their progress
                            other_progress_list = session.query(SyllabusProgressTracking).filter(
                                SyllabusProgressTracking.teacher_id.in_(section_teacher_ids),
                                SyllabusProgressTracking.is_active == True
                            ).all()
                            for p in other_progress_list:
                                key = (p.item_type, p.item_id)
                                if key not in other_progress_map:
                                    other_progress_map[key] = {}
                                other_progress_map[key][p.teacher_id] = p

                    # Fetch current teacher's progress
                    progress_list = session.query(SyllabusProgressTracking).filter_by(
                        teacher_id=teacher_id,
                        is_active=True
                    ).all()
                    progress_map = {(p.item_type, p.item_id): p for p in progress_list}

                    # Load current teacher's name for completed_by attribution
                    current_teacher_user = session.query(SchoolUsers).filter_by(id=teacher_id).first()
                    current_teacher_name = current_teacher_user.full_name if current_teacher_user else 'Unknown'

                    def apply_with_attribution(item_dict, item_type, item_id):
                        """Apply progress and set editable/completed_by metadata."""
                        my_progress = progress_map.get((item_type, item_id))
                        SyllabusService._apply_teacher_progress_to_dict(item_dict, my_progress)

                        if is_read_only:
                            item_dict['editable'] = False
                            # Show who completed for admin/student views
                            if my_progress and (my_progress.is_completed or my_progress.status == 'completed'):
                                item_dict['completed_by'] = current_teacher_name
                            else:
                                item_dict['completed_by'] = None
                            return

                        # Check if another teacher completed this item
                        other_records = other_progress_map.get((item_type, item_id), {})
                        completed_by_other = None
                        for other_tid, other_p in other_records.items():
                            if other_p.is_completed or other_p.status == 'completed':
                                completed_by_other = other_teacher_names.get(other_tid, 'Unknown')
                                break

                        if completed_by_other:
                            # Item was completed by a previous teacher
                            item_dict['status'] = 'completed'
                            item_dict['is_completed'] = True
                            item_dict['completion_percentage'] = 100.0
                            item_dict['editable'] = False
                            item_dict['completed_by'] = completed_by_other
                        else:
                            # Item is editable by this teacher
                            item_dict['editable'] = True
                            # Show completed_by if current teacher completed it
                            if my_progress and (my_progress.is_completed or my_progress.status == 'completed'):
                                item_dict['completed_by'] = current_teacher_name
                            else:
                                item_dict['completed_by'] = None

                    # Apply to syllabus level
                    apply_with_attribution(syllabus_dict, 'syllabus', syllabus_id)

                    # Apply to nested hierarchy
                    if include_hierarchy and 'lessons' in syllabus_dict:
                        for lesson in syllabus_dict['lessons']:
                            apply_with_attribution(lesson, 'lesson', lesson['id'])
                            if 'topics' in lesson:
                                for topic in lesson['topics']:
                                    apply_with_attribution(topic, 'topic', topic['id'])
                                    if 'subtopics' in topic:
                                        for subtopic in topic['subtopics']:
                                            apply_with_attribution(subtopic, 'subtopic', subtopic['id'])

                    # Recalculate parent completion percentages bottom-up from
                    # the merged child states so that progress completed by
                    # section-mates is reflected in topic/lesson/syllabus bars.
                    # Only needed when merging — individual progress is already consistent.
                    if include_hierarchy and 'lessons' in syllabus_dict and not is_read_only and merge_section_progress:
                        for lesson in syllabus_dict['lessons']:
                            if 'topics' in lesson:
                                for topic in lesson['topics']:
                                    subtopics = topic.get('subtopics', [])
                                    if subtopics:
                                        completed_count = sum(
                                            1 for s in subtopics
                                            if s.get('is_completed')
                                        )
                                        topic_pct = round(
                                            (completed_count / len(subtopics)) * 100, 2
                                        )
                                        topic['completion_percentage'] = topic_pct
                                        if topic_pct >= 100:
                                            topic['status'] = 'completed'
                                            topic['is_completed'] = True
                                        elif topic_pct > 0:
                                            topic['status'] = 'in_progress'

                            topics = lesson.get('topics', [])
                            if topics:
                                total_pct = sum(
                                    float(t.get('completion_percentage', 0))
                                    for t in topics
                                )
                                lesson_pct = round(total_pct / len(topics), 2)
                                lesson['completion_percentage'] = lesson_pct
                                if lesson_pct >= 100:
                                    lesson['status'] = 'completed'
                                    lesson['is_completed'] = True
                                elif lesson_pct > 0:
                                    lesson['status'] = 'in_progress'

                        lessons = syllabus_dict.get('lessons', [])
                        if lessons:
                            total_pct = sum(
                                float(l.get('completion_percentage', 0))
                                for l in lessons
                            )
                            syllabus_pct = round(total_pct / len(lessons), 2)
                            syllabus_dict['completion_percentage'] = syllabus_pct
                            if syllabus_pct >= 100:
                                syllabus_dict['status'] = 'completed'
                            elif syllabus_pct > 0:
                                syllabus_dict['status'] = 'in_progress'

                return syllabus_dict

        except Exception as e:
            raise Exception(f"Failed to get syllabus: {str(e)}")

    @staticmethod
    def get_syllabi_by_subject(skid, subject_id, academic_year_id=None):
        """Get all syllabi for a subject"""
        try:
            with switch_to_school_db(skid) as session:
                query = session.query(Syllabus).filter_by(subject_id=subject_id, is_active=True)

                if academic_year_id:
                    query = query.filter_by(academic_year_id=academic_year_id)

                syllabi = query.all()
                return [s.to_dict() for s in syllabi]

        except Exception as e:
            raise Exception(f"Failed to get syllabi: {str(e)}")

    @staticmethod
    def get_all_syllabi(skid, academic_year_id=None):
        """Get all syllabi for a school"""
        try:
            with switch_to_school_db(skid) as session:
                query = session.query(Syllabus).filter_by(is_active=True)

                if academic_year_id:
                    query = query.filter_by(academic_year_id=academic_year_id)

                syllabi = query.all()
                return [s.to_dict() for s in syllabi]

        except Exception as e:
            raise Exception(f"Failed to get all syllabi: {str(e)}")

    @staticmethod
    def get_syllabi_by_teacher(skid, teacher_id, academic_year_id=None):
        """Get all syllabi for a teacher"""
        try:
            with switch_to_school_db(skid) as session:
                # Get subjects assigned to teacher
                subject_ids = [ts.subject_id for ts in session.query(TeacherSubject).filter_by(teacher_id=teacher_id).all()]

                if not subject_ids:
                    return []

                query = session.query(Syllabus).filter(
                    Syllabus.subject_id.in_(subject_ids),
                    Syllabus.is_active == True
                )

                if academic_year_id:
                    query = query.filter_by(academic_year_id=academic_year_id)

                syllabi = query.all()
                return [s.to_dict() for s in syllabi]

        except Exception as e:
            raise Exception(f"Failed to get teacher syllabi: {str(e)}")

    @staticmethod
    def update_syllabus(skid, syllabus_id, data):
        """Update syllabus details"""
        try:
            with switch_to_school_db(skid) as session:
                syllabus = session.query(Syllabus).filter_by(id=syllabus_id, is_active=True).first()
                if not syllabus:
                    raise ValueError("Syllabus not found")

                # Update fields
                updatable_fields = ['title', 'description', 'status', 'planned_start_date',
                                    'planned_end_date', 'actual_start_date', 'actual_end_date',
                                    'estimated_duration_hours']

                for field in updatable_fields:
                    if field in data:
                        setattr(syllabus, field, data[field])

                syllabus.updated_at = datetime.utcnow()
                session.commit()
                session.refresh(syllabus)

                return syllabus.to_dict()

        except Exception as e:
            raise Exception(f"Failed to update syllabus: {str(e)}")

    @staticmethod
    def delete_syllabus(skid, syllabus_id):
        """Soft delete syllabus"""
        try:
            with switch_to_school_db(skid) as session:
                syllabus = session.query(Syllabus).filter_by(id=syllabus_id).first()
                if not syllabus:
                    raise ValueError("Syllabus not found")

                syllabus.is_active = False
                syllabus.updated_at = datetime.utcnow()
                session.commit()

                return {"message": "Syllabus deleted successfully"}

        except Exception as e:
            raise Exception(f"Failed to delete syllabus: {str(e)}")

    # ============== LESSON OPERATIONS ==============

    @staticmethod
    def create_lesson_or_chapter(skid, syllabus_id, data):
        """Create a new lesson under a syllabus"""
        try:
            with switch_to_school_db(skid) as session:
                syllabus = session.query(Syllabus).filter_by(id=syllabus_id, is_active=True).first()
                if not syllabus:
                    raise ValueError("Syllabus not found")

                # Auto-calculate sequence order if not provided
                if 'sequence_order' not in data:
                    max_order = session.query(Lesson).filter_by(syllabus_id=syllabus_id, is_active=True).count()
                    data['sequence_order'] = max_order + 1

                lesson = Lesson(
                    syllabus_id=syllabus_id,
                    title=data['title'],
                    description=data.get('description'),
                    sequence_order=data['sequence_order'],
                    estimated_duration_hours=data.get('estimated_duration_hours', 0),
                    lesson_notes=data.get('lesson_notes'),
                    teaching_method=data.get('teaching_method'),
                    resources_url=data.get('resources_url')
                )

                session.add(lesson)
                session.commit()
                session.refresh(lesson)

                return lesson.to_dict()

        except Exception as e:
            raise Exception(f"Failed to create lesson: {str(e)}")

    @staticmethod
    def update_lesson(skid, lesson_id, data, teacher_id=None):
        """Update lesson details (Shared content or Teacher-specific tracking)"""
        try:
            with switch_to_school_db(skid) as session:
                lesson = session.query(Lesson).filter_by(id=lesson_id, is_active=True).first()
                if not lesson:
                    raise ValueError("Lesson not found")

                if teacher_id:
                    # Update teacher-specific progress
                    progress = SyllabusService._get_or_create_progress(session, teacher_id, 'lesson', lesson_id)
                    tracking_fields = ['status', 'planned_start_date', 'planned_end_date',
                                      'actual_start_date', 'actual_end_date', 'teacher_notes']
                    for field in tracking_fields:
                        if field in data:
                            setattr(progress, field, data[field])

                    session.commit()
                    # Recalculate teacher-specific parent completion
                    SyllabusService._recalculate_teacher_syllabus_completion(session, teacher_id, lesson.syllabus_id)
                    return lesson.to_dict() # Return dict, UI will overlay progress later
                else:
                    # Update shared content
                    updatable_fields = ['title', 'description', 'sequence_order', 'status',
                                        'planned_start_date', 'planned_end_date',
                                        'actual_start_date', 'actual_end_date',
                                        'estimated_duration_hours', 'lesson_notes',
                                        'teaching_method', 'resources_url']

                    for field in updatable_fields:
                        if field in data:
                            setattr(lesson, field, data[field])

                    lesson.updated_at = datetime.utcnow()
                    session.commit()
                    session.refresh(lesson)
                    return lesson.to_dict()

        except Exception as e:
            raise Exception(f"Failed to update lesson: {str(e)}")

    @staticmethod
    def delete_lesson(skid, lesson_id):
        """Soft delete lesson"""
        try:
            with switch_to_school_db(skid) as session:
                lesson = session.query(Lesson).filter_by(id=lesson_id).first()
                if not lesson:
                    raise ValueError("Lesson not found")

                lesson.is_active = False
                lesson.updated_at = datetime.utcnow()

                # Soft delete all teacher progress for this lesson
                session.query(SyllabusProgressTracking).filter_by(
                    item_type='lesson',
                    item_id=lesson_id
                ).update({"is_active": False})

                session.commit()

                return {"message": "Lesson deleted successfully"}

        except Exception as e:
            raise Exception(f"Failed to delete lesson: {str(e)}")

    # ============== TOPIC OPERATIONS ==============

    @staticmethod
    def create_topic(skid, lesson_id, data):
        """Create a new topic under a lesson"""
        try:
            with switch_to_school_db(skid) as session:
                lesson = session.query(Lesson).filter_by(id=lesson_id, is_active=True).first()
                if not lesson:
                    raise ValueError("Lesson not found")

                if 'sequence_order' not in data:
                    max_order = session.query(Topic).filter_by(lesson_id=lesson_id, is_active=True).count()
                    data['sequence_order'] = max_order + 1

                topic = Topic(
                    lesson_id=lesson_id,
                    title=data['title'],
                    description=data.get('description'),
                    sequence_order=data['sequence_order'],
                    estimated_duration_hours=data.get('estimated_duration_hours', 0)
                )

                session.add(topic)
                session.commit()
                session.refresh(topic)

                return topic.to_dict()

        except Exception as e:
            raise Exception(f"Failed to create topic: {str(e)}")

    @staticmethod
    def update_topic(skid, topic_id, data, teacher_id=None):
        """Update topic details (Shared content or Teacher-specific tracking)"""
        try:
            with switch_to_school_db(skid) as session:
                topic = session.query(Topic).filter_by(id=topic_id, is_active=True).first()
                if not topic:
                    raise ValueError("Topic not found")

                if teacher_id:
                    # Update teacher-specific progress
                    progress = SyllabusService._get_or_create_progress(session, teacher_id, 'topic', topic_id)
                    tracking_fields = ['status', 'planned_start_date', 'planned_end_date',
                                      'actual_start_date', 'actual_end_date', 'teacher_notes']
                    for field in tracking_fields:
                        if field in data:
                            setattr(progress, field, data[field])

                    session.commit()
                    # Recalculate teacher-specific parent completion
                    SyllabusService._recalculate_teacher_lesson_completion(session, teacher_id, topic.lesson_id)
                    return topic.to_dict()
                else:
                    # Update shared content
                    updatable_fields = ['title', 'description', 'sequence_order', 'status',
                                        'planned_start_date', 'planned_end_date',
                                        'actual_start_date', 'actual_end_date',
                                        'estimated_duration_hours']

                    for field in updatable_fields:
                        if field in data:
                            setattr(topic, field, data[field])

                    topic.updated_at = datetime.utcnow()
                    session.commit()
                    session.refresh(topic)
                    return topic.to_dict()

        except Exception as e:
            raise Exception(f"Failed to update topic: {str(e)}")

    @staticmethod
    def delete_topic(skid, topic_id):
        """Soft delete topic"""
        try:
            with switch_to_school_db(skid) as session:
                topic = session.query(Topic).filter_by(id=topic_id).first()
                if not topic:
                    raise ValueError("Topic not found")

                topic.is_active = False
                topic.updated_at = datetime.utcnow()

                # Soft delete all teacher progress for this topic
                session.query(SyllabusProgressTracking).filter_by(
                    item_type='topic',
                    item_id=topic_id
                ).update({"is_active": False})

                session.commit()

                return {"message": "Topic deleted successfully"}

        except Exception as e:
            raise Exception(f"Failed to delete topic: {str(e)}")

    # ============== SUBTOPIC OPERATIONS ==============

    @staticmethod
    def create_subtopic(skid, topic_id, data):
        """Create a new subtopic under a topic"""
        try:
            with switch_to_school_db(skid) as session:
                topic = session.query(Topic).filter_by(id=topic_id, is_active=True).first()
                if not topic:
                    raise ValueError("Topic not found")

                if 'sequence_order' not in data:
                    max_order = session.query(Subtopic).filter_by(topic_id=topic_id, is_active=True).count()
                    data['sequence_order'] = max_order + 1

                subtopic = Subtopic(
                    topic_id=topic_id,
                    title=data['title'],
                    description=data.get('description'),
                    sequence_order=data['sequence_order'],
                    estimated_duration_hours=data.get('estimated_duration_hours', 0),
                    learning_objectives=data.get('learning_objectives')
                )

                session.add(subtopic)
                session.commit()
                session.refresh(subtopic)

                return subtopic.to_dict()

        except Exception as e:
            raise Exception(f"Failed to create subtopic: {str(e)}")

    @staticmethod
    def update_subtopic(skid, subtopic_id, data, teacher_id=None):
        """Update subtopic details (Shared content or Teacher-specific tracking)"""
        try:
            with switch_to_school_db(skid) as session:
                subtopic = session.query(Subtopic).filter_by(id=subtopic_id, is_active=True).first()
                if not subtopic:
                    raise ValueError("Subtopic not found")

                if teacher_id:
                    # Update teacher-specific progress
                    progress = SyllabusService._get_or_create_progress(session, teacher_id, 'subtopic', subtopic_id)
                    tracking_fields = ['status', 'planned_completion_date', 'actual_completion_date',
                                      'is_completed', 'teacher_notes']
                    for field in tracking_fields:
                        if field in data:
                            setattr(progress, field, data[field])

                    # Auto-set actual_completion_date if marked completed
                    if data.get('is_completed') and not progress.actual_completion_date:
                        progress.actual_completion_date = date.today()
                        progress.status = 'completed'

                    session.commit()
                    # Recalculate teacher-specific parent completion
                    SyllabusService._recalculate_teacher_topic_completion(session, teacher_id, subtopic.topic_id)
                    return subtopic.to_dict()
                else:
                    # Update shared content
                    updatable_fields = ['title', 'description', 'sequence_order', 'status',
                                        'planned_completion_date', 'actual_completion_date',
                                        'estimated_duration_hours', 'learning_objectives',
                                        'is_completed']

                    for field in updatable_fields:
                        if field in data:
                            setattr(subtopic, field, data[field])

                    # Auto-set actual_completion_date if marked completed
                    if data.get('is_completed') and not subtopic.actual_completion_date:
                        subtopic.actual_completion_date = date.today()
                        subtopic.status = 'completed'

                    subtopic.updated_at = datetime.utcnow()
                    session.commit()
                    session.refresh(subtopic)
                    return subtopic.to_dict()

        except Exception as e:
            raise Exception(f"Failed to update subtopic: {str(e)}")

    @staticmethod
    def delete_subtopic(skid, subtopic_id):
        """Soft delete subtopic"""
        try:
            with switch_to_school_db(skid) as session:
                subtopic = session.query(Subtopic).filter_by(id=subtopic_id).first()
                if not subtopic:
                    raise ValueError("Subtopic not found")

                subtopic.is_active = False
                subtopic.updated_at = datetime.utcnow()

                # Soft delete all teacher progress for this subtopic
                session.query(SyllabusProgressTracking).filter_by(
                    item_type='subtopic',
                    item_id=subtopic_id
                ).update({"is_active": False})

                session.commit()

                return {"message": "Subtopic deleted successfully"}

        except Exception as e:
            raise Exception(f"Failed to delete subtopic: {str(e)}")

    # ============== TEACHER-SPECIFIC COMPLETION CALCULATION ==============

    @staticmethod
    def _recalculate_teacher_topic_completion(session, teacher_id, topic_id):
        """Recalculate teacher-specific topic completion based on subtopics"""
        topic = session.query(Topic).filter_by(id=topic_id).first()
        if not topic:
            return

        subtopics = session.query(Subtopic).filter_by(topic_id=topic_id, is_active=True).all()
        if not subtopics:
            return

        # Get all subtopic progress for this teacher
        subtopic_ids = [s.id for s in subtopics]
        progress_records = session.query(SyllabusProgressTracking).filter(
            SyllabusProgressTracking.teacher_id == teacher_id,
            SyllabusProgressTracking.item_type == 'subtopic',
            SyllabusProgressTracking.item_id.in_(subtopic_ids),
            SyllabusProgressTracking.is_active == True
        ).all()

        completed_count = sum(1 for p in progress_records if p.is_completed)
        completion_percentage = Decimal((completed_count / len(subtopics)) * 100)

        # Update topic progress
        progress = SyllabusService._get_or_create_progress(session, teacher_id, 'topic', topic_id)
        progress.completion_percentage = completion_percentage

        if completion_percentage == 100:
            progress.status = 'completed'
            if not progress.actual_end_date:
                progress.actual_end_date = date.today()
        elif completion_percentage > 0:
            progress.status = 'in_progress'
            if not progress.actual_start_date:
                progress.actual_start_date = date.today()

        session.commit()
        # Cascade
        SyllabusService._recalculate_teacher_lesson_completion(session, teacher_id, topic.lesson_id)

    @staticmethod
    def _recalculate_teacher_lesson_completion(session, teacher_id, lesson_id):
        """Recalculate teacher-specific lesson completion based on topics"""
        lesson = session.query(Lesson).filter_by(id=lesson_id).first()
        if not lesson:
            return

        topics = session.query(Topic).filter_by(lesson_id=lesson_id, is_active=True).all()
        if not topics:
            return

        # Get all topic progress for this teacher
        topic_ids = [t.id for t in topics]
        progress_records = session.query(SyllabusProgressTracking).filter(
            SyllabusProgressTracking.teacher_id == teacher_id,
            SyllabusProgressTracking.item_type == 'topic',
            SyllabusProgressTracking.item_id.in_(topic_ids),
            SyllabusProgressTracking.is_active == True
        ).all()

        total_completion = sum(float(p.completion_percentage) for p in progress_records)
        completion_percentage = Decimal(total_completion / len(topics))

        # Update lesson progress
        progress = SyllabusService._get_or_create_progress(session, teacher_id, 'lesson', lesson_id)
        progress.completion_percentage = completion_percentage

        if completion_percentage == 100:
            progress.status = 'completed'
        elif completion_percentage > 0:
            progress.status = 'in_progress'

        session.commit()
        # Cascade
        SyllabusService._recalculate_teacher_syllabus_completion(session, teacher_id, lesson.syllabus_id)

    @staticmethod
    def _recalculate_teacher_syllabus_completion(session, teacher_id, syllabus_id):
        """Recalculate teacher-specific syllabus completion based on lessons"""
        syllabus = session.query(Syllabus).filter_by(id=syllabus_id).first()
        if not syllabus:
            return

        lessons = session.query(Lesson).filter_by(syllabus_id=syllabus_id, is_active=True).all()
        if not lessons:
            return

        # Get all lesson progress for this teacher
        lesson_ids = [l.id for l in lessons]
        progress_records = session.query(SyllabusProgressTracking).filter(
            SyllabusProgressTracking.teacher_id == teacher_id,
            SyllabusProgressTracking.item_type == 'lesson',
            SyllabusProgressTracking.item_id.in_(lesson_ids),
            SyllabusProgressTracking.is_active == True
        ).all()

        total_completion = sum(float(p.completion_percentage) for p in progress_records)
        completion_percentage = Decimal(total_completion / len(lessons))

        # Update syllabus progress
        progress = SyllabusService._get_or_create_progress(session, teacher_id, 'syllabus', syllabus_id)
        progress.completion_percentage = completion_percentage

        if completion_percentage == 100:
            progress.status = 'completed'
        elif completion_percentage > 0:
            progress.status = 'in_progress'

        session.commit()

    # ============== TEACHER SYLLABUS ASSIGNMENTS ==============

    @staticmethod
    def assign_teacher_to_syllabus(skid, syllabus_id, teacher_id, section_id):
        """Assign a teacher to a syllabus for a specific section."""
        try:
            with switch_to_school_db(skid) as session:
                syllabus = session.query(Syllabus).filter_by(id=syllabus_id, is_active=True).first()
                if not syllabus:
                    raise ValueError("Syllabus not found")

                teacher = session.query(Teacher).filter_by(user_id=teacher_id).first()
                if not teacher:
                    raise ValueError("Teacher not found")

                section = session.query(Section).filter_by(id=section_id).first()
                if not section:
                    raise ValueError("Section not found")

                # Check no active assignment already exists for this combo
                existing = session.query(TeacherSyllabusAssignment).filter_by(
                    syllabus_id=syllabus_id,
                    teacher_id=teacher_id,
                    section_id=section_id,
                    is_active=True
                ).first()
                if existing:
                    raise ValueError("This teacher is already actively assigned to this syllabus for this section")

                assignment = TeacherSyllabusAssignment(
                    syllabus_id=syllabus_id,
                    teacher_id=teacher_id,
                    section_id=section_id,
                    is_active=True
                )
                session.add(assignment)
                session.flush()

                # Ensure a syllabus-level progress tracking record exists
                progress = session.query(SyllabusProgressTracking).filter_by(
                    teacher_id=teacher_id,
                    item_type='syllabus',
                    item_id=syllabus_id,
                    is_active=True
                ).first()
                if not progress:
                    progress = SyllabusProgressTracking(
                        teacher_id=teacher_id,
                        item_type='syllabus',
                        item_id=syllabus_id,
                        status='planned',
                        completion_percentage=0.00
                    )
                    session.add(progress)

                session.commit()

                # Build response with names
                teacher_user = session.query(SchoolUsers).filter_by(id=teacher_id).first()
                class_obj = session.query(Class).filter_by(id=section.class_id).first()

                result = assignment.to_dict()
                result['teacher_name'] = teacher_user.full_name if teacher_user else 'Unknown'
                result['section_name'] = section.section_name
                result['class_name'] = class_obj.class_name if class_obj else 'Unknown'
                result['class_id'] = section.class_id

                return result

        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to assign teacher: {str(e)}")

    @staticmethod
    def unassign_teacher_from_syllabus(skid, assignment_id):
        """Unassign a teacher from a syllabus section (preserves history)."""
        try:
            with switch_to_school_db(skid) as session:
                assignment = session.query(TeacherSyllabusAssignment).filter_by(
                    id=assignment_id, is_active=True
                ).first()
                if not assignment:
                    raise ValueError("Active assignment not found")

                assignment.is_active = False
                assignment.unassigned_at = datetime.utcnow()
                session.commit()

                return {'message': 'Teacher unassigned successfully'}

        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to unassign teacher: {str(e)}")

    @staticmethod
    def get_syllabus_assignments(skid, syllabus_id):
        """Get all assignments (active + inactive) for a syllabus with teacher/section names."""
        try:
            with switch_to_school_db(skid) as session:
                syllabus = session.query(Syllabus).filter_by(id=syllabus_id, is_active=True).first()
                if not syllabus:
                    raise ValueError("Syllabus not found")

                assignments = session.query(TeacherSyllabusAssignment).filter_by(
                    syllabus_id=syllabus_id
                ).order_by(
                    TeacherSyllabusAssignment.is_active.desc(),
                    TeacherSyllabusAssignment.assigned_at.desc()
                ).all()

                if not assignments:
                    return []

                # Collect IDs for batch lookup
                teacher_ids = set(a.teacher_id for a in assignments)
                section_ids = set(a.section_id for a in assignments)

                teacher_users = session.query(SchoolUsers).filter(SchoolUsers.id.in_(teacher_ids)).all()
                teacher_map = {t.id: t.full_name for t in teacher_users}

                sections = session.query(Section).filter(Section.id.in_(section_ids)).all()
                section_map = {s.id: s for s in sections}

                class_ids = set(s.class_id for s in sections if s.class_id)
                classes = session.query(Class).filter(Class.id.in_(class_ids)).all() if class_ids else []
                class_map = {c.id: c.class_name for c in classes}

                results = []
                for a in assignments:
                    sec = section_map.get(a.section_id)
                    result = a.to_dict()
                    result['teacher_name'] = teacher_map.get(a.teacher_id, 'Unknown')
                    result['section_name'] = sec.section_name if sec else 'Unknown'
                    result['class_id'] = sec.class_id if sec else None
                    result['class_name'] = class_map.get(sec.class_id, 'Unknown') if sec else 'Unknown'
                    results.append(result)

                return results

        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to get syllabus assignments: {str(e)}")

    @staticmethod
    def get_teachers_by_subject(skid, subject_id):
        """Get all teachers assigned to a subject via TeacherSubject."""
        try:
            with switch_to_school_db(skid) as session:
                teacher_subjects = session.query(TeacherSubject).filter_by(
                    subject_id=subject_id
                ).all()

                if not teacher_subjects:
                    return []

                teacher_ids = [ts.teacher_id for ts in teacher_subjects]
                teachers = session.query(SchoolUsers).filter(
                    SchoolUsers.id.in_(teacher_ids)
                ).all()

                return [
                    {
                        'teacher_id': t.id,
                        'teacher_name': t.full_name
                    }
                    for t in teachers
                ]

        except Exception as e:
            raise Exception(f"Failed to get teachers by subject: {str(e)}")

    # ============== TEACHERS FOR SYLLABUS ==============

    @staticmethod
    def get_teachers_for_syllabus(skid, syllabus_id):
        """Get all teachers for a syllabus, grouped by section — active and former.
        Source of truth: teacher_syllabus_assignments table only.
        """
        try:
            with switch_to_school_db(skid) as session:
                syllabus = session.query(Syllabus).filter_by(id=syllabus_id, is_active=True).first()
                if not syllabus:
                    raise ValueError("Syllabus not found")

                assignments = session.query(TeacherSyllabusAssignment).filter_by(
                    syllabus_id=syllabus_id
                ).all()

                if not assignments:
                    return []

                # Collect unique IDs
                teacher_ids = set(a.teacher_id for a in assignments)
                section_ids = set(a.section_id for a in assignments)

                # Batch-load names
                teachers = session.query(SchoolUsers).filter(
                    SchoolUsers.id.in_(teacher_ids)
                ).all()
                teacher_map = {t.id: t.full_name for t in teachers}

                # Batch-load sections and classes
                sections = session.query(Section).filter(Section.id.in_(section_ids)).all()
                section_map = {s.id: s for s in sections}
                class_ids = set(s.class_id for s in sections if s.class_id)
                class_map = {}
                if class_ids:
                    classes = session.query(Class).filter(Class.id.in_(class_ids)).all()
                    class_map = {c.id: c.class_name for c in classes}

                # Batch-load progress
                progress_list = session.query(SyllabusProgressTracking).filter(
                    SyllabusProgressTracking.teacher_id.in_(teacher_ids),
                    SyllabusProgressTracking.item_type == 'syllabus',
                    SyllabusProgressTracking.item_id == syllabus_id,
                    SyllabusProgressTracking.is_active == True
                ).all()
                progress_map = {p.teacher_id: p for p in progress_list}

                # Build per-teacher section lists and active flag
                teacher_sections = {}  # {teacher_id: [section_info]}
                teacher_active = {}    # {teacher_id: bool}
                for a in assignments:
                    if a.teacher_id not in teacher_sections:
                        teacher_sections[a.teacher_id] = []
                        teacher_active[a.teacher_id] = False
                    if a.is_active:
                        teacher_active[a.teacher_id] = True

                    sec = section_map.get(a.section_id)
                    section_info = {
                        'section_id': a.section_id,
                        'section_name': sec.section_name if sec else 'Unknown',
                        'class_id': sec.class_id if sec else None,
                        'class_name': class_map.get(sec.class_id, 'Unknown') if sec else 'Unknown'
                    }
                    if section_info not in teacher_sections[a.teacher_id]:
                        teacher_sections[a.teacher_id].append(section_info)

                # Build results
                results = []
                for tid in teacher_ids:
                    p = progress_map.get(tid)
                    results.append({
                        'teacher_id': tid,
                        'teacher_name': teacher_map.get(tid, 'Unknown'),
                        'completion_percentage': float(p.completion_percentage) if p else 0,
                        'status': p.status if p else 'planned',
                        'is_active': teacher_active.get(tid, False),
                        'sections': teacher_sections.get(tid, [])
                    })

                # Sort: active teachers first, then by name
                results.sort(key=lambda x: (not x['is_active'], x['teacher_name']))

                return results

        except Exception as e:
            raise Exception(f"Failed to get teachers for syllabus: {str(e)}")

    @staticmethod
    def get_syllabus_combined_progress(skid, syllabus_id, teacher_ids=None):
        """Get syllabus with combined progress — best-status logic.
        If teacher_ids is provided, only merge progress from those teachers.
        """
        try:
            with switch_to_school_db(skid) as session:
                syllabus = session.query(Syllabus).options(
                    joinedload(Syllabus.lessons).joinedload(Lesson.topics).joinedload(Topic.subtopics)
                ).filter_by(id=syllabus_id, is_active=True).first()

                if not syllabus:
                    raise ValueError("Syllabus not found")

                syllabus_dict = syllabus.to_dict(include_lessons=True)

                # Collect all item IDs from the hierarchy
                item_ids = {
                    'syllabus': [syllabus_id],
                    'lesson': [],
                    'topic': [],
                    'subtopic': []
                }
                for lesson in syllabus_dict.get('lessons', []):
                    item_ids['lesson'].append(lesson['id'])
                    for topic in lesson.get('topics', []):
                        item_ids['topic'].append(topic['id'])
                        for subtopic in topic.get('subtopics', []):
                            item_ids['subtopic'].append(subtopic['id'])

                # Query all progress records for these items (all teachers)
                all_item_ids = []
                for ids in item_ids.values():
                    all_item_ids.extend(ids)

                if not all_item_ids:
                    return syllabus_dict

                progress_query = session.query(SyllabusProgressTracking).filter(
                    SyllabusProgressTracking.is_active == True,
                    SyllabusProgressTracking.item_id.in_(all_item_ids)
                )
                if teacher_ids:
                    progress_query = progress_query.filter(
                        SyllabusProgressTracking.teacher_id.in_(teacher_ids)
                    )
                progress_list = progress_query.all()

                # Load teacher names for completed_by attribution
                all_progress_teacher_ids = set(p.teacher_id for p in progress_list)
                teacher_name_map = {}
                if all_progress_teacher_ids:
                    teacher_users = session.query(SchoolUsers).filter(
                        SchoolUsers.id.in_(all_progress_teacher_ids)
                    ).all()
                    teacher_name_map = {t.id: t.full_name for t in teacher_users}

                # Group by (item_type, item_id)
                progress_groups = {}
                for p in progress_list:
                    key = (p.item_type, p.item_id)
                    if key not in progress_groups:
                        progress_groups[key] = []
                    progress_groups[key].append(p)

                # Merge function: best-status logic
                def merge_progress(item_type, item_id):
                    records = progress_groups.get((item_type, item_id), [])
                    if not records:
                        return None

                    has_completed = any(
                        r.status == 'completed' or r.is_completed for r in records
                    )
                    has_in_progress = any(r.status == 'in_progress' for r in records)
                    max_pct = max(float(r.completion_percentage) for r in records)

                    # Find who completed it
                    completed_by = None
                    if has_completed:
                        for r in records:
                            if r.is_completed or r.status == 'completed':
                                completed_by = teacher_name_map.get(r.teacher_id, 'Unknown')
                                break
                        status = 'completed'
                    elif has_in_progress:
                        status = 'in_progress'
                    else:
                        status = 'planned'

                    # Merge timeline dates: earliest start, latest end
                    planned_starts = [r.planned_start_date for r in records if r.planned_start_date]
                    planned_ends = [r.planned_end_date for r in records if r.planned_end_date]
                    actual_starts = [r.actual_start_date for r in records if r.actual_start_date]
                    actual_ends = [r.actual_end_date for r in records if r.actual_end_date]

                    return {
                        'status': status,
                        'completion_percentage': max_pct if item_type != 'subtopic' else (100.0 if has_completed else max_pct),
                        'is_completed': has_completed,
                        'completed_by': completed_by,
                        'planned_start_date': min(planned_starts).isoformat() if planned_starts else None,
                        'planned_end_date': max(planned_ends).isoformat() if planned_ends else None,
                        'actual_start_date': min(actual_starts).isoformat() if actual_starts else None,
                        'actual_end_date': max(actual_ends).isoformat() if actual_ends else None,
                    }

                # Helper to apply timeline date fields from merged progress
                def apply_timeline_dates(item_dict, merged_data):
                    if not merged_data:
                        return
                    for date_field in ('planned_start_date', 'planned_end_date', 'actual_start_date', 'actual_end_date'):
                        if merged_data.get(date_field):
                            item_dict[date_field] = merged_data[date_field]

                # Apply merged progress to subtopics first (leaf nodes)
                for lesson in syllabus_dict.get('lessons', []):
                    for topic in lesson.get('topics', []):
                        for subtopic in topic.get('subtopics', []):
                            merged = merge_progress('subtopic', subtopic['id'])
                            if merged:
                                subtopic['status'] = merged['status']
                                subtopic['is_completed'] = merged['is_completed']
                                subtopic['completion_percentage'] = merged['completion_percentage']
                                subtopic['completed_by'] = merged.get('completed_by')
                                apply_timeline_dates(subtopic, merged)

                        # Recalculate topic percentage from merged subtopics
                        subtopics = topic.get('subtopics', [])
                        # Always apply timeline dates from direct topic progress
                        topic_merged = merge_progress('topic', topic['id'])
                        apply_timeline_dates(topic, topic_merged)

                        if subtopics:
                            completed_count = sum(
                                1 for s in subtopics if s.get('is_completed')
                            )
                            topic_pct = (completed_count / len(subtopics)) * 100
                            topic['completion_percentage'] = round(topic_pct, 2)
                            if topic_pct == 100:
                                topic['status'] = 'completed'
                            elif topic_pct > 0:
                                topic['status'] = 'in_progress'
                            else:
                                # Check if any direct topic progress exists
                                if topic_merged:
                                    topic['status'] = topic_merged['status']
                                    topic['completed_by'] = topic_merged.get('completed_by')
                        else:
                            # No subtopics — use direct topic progress
                            if topic_merged:
                                topic['status'] = topic_merged['status']
                                topic['completion_percentage'] = topic_merged['completion_percentage']
                                topic['completed_by'] = topic_merged.get('completed_by')

                    # Recalculate lesson percentage from merged topics
                    topics = lesson.get('topics', [])
                    # Always apply timeline dates from direct lesson progress
                    lesson_merged = merge_progress('lesson', lesson['id'])
                    apply_timeline_dates(lesson, lesson_merged)

                    if topics:
                        total_pct = sum(
                            float(t.get('completion_percentage', 0)) for t in topics
                        )
                        lesson_pct = total_pct / len(topics)
                        lesson['completion_percentage'] = round(lesson_pct, 2)
                        if lesson_pct == 100:
                            lesson['status'] = 'completed'
                        elif lesson_pct > 0:
                            lesson['status'] = 'in_progress'
                        else:
                            if lesson_merged:
                                lesson['status'] = lesson_merged['status']
                                lesson['completed_by'] = lesson_merged.get('completed_by')
                    else:
                        if lesson_merged:
                            lesson['status'] = lesson_merged['status']
                            lesson['completion_percentage'] = lesson_merged['completion_percentage']
                            lesson['completed_by'] = lesson_merged.get('completed_by')

                # Recalculate syllabus percentage from merged lessons
                lessons = syllabus_dict.get('lessons', [])
                if lessons:
                    total_pct = sum(
                        float(l.get('completion_percentage', 0)) for l in lessons
                    )
                    syllabus_pct = total_pct / len(lessons)
                    syllabus_dict['completion_percentage'] = round(syllabus_pct, 2)
                    if syllabus_pct == 100:
                        syllabus_dict['status'] = 'completed'
                    elif syllabus_pct > 0:
                        syllabus_dict['status'] = 'in_progress'

                return syllabus_dict

        except Exception as e:
            raise Exception(f"Failed to get combined progress: {str(e)}")

    # ============== ANALYTICS & REPORTING ==============

    @staticmethod
    def get_syllabus_analytics(skid, syllabus_id, teacher_id=None):
        """Get detailed analytics for a syllabus with optional teacher-specific progress"""
        try:
            with switch_to_school_db(skid) as session:
                syllabus = session.query(Syllabus).options(
                    joinedload(Syllabus.lessons).joinedload(Lesson.topics).joinedload(Topic.subtopics)
                ).filter_by(id=syllabus_id, is_active=True).first()

                if not syllabus:
                    raise ValueError("Syllabus not found")

                syllabus_dict = syllabus.to_dict(include_lessons=True)

                if teacher_id:
                    # Apply teacher-specific progress to the hierarchy
                    progress_list = session.query(SyllabusProgressTracking).filter_by(
                        teacher_id=teacher_id,
                        is_active=True
                    ).all()
                    progress_map = {(p.item_type, p.item_id): p for p in progress_list}

                    SyllabusService._apply_teacher_progress_to_dict(
                        syllabus_dict, progress_map.get(('syllabus', syllabus_id))
                    )

                    for lesson in syllabus_dict['lessons']:
                        SyllabusService._apply_teacher_progress_to_dict(
                            lesson, progress_map.get(('lesson', lesson['id']))
                        )
                        for topic in lesson['topics']:
                            SyllabusService._apply_teacher_progress_to_dict(
                                topic, progress_map.get(('topic', topic['id']))
                            )
                            for subtopic in topic['subtopics']:
                                SyllabusService._apply_teacher_progress_to_dict(
                                    subtopic, progress_map.get(('subtopic', subtopic['id']))
                                )

                # Calculate stats based on potentially overridden data
                lessons = syllabus_dict['lessons']
                total_lessons = len(lessons)
                completed_lessons = sum(1 for l in lessons if l['status'] == 'completed')
                in_progress_lessons = sum(1 for l in lessons if l['status'] == 'in_progress')

                topics = []
                for l in lessons:
                    topics.extend(l.get('topics', []))
                total_topics = len(topics)
                completed_topics = sum(1 for t in topics if t['status'] == 'completed')

                subtopics = []
                for t in topics:
                    subtopics.extend(t.get('subtopics', []))
                total_subtopics = len(subtopics)
                completed_subtopics = sum(1 for s in subtopics if s.get('is_completed'))

                # Check for overdue items
                today = date.today()
                overdue_items = []

                # Check lessons for overdue
                for l in lessons:
                    if l.get('planned_end_date'):
                        planned_end = datetime.strptime(l['planned_end_date'], '%Y-%m-%d').date() if isinstance(l['planned_end_date'], str) else l['planned_end_date']
                        if planned_end < today and l['status'] != 'completed':
                            overdue_items.append({
                                'id': l['id'],
                                'title': l['title'],
                                'type': 'lesson',
                                'planned_end_date': planned_end.isoformat(),
                                'days_overdue': (today - planned_end).days,
                                'status': l['status']
                            })

                return {
                    'syllabus': syllabus_dict,
                    'total_lessons': total_lessons,
                    'lessons_completed': completed_lessons,
                    'lessons_in_progress': in_progress_lessons,
                    'lessons_planned': total_lessons - completed_lessons - in_progress_lessons,
                    'total_topics': total_topics,
                    'topics_completed': completed_topics,
                    'topics_in_progress': sum(1 for t in topics if t['status'] == 'in_progress'),
                    'topics_planned': total_topics - completed_topics - sum(1 for t in topics if t['status'] == 'in_progress'),
                    'total_subtopics': total_subtopics,
                    'subtopics_completed': completed_subtopics,
                    'subtopics_in_progress': sum(1 for s in subtopics if s['status'] == 'in_progress'),
                    'subtopics_planned': total_subtopics - completed_subtopics - sum(1 for s in subtopics if s['status'] == 'in_progress'),
                    'overall_completion_percentage': float(syllabus_dict['completion_percentage']),
                    'status_breakdown': {
                        'planned': sum(1 for l in lessons if l['status'] == 'planned'),
                        'in_progress': in_progress_lessons,
                        'completed': completed_lessons
                    },
                    'overdue_items': overdue_items
                }

        except Exception as e:
            raise Exception(f"Failed to get analytics: {str(e)}")

    @staticmethod
    def get_teacher_progress_summary(skid, teacher_id, academic_year_id):
        """Get summary of all syllabi for a teacher"""
        try:
            syllabi = SyllabusService.get_syllabi_by_teacher(skid, teacher_id, academic_year_id)

            total_syllabi = len(syllabi)
            completed_syllabi = sum(1 for s in syllabi if s['status'] == 'completed')
            in_progress_syllabi = sum(1 for s in syllabi if s['status'] == 'in_progress')

            avg_completion = sum(s['completion_percentage'] for s in syllabi) / total_syllabi if total_syllabi > 0 else 0

            return {
                'teacher_id': teacher_id,
                'academic_year_id': academic_year_id,
                'total_syllabi': total_syllabi,
                'completed_syllabi': completed_syllabi,
                'in_progress_syllabi': in_progress_syllabi,
                'planned_syllabi': total_syllabi - completed_syllabi - in_progress_syllabi,
                'average_completion_percentage': round(avg_completion, 2),
                'syllabi': syllabi
            }

        except Exception as e:
            raise Exception(f"Failed to get teacher summary: {str(e)}")
