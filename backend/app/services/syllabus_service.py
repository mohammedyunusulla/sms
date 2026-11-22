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


def _next_position(session, model, parent_field, parent_id, requested=None):
    """
    Position for a new lesson / topic / subtopic. Deleted items give up their position (see _retire), so the
    next free number is max(active) + 1; a requested position already in use is refused (it used to be a 500).
    """
    from sqlalchemy import func
    parent_col = getattr(model, parent_field)
    if requested not in (None, ''):
        requested = int(requested)
        if requested < 1:
            raise ValueError("Position must be 1 or more")
        taken = session.query(model).filter(parent_col == parent_id, model.sequence_order == requested).first()
        if taken:
            raise ValueError(f"Position {requested} is already used by '{taken.title}'. Choose another position.")
        return requested
    top = session.query(func.max(model.sequence_order)).filter(parent_col == parent_id, model.is_active.is_(True)).scalar()
    candidate = (top or 0) + 1
    while session.query(model).filter(parent_col == parent_id, model.sequence_order == candidate).first():
        candidate += 1  # an old row could still sit on it
    return candidate


def _retire(item):
    """Soft delete an item and free its position (a deleted item kept its number and blocked the next one)."""
    item.is_active = False
    item.sequence_order = -item.id
    item.updated_at = datetime.utcnow()


def _retire_progress(session, item_type, item_ids):
    if item_ids:
        session.query(SyllabusProgressTracking).filter(
            SyllabusProgressTracking.item_type == item_type,
            SyllabusProgressTracking.item_id.in_(list(item_ids)),
        ).update({"is_active": False}, synchronize_session=False)


def _retire_lesson_tree(session, lessons):
    """Delete lessons with all their topics and subtopics (and their teacher progress)."""
    lesson_ids, topic_ids, subtopic_ids = set(), set(), set()
    for lesson in lessons:
        for topic in list(lesson.all_topics):
            for sub in list(topic.all_subtopics):
                if sub.is_active:
                    _retire(sub)
                    subtopic_ids.add(sub.id)
            if topic.is_active:
                _retire(topic)
                topic_ids.add(topic.id)
        if lesson.is_active:
            _retire(lesson)
            lesson_ids.add(lesson.id)
    _retire_progress(session, 'subtopic', subtopic_ids)
    _retire_progress(session, 'topic', topic_ids)
    _retire_progress(session, 'lesson', lesson_ids)


def _with_status_defaults(syllabus_dict):
    """Every item gets a status and %, also with no progress yet (analytics read them and raised KeyError)."""
    for key, default in (('status', 'planned'), ('completion_percentage', 0)):
        syllabus_dict.setdefault(key, default)
    for lesson in syllabus_dict.setdefault('lessons', []):
        lesson.setdefault('status', 'planned'); lesson.setdefault('completion_percentage', 0)
        for topic in lesson.setdefault('topics', []):
            topic.setdefault('status', 'planned'); topic.setdefault('completion_percentage', 0)
            for sub in topic.setdefault('subtopics', []):
                sub.setdefault('status', 'completed' if sub.get('is_completed') else 'planned')
                sub.setdefault('is_completed', False)
    return syllabus_dict


# ---------- per-section progress (QA B33) ----------
# A progress record belongs to a SECTION: a teacher with sections A and B ticks them separately, and whoever
# teaches the section next carries on from it. A teacher with no section assignment for the syllabus keeps
# their own records (section_id NULL), as before.

def _progress_scope(query, teacher_id, section_id):
    if section_id:
        return query.filter(SyllabusProgressTracking.section_id == int(section_id))
    return query.filter(SyllabusProgressTracking.teacher_id == teacher_id,
                        SyllabusProgressTracking.section_id.is_(None))


