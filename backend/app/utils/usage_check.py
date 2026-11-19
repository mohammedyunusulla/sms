"""
"Is this still in use?" checks used before deleting classes and subjects.
Each rule is (table, column, human label). Counts are per tenant DB.
"""
from sqlalchemy import text

CLASS_REFERENCES = [
    ('students', 'class_id', 'students'),
    ('student_enrollments', 'class_id', 'enrollment records'),
    ('fee_structures', 'class_id', 'fee structures'),
    ('timetables', 'class_id', 'timetables'),
    ('exam_subject_configs', 'class_id', 'exam subject setups'),
    ('exam_timetables', 'class_id', 'exam timetable entries'),
    ('attendance', 'class_id', 'attendance records'),
    ('assignments', 'class_id', 'assignments'),
    ('homework_assignments', 'class_id', 'homework assignments'),
    ('subjects', 'class_id', 'subjects'),
    ('promotion_history', 'from_class_id', 'promotion records'),
    ('promotion_history', 'to_class_id', 'promotion records'),
]

SUBJECT_REFERENCES = [
    ('section_subjects', 'subject_id', 'section links'),
    ('teacher_subjects', 'subject_id', 'teacher assignments'),
    ('timetable_entries', 'subject_id', 'timetable periods'),
    ('exam_subject_configs', 'subject_id', 'exam subject setups'),
    ('exam_timetables', 'subject_id', 'exam timetable entries'),
    ('syllabi', 'subject_id', 'syllabi'),
    ('assignments', 'subject_id', 'assignments'),
]


# Section subject links (section_subjects) are configuration only and are removed with the section.
SECTION_REFERENCES = [
    ('students', 'section_id', 'students'),
    ('student_enrollments', 'section_id', 'enrollment records'),
    ('attendance', 'section_id', 'attendance records'),
    ('timetables', 'section_id', 'timetables'),
    ('assignments', 'section_id', 'assignments'),
    ('homework_assignments', 'section_id', 'homework assignments'),
    ('exam_subject_configs', 'section_id', 'exam subject setups'),
    ('exam_timetables', 'section_id', 'exam timetable entries'),
    ('teacher_syllabus_assignments', 'section_id', 'syllabus assignments'),
    ('promotion_history', 'from_section_id', 'promotion records'),
    ('promotion_history', 'to_section_id', 'promotion records'),
]

def usage_summary(session, references, record_id):
    """Return e.g. ['9 students', '2 fee structures'] for every reference with rows (labels merged)."""
    counts = {}
    for table, column, label in references:
        n = session.execute(text(f'SELECT COUNT(*) FROM {table} WHERE {column} = :id'), {'id': int(record_id)}).scalar() or 0
        if n:
            counts[label] = counts.get(label, 0) + n
    return [f'{n} {label}' for label, n in counts.items()]


def blocked_message(name, kind, usage):
    return f"Can't delete {kind} \"{name}\": it still has {', '.join(usage)}. Remove or move these first."