def _syllabus_id_of(session, item_type, item_id):
    """The syllabus a lesson / topic / subtopic belongs to (None if it doesn't exist)."""
    if item_type == 'syllabus':
        return int(item_id)
    if item_type == 'lesson':
        row = session.query(Lesson.syllabus_id).filter(Lesson.id == item_id).first()
    elif item_type == 'topic':
        row = session.query(Lesson.syllabus_id).join(Topic, Topic.lesson_id == Lesson.id).filter(Topic.id == item_id).first()
    elif item_type == 'subtopic':
        row = (session.query(Lesson.syllabus_id).join(Topic, Topic.lesson_id == Lesson.id)
               .join(Subtopic, Subtopic.topic_id == Topic.id).filter(Subtopic.id == item_id).first())
    else:
        raise ValueError(f"Invalid item_type: {item_type}")
    return row[0] if row else None


def _teacher_section_ids(session, syllabus_id, teacher_id):
    """Sections the teacher is actively assigned to for this syllabus (sorted)."""
    return sorted({a.section_id for a in session.query(TeacherSyllabusAssignment).filter_by(
        syllabus_id=syllabus_id, teacher_id=teacher_id, is_active=True).all()})


def _resolve_section(session, teacher_id, syllabus_id, section_id=None, default_first=False):
    """
    The section a teacher's progress is for. A chosen section must be one of theirs. With one section it is
    that one; with several, writes must say which (reads default to the first). None = no section assignment.
    """
    mine = _teacher_section_ids(session, syllabus_id, teacher_id)
    if section_id not in (None, '', 0, '0'):
        section_id = int(section_id)
        if section_id not in mine:
            raise ValueError("You aren't assigned to that section for this syllabus")
        return section_id
    if len(mine) == 1 or (mine and default_first):
        return mine[0]
    if mine:
        raise ValueError("Choose the section you're recording progress for")
    return None


def _section_options(session, section_ids):
    """[{section_id, label}] for a picker, e.g. 'Grade 5 - A'."""
    if not section_ids:
        return []
    sections = session.query(Section).filter(Section.id.in_(list(section_ids))).all()
    classes = {c.id: c.class_name for c in session.query(Class).filter(
        Class.id.in_([x.class_id for x in sections if x.class_id])).all()} if sections else {}
    out = [{'section_id': x.id, 'section_name': x.section_name, 'class_id': x.class_id,
            'label': f"{classes.get(x.class_id) or 'Class'} - {x.section_name}"} for x in sections]
    return sorted(out, key=lambda o: o['label'])


class SyllabusService:

    # ============== HELPER METHODS ==============

    @staticmethod
    def _get_or_create_progress(session, teacher_id, item_type, item_id, section_id=None):
        """The section's progress record for an item (the teacher's own without a section); teacher_id = who
        last recorded it."""
        progress = _progress_scope(session.query(SyllabusProgressTracking).filter_by(
            item_type=item_type,
            item_id=item_id,
            is_active=True
        ), teacher_id, section_id).first()

        if not progress:
            progress = SyllabusProgressTracking(
                teacher_id=teacher_id,
                section_id=section_id or None,
                item_type=item_type,
                item_id=item_id,
                status='planned',
                completion_percentage=0.00
            )
            session.add(progress)
            session.flush()
        else:
            progress.teacher_id = teacher_id

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
    def _cascade_complete_down(session, teacher_id, item_type, item_id, is_completed, section_id=None):
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
                tp = SyllabusService._get_or_create_progress(session, teacher_id, 'topic', topic.id, section_id)
                tp.status = status
                tp.completion_percentage = percentage
                if is_completed and not tp.actual_end_date:
                    tp.actual_end_date = date.today()
                elif not is_completed:
                    tp.actual_end_date = None
                # Cascade further into subtopics
                SyllabusService._cascade_complete_down(session, teacher_id, 'topic', topic.id, is_completed, section_id)

        elif item_type == 'topic':
            subtopics = session.query(Subtopic).filter_by(topic_id=item_id, is_active=True).all()
            for subtopic in subtopics:
                sp = SyllabusService._get_or_create_progress(session, teacher_id, 'subtopic', subtopic.id, section_id)
                sp.status = status
                sp.is_completed = is_completed
                sp.completion_percentage = percentage
                if is_completed and not sp.actual_completion_date:
                    sp.actual_completion_date = date.today()
                elif not is_completed:
                    sp.actual_completion_date = None

    @staticmethod
    def _compute_section_syllabus_pct(session, syllabus_id, section_id):
        """A section's completion: subtopics completed in that section / all subtopics."""
        subtopic_ids = [r[0] for r in session.query(Subtopic.id).join(
            Topic, Subtopic.topic_id == Topic.id
        ).join(
            Lesson, Topic.lesson_id == Lesson.id
        ).filter(
            Lesson.syllabus_id == syllabus_id,
            Lesson.is_active == True,
            Topic.is_active == True,
            Subtopic.is_active == True
        ).all()]
        base = session.query(SyllabusProgressTracking).filter(
            SyllabusProgressTracking.section_id == section_id,
            SyllabusProgressTracking.is_active == True)
        if not subtopic_ids:
            row = base.filter(SyllabusProgressTracking.item_type == 'syllabus',
                              SyllabusProgressTracking.item_id == syllabus_id).first()
            return (float(row.completion_percentage), row.status) if row else (0, 'planned')
        completed = base.filter(SyllabusProgressTracking.item_type == 'subtopic',
                                SyllabusProgressTracking.item_id.in_(subtopic_ids),
                                SyllabusProgressTracking.is_completed == True).count()
        pct = round((completed / len(subtopic_ids)) * 100, 2)
        return pct, ('completed' if pct >= 100 else 'in_progress' if pct > 0 else 'planned')

    @staticmethod
    def _own_syllabus_pct(session, syllabus_id, teacher_id):
        """A teacher's progress without a section (no section assignment)."""
        row = session.query(SyllabusProgressTracking).filter_by(
            teacher_id=teacher_id, section_id=None, item_type='syllabus', item_id=syllabus_id, is_active=True).first()
        return (float(row.completion_percentage), row.status) if row else (0, 'planned')

    @staticmethod
    def configure_timeline(skid, teacher_id, item_type, item_id, data, section_id=None):
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
                section_id = _resolve_section(session, teacher_id, _syllabus_id_of(session, item_type, item_id), section_id)

                progress = SyllabusService._get_or_create_progress(session, teacher_id, item_type, item_id, section_id)

                # Set planned dates
                # the planned end can't be before the planned start (it used to be accepted - QA B32)
                from app.utils.validators import to_date
                start = to_date(data['planned_start_date'], "Planned start date") if data.get('planned_start_date') else None
                end = to_date(data['planned_end_date'], "Planned end date") if data.get('planned_end_date') else None
                if start and end and end < start:
                    raise ValueError("The planned end date can't be before the planned start date")
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

        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to configure timeline: {str(e)}")

    @staticmethod
    def start_item(skid, teacher_id, item_type, item_id, section_id=None):
        """Start teaching a syllabus item (Start step). Requires item to be configured first."""
        try:
            with switch_to_school_db(skid) as session:
                syllabus_id = _syllabus_id_of(session, item_type, item_id)
                if not syllabus_id:
                    raise ValueError(f"{item_type.capitalize()} not found")
                section_id = _resolve_section(session, teacher_id, syllabus_id, section_id)
                # Get tracking record — must exist
                progress = _progress_scope(session.query(SyllabusProgressTracking).filter_by(
                    item_type=item_type,
                    item_id=item_id,
                    is_active=True
                ), teacher_id, section_id).first()

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
                    parent_progress = _progress_scope(session.query(SyllabusProgressTracking).filter_by(
                        item_type='lesson',
                        item_id=topic.lesson_id,
                        is_active=True
                    ), teacher_id, section_id).first()
                    if not parent_progress or parent_progress.status not in ('in_progress', 'completed'):
                        raise ValueError("Parent lesson must be started first")

                elif item_type == 'subtopic':
                    subtopic = session.query(Subtopic).filter_by(id=item_id, is_active=True).first()
                    if not subtopic:
                        raise ValueError("Subtopic not found")
                    parent_progress = _progress_scope(session.query(SyllabusProgressTracking).filter_by(
                        item_type='topic',
                        item_id=subtopic.topic_id,
                        is_active=True
                    ), teacher_id, section_id).first()
                    if not parent_progress or parent_progress.status not in ('in_progress', 'completed'):
                        raise ValueError("Parent topic must be started first")

                # Set to in_progress
                progress.status = 'in_progress'
                progress.actual_start_date = date.today()
                progress.teacher_id = teacher_id

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
    def mark_progress(skid, teacher_id, item_type, item_id, is_completed, section_id=None):
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

                section_id = _resolve_section(session, teacher_id, _syllabus_id_of(session, item_type, item_id), section_id)
                # Gate: check if item is started
                existing_progress = _progress_scope(session.query(SyllabusProgressTracking).filter_by(
                    item_type=item_type,
                    item_id=item_id,
                    is_active=True
                ), teacher_id, section_id).first()

                if existing_progress:
                    if existing_progress.status == 'planned':
                        raise ValueError(f"{item_type.capitalize()} must be started before marking progress. Use the Start button first.")
                # If no record exists, this is legacy/grandfathered data — allow and auto-set in_progress

                # Update the target item's progress
                progress = SyllabusService._get_or_create_progress(session, teacher_id, item_type, item_id, section_id)
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
                    SyllabusService._cascade_complete_down(session, teacher_id, item_type, item_id, is_completed, section_id)

                session.flush()

                # Cascade UP: recalculate parent completion percentages
                if item_type == 'subtopic':
                    SyllabusService._recalculate_teacher_topic_completion(session, teacher_id, item.topic_id, section_id)
                elif item_type == 'topic':
                    SyllabusService._recalculate_teacher_lesson_completion(session, teacher_id, item.lesson_id, section_id)
                elif item_type == 'lesson':
                    SyllabusService._recalculate_teacher_syllabus_completion(session, teacher_id, item.syllabus_id, section_id)

                session.commit()

                return {
                    'item_type': item_type,
                    'item_id': item_id,
                    'is_completed': is_completed,
                    'message': f'{item_type.capitalize()} {"completed" if is_completed else "reverted"} successfully'
                }

        except ValueError:
            raise
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

                    # The student's own section's progress (QA B33)
                    section_assigned = session.query(TeacherSyllabusAssignment).filter_by(
                        syllabus_id=syllabus.id, section_id=student.section_id).first()
                    if section_assigned:
                        completion_pct, status = SyllabusService._compute_section_syllabus_pct(
                            session, syllabus.id, student.section_id)
                        result_section = student.section_id
                    else:
                        # No teacher assigned to the section yet: the timetable teacher's own progress
                        completion_pct, status = SyllabusService._own_syllabus_pct(session, syllabus.id, teacher_id)
                        result_section = None

                    results.append({
                        'syllabus': syllabus.to_dict(),
                        'teacher_id': teacher_id,
                        'teacher_name': teacher_name,
                        'subject_id': subject_id,
                        'subject_name': subject_name,
                        'section_id': result_section,
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

                results = []
                for syllabus in syllabi:
                    subject = session.query(Subject).filter_by(id=syllabus.subject_id).first()
                    subject_name = subject.subject_name if subject else 'Unknown'
                    row = {
                        'syllabus': syllabus.to_dict(),
                        'teacher_id': teacher_id,
                        'teacher_name': teacher_name,
                        'subject_id': syllabus.subject_id,
                        'subject_name': subject_name,
                    }
                    # one row per section they teach it in (QA B33); their own progress without a section
                    options = _section_options(session, _teacher_section_ids(session, syllabus.id, teacher_id))
                    if not options:
                        pct, status = SyllabusService._own_syllabus_pct(session, syllabus.id, teacher_id)
                        results.append({**row, 'section_id': None, 'section_label': None,
                                        'completion_percentage': pct, 'status': status})
                    for opt in options:
                        pct, status = SyllabusService._compute_section_syllabus_pct(session, syllabus.id, opt['section_id'])
                        results.append({**row, 'section_id': opt['section_id'], 'section_label': opt['label'],
                                        'completion_percentage': pct, 'status': status})

                return results

        except Exception as e:
            raise Exception(f"Failed to get teacher syllabus progress view: {str(e)}")

    @staticmethod
    def get_student_syllabus_detail(skid, syllabus_id, teacher_id, section_id=None):
        """Full syllabus hierarchy with the section's progress (read-only); the teacher's own without a section."""
        try:
            if section_id:
                with switch_to_school_db(skid) as session:
                    assigned = session.query(TeacherSyllabusAssignment).filter_by(
                        syllabus_id=syllabus_id, section_id=section_id).first()
                if assigned or not teacher_id:
                    return SyllabusService.get_syllabus_by_id(skid, syllabus_id, None, include_hierarchy=True,
                                                             section_id=section_id)
                # no teacher assigned to the section yet: the timetable teacher's own progress (as the list shows)
            return SyllabusService.get_syllabus_by_id(skid, syllabus_id, teacher_id, include_hierarchy=True,
                                                     own_only=True)
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

                # One syllabus per subject and year (a database rule). A deleted one used to block creating a
                # new one; it now comes back as a fresh, empty syllabus (old content stays deleted).
                existing = session.query(Syllabus).filter_by(
                    subject_id=data['subject_id'],
                    academic_year_id=data['academic_year_id'],
                ).first()
                if existing and existing.is_active:
                    raise ValueError("Syllabus already exists for this subject and academic year")

                if existing:
                    _retire_lesson_tree(session, existing.all_lessons)
                    syllabus = existing
                    syllabus.is_active = True
                    syllabus.title = data['title']
                    syllabus.description = data.get('description')
                    syllabus.estimated_duration_hours = data.get('estimated_duration_hours', 0)
                    syllabus.created_by = teacher_id or syllabus.created_by
                    syllabus.updated_at = datetime.utcnow()
                    session.query(SyllabusProgressTracking).filter_by(
                        item_type='syllabus', item_id=syllabus.id
                    ).update({"is_active": False})
                else:
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

        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to create syllabus: {str(e)}")

    @staticmethod
    def get_syllabus_by_id(skid, syllabus_id, teacher_id=None, include_hierarchy=False, merge_section_progress=False,
                           section_id=None, own_only=False):
        """Get a syllabus, optionally with its full hierarchy and progress (QA B33: progress is per section).
        - teacher_id (a teacher's own page): their section's progress. With several sections, `section_id`
          picks one (default: the first); `sections` lists them for the picker. is_read_only when they are no
          longer assigned. Every item gets editable / completed_by.
        - section_id without teacher_id (admin, student, parent): that section's progress, read-only.
        - own_only: the teacher's records without a section (a teacher never assigned to a section).
        merge_section_progress is kept for old callers; progress is always the section's now.
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

                if not teacher_id and not section_id:
                    return syllabus_dict

                is_read_only = True
                if teacher_id and not own_only:
                    mine = _teacher_section_ids(session, syllabus_id, teacher_id)
                    is_read_only = not mine
                    if mine:
                        section_id = _resolve_section(session, teacher_id, syllabus_id, section_id, default_first=True)
                    else:
                        # a former teacher: the sections they used to teach, read-only (else their own records)
                        former = sorted({a.section_id for a in session.query(TeacherSyllabusAssignment).filter_by(
                            syllabus_id=syllabus_id, teacher_id=teacher_id).all()})
                        if section_id and int(section_id) not in former:
                            raise ValueError("You aren't assigned to that section for this syllabus")
                        section_id = int(section_id) if section_id else (former[0] if former else None)
                        mine = former
                    syllabus_dict['sections'] = _section_options(session, mine)
                    syllabus_dict['is_read_only'] = is_read_only
                syllabus_dict['section_id'] = int(section_id) if section_id else None

                progress_list = _progress_scope(session.query(SyllabusProgressTracking).filter(
                    SyllabusProgressTracking.is_active == True), teacher_id, section_id).all()
                progress_map = {(p.item_type, p.item_id): p for p in progress_list}
                names = {u.id: u.full_name for u in session.query(SchoolUsers).filter(
                    SchoolUsers.id.in_({p.teacher_id for p in progress_list})).all()} if progress_list else {}

                def apply_with_attribution(item_dict, item_type, item_id):
                    """The section's progress, who recorded the completion, and whether this teacher can change it."""
                    p = progress_map.get((item_type, item_id))
                    SyllabusService._apply_teacher_progress_to_dict(item_dict, p)
                    item_dict['editable'] = not is_read_only
                    done = p and (p.is_completed or p.status == 'completed')
                    item_dict['completed_by'] = names.get(p.teacher_id, 'Unknown') if done else None

                apply_with_attribution(syllabus_dict, 'syllabus', syllabus_id)
                if include_hierarchy and 'lessons' in syllabus_dict:
                    for lesson in syllabus_dict['lessons']:
                        apply_with_attribution(lesson, 'lesson', lesson['id'])
                        for topic in lesson.get('topics', []):
                            apply_with_attribution(topic, 'topic', topic['id'])
                            for subtopic in topic.get('subtopics', []):
                                apply_with_attribution(subtopic, 'subtopic', subtopic['id'])

                    # parents' percentages from their children (records carried over from several teachers
                    # may not have agreed)
                    for lesson in syllabus_dict['lessons']:
                        for topic in lesson.get('topics', []):
                            subtopics = topic.get('subtopics', [])
                            if subtopics:
                                topic_pct = round(sum(1 for x in subtopics if x.get('is_completed')) / len(subtopics) * 100, 2)
                                topic['completion_percentage'] = topic_pct
                                if topic_pct >= 100:
                                    topic['status'] = 'completed'
                                    topic['is_completed'] = True
                                elif topic_pct > 0 and topic.get('status') != 'completed':
                                    topic['status'] = 'in_progress'
                        topics = lesson.get('topics', [])
                        if topics:
                            lesson_pct = round(sum(float(t.get('completion_percentage') or 0) for t in topics) / len(topics), 2)
                            lesson['completion_percentage'] = lesson_pct
                            if lesson_pct >= 100:
                                lesson['status'] = 'completed'
                                lesson['is_completed'] = True
                            elif lesson_pct > 0 and lesson.get('status') != 'completed':
                                lesson['status'] = 'in_progress'
                    lessons = syllabus_dict.get('lessons', [])
                    if lessons:
                        syllabus_pct = round(sum(float(x.get('completion_percentage') or 0) for x in lessons) / len(lessons), 2)
                        syllabus_dict['completion_percentage'] = syllabus_pct
                        if syllabus_pct >= 100:
                            syllabus_dict['status'] = 'completed'
                        elif syllabus_pct > 0:
                            syllabus_dict['status'] = 'in_progress'

                return syllabus_dict

        except ValueError:
            raise
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
                # its lessons, topics and subtopics go with it (they used to stay active underneath)
                _retire_lesson_tree(session, syllabus.all_lessons)
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

                data['sequence_order'] = _next_position(session, Lesson, 'syllabus_id', syllabus_id, data.get('sequence_order'))

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

        except ValueError:
            raise
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
                    # Update the section's progress
                    section_id = _resolve_section(session, teacher_id, _syllabus_id_of(session, 'lesson', lesson_id), data.get('section_id'))
                    progress = SyllabusService._get_or_create_progress(session, teacher_id, 'lesson', lesson_id, section_id)
                    tracking_fields = ['status', 'planned_start_date', 'planned_end_date',
                                      'actual_start_date', 'actual_end_date', 'teacher_notes']
                    for field in tracking_fields:
                        if field in data:
                            setattr(progress, field, data[field])

                    session.commit()
                    # Recalculate teacher-specific parent completion
                    SyllabusService._recalculate_teacher_syllabus_completion(session, teacher_id, lesson.syllabus_id, section_id)
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

                # the lesson, its topics and subtopics; positions are freed
                _retire_lesson_tree(session, [lesson])

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

                data['sequence_order'] = _next_position(session, Topic, 'lesson_id', lesson_id, data.get('sequence_order'))

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

        except ValueError:
            raise
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
                    # Update the section's progress
                    section_id = _resolve_section(session, teacher_id, _syllabus_id_of(session, 'topic', topic_id), data.get('section_id'))
                    progress = SyllabusService._get_or_create_progress(session, teacher_id, 'topic', topic_id, section_id)
                    tracking_fields = ['status', 'planned_start_date', 'planned_end_date',
                                      'actual_start_date', 'actual_end_date', 'teacher_notes']
                    for field in tracking_fields:
                        if field in data:
                            setattr(progress, field, data[field])

                    session.commit()
                    # Recalculate teacher-specific parent completion
                    SyllabusService._recalculate_teacher_lesson_completion(session, teacher_id, topic.lesson_id, section_id)
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

                for sub in list(topic.all_subtopics):
                    if sub.is_active:
                        _retire(sub)
                        _retire_progress(session, 'subtopic', {sub.id})
                _retire(topic)

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

                data['sequence_order'] = _next_position(session, Subtopic, 'topic_id', topic_id, data.get('sequence_order'))

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

        except ValueError:
            raise
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
                    # Update the section's progress
                    section_id = _resolve_section(session, teacher_id, _syllabus_id_of(session, 'subtopic', subtopic_id), data.get('section_id'))
                    progress = SyllabusService._get_or_create_progress(session, teacher_id, 'subtopic', subtopic_id, section_id)
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
                    SyllabusService._recalculate_teacher_topic_completion(session, teacher_id, subtopic.topic_id, section_id)
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

                _retire(subtopic)

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
    def _recalculate_teacher_topic_completion(session, teacher_id, topic_id, section_id=None):
        """Recalculate teacher-specific topic completion based on subtopics"""
        topic = session.query(Topic).filter_by(id=topic_id).first()
        if not topic:
            return

        subtopics = session.query(Subtopic).filter_by(topic_id=topic_id, is_active=True).all()
        if not subtopics:
            return

        # Get all subtopic progress for this teacher
        subtopic_ids = [s.id for s in subtopics]
        progress_records = _progress_scope(session.query(SyllabusProgressTracking), teacher_id, section_id).filter(
            SyllabusProgressTracking.item_type == 'subtopic',
            SyllabusProgressTracking.item_id.in_(subtopic_ids),
            SyllabusProgressTracking.is_active == True
        ).all()

        completed_count = sum(1 for p in progress_records if p.is_completed)
        completion_percentage = Decimal((completed_count / len(subtopics)) * 100)

        # Update topic progress
        progress = SyllabusService._get_or_create_progress(session, teacher_id, 'topic', topic_id, section_id)
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
        SyllabusService._recalculate_teacher_lesson_completion(session, teacher_id, topic.lesson_id, section_id)

    @staticmethod
    def _recalculate_teacher_lesson_completion(session, teacher_id, lesson_id, section_id=None):
        """Recalculate teacher-specific lesson completion based on topics"""
        lesson = session.query(Lesson).filter_by(id=lesson_id).first()
        if not lesson:
            return

        topics = session.query(Topic).filter_by(lesson_id=lesson_id, is_active=True).all()
        if not topics:
            return

        # Get all topic progress for this teacher
        topic_ids = [t.id for t in topics]
        progress_records = _progress_scope(session.query(SyllabusProgressTracking), teacher_id, section_id).filter(
            SyllabusProgressTracking.item_type == 'topic',
            SyllabusProgressTracking.item_id.in_(topic_ids),
            SyllabusProgressTracking.is_active == True
        ).all()

        total_completion = sum(float(p.completion_percentage) for p in progress_records)
        completion_percentage = Decimal(total_completion / len(topics))

        # Update lesson progress
        progress = SyllabusService._get_or_create_progress(session, teacher_id, 'lesson', lesson_id, section_id)
        progress.completion_percentage = completion_percentage

        if completion_percentage == 100:
            progress.status = 'completed'
        elif completion_percentage > 0:
            progress.status = 'in_progress'

        session.commit()
        # Cascade
        SyllabusService._recalculate_teacher_syllabus_completion(session, teacher_id, lesson.syllabus_id, section_id)

    @staticmethod
    def _recalculate_teacher_syllabus_completion(session, teacher_id, syllabus_id, section_id=None):
        """Recalculate teacher-specific syllabus completion based on lessons"""
        syllabus = session.query(Syllabus).filter_by(id=syllabus_id).first()
        if not syllabus:
            return

        lessons = session.query(Lesson).filter_by(syllabus_id=syllabus_id, is_active=True).all()
        if not lessons:
            return

        # Get all lesson progress for this teacher
        lesson_ids = [l.id for l in lessons]
        progress_records = _progress_scope(session.query(SyllabusProgressTracking), teacher_id, section_id).filter(
            SyllabusProgressTracking.item_type == 'lesson',
            SyllabusProgressTracking.item_id.in_(lesson_ids),
            SyllabusProgressTracking.is_active == True
        ).all()

        total_completion = sum(float(p.completion_percentage) for p in progress_records)
        completion_percentage = Decimal(total_completion / len(lessons))

        # Update syllabus progress
        progress = SyllabusService._get_or_create_progress(session, teacher_id, 'syllabus', syllabus_id, section_id)
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

                # Ensure the section has a syllabus-level progress record (a new teacher carries on from it)
                progress = session.query(SyllabusProgressTracking).filter_by(
                    section_id=section_id,
                    item_type='syllabus',
                    item_id=syllabus_id,
                    is_active=True
                ).first()
                if not progress:
                    progress = SyllabusProgressTracking(
                        teacher_id=teacher_id,
                        section_id=section_id,
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

                # each section's own progress (QA B33)
                section_pct = {sid: SyllabusService._compute_section_syllabus_pct(session, syllabus_id, sid)
                               for sid in section_ids}

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
                        'class_name': class_map.get(sec.class_id, 'Unknown') if sec else 'Unknown',
                        'completion_percentage': section_pct.get(a.section_id, (0, 'planned'))[0],
                        'status': section_pct.get(a.section_id, (0, 'planned'))[1],
                    }
                    if section_info not in teacher_sections[a.teacher_id]:
                        teacher_sections[a.teacher_id].append(section_info)

                # Build results
                results = []
                for tid in teacher_ids:
                    # a teacher's figure = the average of their sections
                    secs = teacher_sections.get(tid, [])
                    pct = round(sum(x['completion_percentage'] for x in secs) / len(secs), 2) if secs else 0
                    results.append({
                        'teacher_id': tid,
                        'teacher_name': teacher_map.get(tid, 'Unknown'),
                        'completion_percentage': pct,
                        'status': 'completed' if pct >= 100 else 'in_progress' if pct > 0 else 'planned',
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

        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to get combined progress: {str(e)}")

    # ============== ANALYTICS & REPORTING ==============

    @staticmethod
    def get_syllabus_analytics(skid, syllabus_id, teacher_id=None, section_id=None):
        """
        Analytics for a syllabus (QA B33): one section's progress - a teacher's own section (the chosen one, else
        their first), or the section an admin picks. An admin without a section sees all sections combined
        (best status across them).
        """
        try:
            if teacher_id or section_id:
                syllabus_dict = SyllabusService.get_syllabus_by_id(
                    skid, syllabus_id, teacher_id, include_hierarchy=True, section_id=section_id)
            else:
                syllabus_dict = SyllabusService.get_syllabus_combined_progress(skid, syllabus_id, None)
            with switch_to_school_db(skid) as session:
                if not session.query(Syllabus).filter_by(id=syllabus_id, is_active=True).first():
                    raise ValueError("Syllabus not found")

                # Calculate stats based on potentially overridden data
                _with_status_defaults(syllabus_dict)
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

        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to get analytics: {str(e)}")

    @staticmethod
    def get_teacher_progress_summary(skid, teacher_id, academic_year_id):
        """Get summary of all syllabi for a teacher"""
        try:
            syllabi = SyllabusService.get_syllabi_by_teacher(skid, teacher_id, academic_year_id)
            # each syllabus: the average of the teacher's sections (QA B33), their own progress without one
            if syllabi:
                with switch_to_school_db(skid) as session:
                    for item in syllabi:
                        secs = _teacher_section_ids(session, item['id'], teacher_id)
                        figures = ([SyllabusService._compute_section_syllabus_pct(session, item['id'], x) for x in secs]
                                   or [SyllabusService._own_syllabus_pct(session, item['id'], teacher_id)])
                        pct = round(sum(f[0] for f in figures) / len(figures), 2)
                        item['completion_percentage'] = pct
                        item['status'] = 'completed' if pct >= 100 else 'in_progress' if pct > 0 else 'planned'

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
