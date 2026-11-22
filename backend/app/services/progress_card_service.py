from app.models.tenant import Teacher, Student, SchoolUsers, Subject  
from app.models.tenant.ExamModels import *
from app.models.tenant.MarksModels import MarksEntry
from app.models.tenant.Sections import Section
from app.models.tenant.Class import Class
from app.utils.db_manager import switch_to_school_db
from sqlalchemy import func, or_
from datetime import date
import logging
_log = logging.getLogger(__name__)


def _progress_card_attendance(tenant_session, student, exam_id):
    """
    Real attendance for a progress card: from the start of the academic year up to the last
    exam date of this exam for the student's class (or today, if that date is still ahead).
    Present = Present + Late, total = days with attendance marked (same as the attendance
    service). Returns None when no attendance has been marked in that period.
    """
    from app.models.tenant.AcademicYear import AcademicYear
    from app.models.tenant.Attendance import Attendance
    from app.utils.attendance_status import status_key

    exam_rows = tenant_session.query(ExamTimetable).filter(
        ExamTimetable.exam_type_id == exam_id,
        ExamTimetable.class_id == student.class_id,
        or_(ExamTimetable.section_id == student.section_id, ExamTimetable.section_id == None),
    ).all()
    year = None
    if exam_rows:
        year = tenant_session.query(AcademicYear).filter_by(id=exam_rows[0].academic_year_id).first()
    if year is None:
        year = tenant_session.query(AcademicYear).filter_by(is_current=True).first()
    if year is None:
        return None

    last_exam_day = max((row.exam_date for row in exam_rows), default=None)
    period_end = min(d for d in (last_exam_day, date.today(), year.end_date) if d is not None)
    period_start = year.start_date
    if period_end < period_start:
        return None

    records = tenant_session.query(Attendance.status).filter(
        Attendance.student_user_id == student.user_id,
        Attendance.date >= period_start,
        Attendance.date <= period_end,
    ).all()
    total_days = len(records)
    if total_days == 0:
        return None
    present_days = sum(1 for (status,) in records if status_key(status) in ('PRESENT', 'LATE'))
    return {
        'present_days': present_days,
        'total_days': total_days,
        'percentage': round(present_days / total_days * 100, 1),
        'from': period_start.isoformat(),
        'to': period_end.isoformat(),
    }


def _subject_outcome(config, marks_entry):
    """
    One subject's result (QA B26): ('marked', marks, passed) - passed when marks reach THAT subject's pass mark;
    ('absent', 0, False); or ('not_entered', None, None) - no marks yet: left out of totals, never shown as F.
    """
    if marks_entry is None or (not marks_entry.is_absent and marks_entry.total_marks is None):
        return 'not_entered', None, None
    if marks_entry.is_absent:
        return 'absent', 0.0, False
    marks = float(marks_entry.total_marks)
    return 'marked', marks, marks >= float(config.min_passing_marks or 0)


def _overall_result(outcomes):
    """Owner's rule: Pass only if every subject is passed; Incomplete while any subject's marks aren't entered."""
    if not outcomes or any(state == 'not_entered' for state, _, _ in outcomes):
        return 'Incomplete'
    return 'Pass' if all(passed for _, _, passed in outcomes) else 'Fail'


class ProgressCardService:

    @staticmethod
    def get_teacher_class(teacher_id, skid):
        """Get class assigned to teacher as class teacher"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Find section where this teacher is the class teacher
                section = tenant_session.query(Section).filter_by(
                    teacher_id=teacher_id  # ✅ Changed from class_teacher_of_section_id
                ).first()
                
                if not section:
                    raise ValueError("No class assigned as class teacher")
                
                # Get the class information
                class_info = tenant_session.query(Class).filter_by(
                    id=section.class_id
                ).first()
                
                if not class_info:
                    raise ValueError("Class information not found")
                
                return {
                    'class_id': section.class_id,
                    'section_id': section.id,
                    'class_name': class_info.class_name,
                    'section_name': section.section_name
                }
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to fetch class info: {str(e)}")

    
    @staticmethod
    def get_class_progress(exam_id, class_id, section_id, skid, academic_year_id):
        """Calculate complete class progress"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Fetch all exam configs for this class
                configs = tenant_session.query(ExamSubjectConfig).filter_by(
                    exam_type_id=exam_id,
                    class_id=class_id
                ).filter(
                    or_(
                        ExamSubjectConfig.section_id == section_id,
                        ExamSubjectConfig.section_id == None
                    )
                ).all()
                
                # Fetch all students
                students = tenant_session.query(Student, SchoolUsers).join(
                    SchoolUsers, Student.user_id == SchoolUsers.id
                ).filter(
                    Student.section_id == section_id
                ).all()
                
                student_progress = []
                subject_stats = {}
                
                for student, school_user in students:
                    student_total = 0
                    student_max = 0
                    subject_marks = []
                    
                    outcomes = []
                    for config in configs:
                        marks_entry = tenant_session.query(MarksEntry).filter_by(
                            exam_config_id=config.id,
                            student_id=student.user_id,
                            academic_year_id=academic_year_id
                        ).first()

                        state, marks, passed = _subject_outcome(config, marks_entry)
                        outcomes.append((state, marks, passed))
                        if state != 'not_entered':  # not-entered subjects are left out of the total
                            student_total += marks
                            student_max += config.total_max_marks

                        subject_marks.append({
                            'subject_id': config.subject_id,
                            'marks': marks,
                            'max_marks': config.total_max_marks,
                            'min_passing': config.min_passing_marks,
                            'is_absent': state == 'absent',
                            'not_entered': state == 'not_entered',
                            'passed': passed,
                        })
                        
                        # Calculate subject statistics
                        if config.subject_id not in subject_stats:
                            subject_stats[config.subject_id] = {
                                'subject_name': config.subject.subject_name,
                                'subject_code': config.subject.subject_code,
                                'max_marks': config.total_max_marks,
                                'min_passing': config.min_passing_marks,
                                'marks_list': []
                            }
                        if state != 'not_entered':
                            subject_stats[config.subject_id]['marks_list'].append(marks)
                    
                    percentage = (student_total / student_max * 100) if student_max > 0 else 0
                    grade = ProgressCardService._calculate_grade(percentage)
                    
                    student_progress.append({
                        'student_id': student.user_id,
                        'student_name': f"{school_user.first_name} {school_user.last_name}",
                        'roll_number': student.roll_no,
                        'total_marks': student_total,
                        'max_marks': student_max,
                        'percentage': percentage,
                        'grade': grade,
                        'status': _overall_result(outcomes),  # Pass / Fail / Incomplete
                        'subject_marks': subject_marks
                    })
                
                # Sort by percentage descending and assign ranks
                student_progress.sort(key=lambda x: x['percentage'], reverse=True)
                for idx, student in enumerate(student_progress):
                    student['rank'] = idx + 1
                
                # Calculate subject analysis
                subject_analysis = []
                for subject_id, stats in subject_stats.items():
                    marks_list = stats['marks_list']
                    passing_count = sum(1 for m in marks_list if m >= stats['min_passing'])
                    
                    subject_analysis.append({
                        'subject_id': subject_id,
                        'subject_name': stats['subject_name'],
                        'subject_code': stats['subject_code'],
                        'max_marks': stats['max_marks'],
                        'average_marks': sum(marks_list) / len(marks_list) if marks_list else 0,
                        'highest_marks': max(marks_list) if marks_list else 0,
                        'lowest_marks': min(marks_list) if marks_list else 0,
                        'pass_percentage': (passing_count / len(marks_list) * 100) if marks_list else 0
                    })
                
                # Class statistics
                total_students = len(students)
                pass_count = sum(1 for s in student_progress if s['status'] == 'Pass')
                topper = student_progress[0] if student_progress else None
                
                return {
                    'statistics': {
                        'total_students': total_students,
                        'class_average': sum(s['percentage'] for s in student_progress) / total_students if total_students > 0 else 0,
                        'pass_count': pass_count,
                        'pass_percentage': (pass_count / total_students * 100) if total_students > 0 else 0,
                        'topper_name': topper['student_name'] if topper else 'N/A',
                        'topper_percentage': topper['percentage'] if topper else 0
                    },
                    'subject_analysis': subject_analysis,
                    'student_progress': student_progress
                }
        except Exception as e:
            raise Exception(f"Failed to calculate class progress: {str(e)}")
    
    @staticmethod
    def bulk_generate_report_cards(data, skid):
        """
        Report cards for every active student in a section for one exam, in roll-number order
        (the route existed but this method didn't, so it always failed with a 500).
        data: {exam_type_id (or exam_id), section_id}
        """
        exam_id = data.get('exam_type_id') or data.get('exam_id')
        section_id = data.get('section_id')
        if not exam_id or not section_id:
            raise ValueError("exam_type_id and section_id are required")
        with switch_to_school_db(skid) as tenant_session:
            rows = tenant_session.query(Student.user_id, Student.roll_no).join(
                SchoolUsers, Student.user_id == SchoolUsers.id
            ).filter(
                Student.section_id == int(section_id),
                SchoolUsers.is_active.is_(True),
            ).all()
        rows.sort(key=lambda r: (r.roll_no is None, str(r.roll_no or '').zfill(8)))
        cards, skipped = [], []
        for row in rows:
            try:
                cards.append(ProgressCardService.calculate_progress_card(row.user_id, int(exam_id), skid))
            except Exception as e:  # one student's problem shouldn't stop the whole class
                skipped.append({'student_id': row.user_id, 'reason': str(e)})
        return {'count': len(cards), 'cards': cards, 'skipped': skipped}

    @staticmethod
    def _calculate_grade(percentage):
        """Calculate grade based on percentage"""
        if percentage >= 90:
            return 'A+'
        elif percentage >= 80:
            return 'A'
        elif percentage >= 70:
            return 'B+'
        elif percentage >= 60:
            return 'B'
        elif percentage >= 50:
            return 'C'
        elif percentage >= 35:
            return 'D'
        else:
            return 'F'
    
    @staticmethod
    def calculate_progress_card(student_id, exam_id, skid):
        """Calculate individual student progress card"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Get student info using user_id as primary key
                student = tenant_session.query(Student).filter_by(
                    user_id=student_id
                ).first()
                
                if not student:
                    raise ValueError("Student not found")
                
                # Get school user info using the relationship
                school_user = student.user
                
                if not school_user:
                    raise ValueError("Student user information not found")
                
                # Get section using the section_obj relationship or query separately
                section = tenant_session.query(Section).filter_by(
                    id=student.section_id
                ).first()
                
                if not section:
                    raise ValueError("Section not found")
                
                # Get class info
                class_info = tenant_session.query(Class).filter_by(
                    id=student.class_id  # or section.class_id
                ).first()
                
                # Get exam configs for student's class
                configs = tenant_session.query(ExamSubjectConfig).filter_by(
                    exam_type_id=exam_id,
                    class_id=student.class_id
                ).filter(
                    or_(
                        ExamSubjectConfig.section_id == student.section_id,
                        ExamSubjectConfig.section_id == None
                    )
                ).all()
                
                if not configs:
                    raise ValueError("No exam configuration found for this class")
                
                # Get exam type info
                exam_type = tenant_session.query(ExamType).filter_by(
                    id=exam_id
                ).first()
                
                subject_details = []
                outcomes = []
                total_marks_obtained = 0
                total_max_marks = 0
                
                for config in configs:
                    # Get subject info
                    subject = tenant_session.query(Subject).filter_by(
                        id=config.subject_id
                    ).first()
                    
                    # Get marks entry using student's user_id
                    marks_entry = tenant_session.query(MarksEntry).filter_by(
                        exam_config_id=config.id,
                        student_id=student_id  # This is user_id
                    ).first()
                    
                    state, total_marks, passed = _subject_outcome(config, marks_entry)
                    outcomes.append((state, total_marks, passed))
                    if state != 'not_entered':
                        total_marks_obtained += total_marks
                        total_max_marks += config.total_max_marks

                        percentage = (total_marks / config.total_max_marks * 100) if config.total_max_marks > 0 else 0
                                                
                        subject_details.append({
                            'subject_id': config.subject_id,
                            'subject_name': subject.subject_name if subject else 'Unknown',
                            'subject_code': subject.subject_code if subject else 'N/A',
                            'has_internal_external': config.has_internal_external,
                            'internal_marks': marks_entry.internal_marks,
                            'external_marks': marks_entry.external_marks,
                            'total_marks': total_marks,
                            'max_marks': config.total_max_marks,
                            'percentage': percentage,
                            'grade': ProgressCardService._calculate_grade(percentage),
                            'is_absent': marks_entry.is_absent,
                            'not_entered': False,
                            'min_passing_marks': config.min_passing_marks,
                            'passed': passed,
                            'remarks': marks_entry.remarks or ''
                        })
                    else:
                        # No marks yet: shown as "-" (it used to be 0 / grade F) and left out of the total
                        subject_details.append({
                            'subject_id': config.subject_id,
                            'subject_name': subject.subject_name if subject else 'Unknown',
                            'subject_code': subject.subject_code if subject else 'N/A',
                            'has_internal_external': config.has_internal_external,
                            'internal_marks': None,
                            'external_marks': None,
                            'total_marks': None,
                            'max_marks': config.total_max_marks,
                            'percentage': None,
                            'grade': '-',
                            'is_absent': False,
                            'not_entered': True,
                            'min_passing_marks': config.min_passing_marks,
                            'passed': None,
                            'remarks': 'Marks not entered'
                        })
                
                overall_percentage = (total_marks_obtained / total_max_marks * 100) if total_max_marks > 0 else 0
                overall_grade = ProgressCardService._calculate_grade(overall_percentage)
                
                # Calculate rank
                rank = ProgressCardService._calculate_rank(student_id, exam_id, student.section_id, tenant_session)
                total_students = tenant_session.query(Student).filter_by(
                    section_id=student.section_id
                ).count()
                
                # Get class teacher info
                class_teacher_name = 'N/A'
                if section.teacher_id:
                    # Get teacher's school user info
                    teacher_user = tenant_session.query(SchoolUsers).filter_by(
                        id=section.teacher_id
                    ).first()
                    if teacher_user:
                        class_teacher_name = f"{teacher_user.first_name} {teacher_user.last_name}"
                
                return {
                    'student_id': student_id,
                    'student_name': f"{school_user.first_name} {school_user.last_name}",
                    'roll_number': student.roll_no,
                    'class_name': class_info.class_name if class_info else 'Unknown',
                    'section_name': section.section_name,
                    'exam_name': exam_type.exam_name if exam_type else 'N/A',
                    'exam_code': exam_type.exam_code if exam_type else 'N/A',
                    'subject_details': subject_details,
                    'overall_total_marks': total_marks_obtained,
                    'overall_max_marks': total_max_marks,
                    'overall_percentage': overall_percentage,
                    'overall_grade': overall_grade,
                    'result': _overall_result(outcomes),  # Pass / Fail / Incomplete
                    'rank': rank,
                    'total_students': total_students,
                    'class_teacher_name': class_teacher_name,
                    # No remarks feature exists yet: don't invent one (the card shows "No remarks provided.")
                    'class_teacher_remarks': None,
                    # Real attendance (None = nothing marked yet; the card then hides the box)
                    'attendance': _progress_card_attendance(tenant_session, student, exam_id),
                }
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to calculate progress card: {str(e)}")

    @staticmethod
    def get_student_annual_report(student_id, academic_year_id, skid):
        """Get annual report for a student showing all exams"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Get student info
                student = tenant_session.query(Student).filter_by(
                    user_id=student_id
                ).first()

                if not student:
                    raise ValueError("Student not found")

                school_user = student.user
                section = tenant_session.query(Section).filter_by(
                    id=student.section_id
                ).first()
                class_info = tenant_session.query(Class).filter_by(
                    id=student.class_id
                ).first()

                # Get all exam types
                exam_types = tenant_session.query(ExamType).all()

                exam_results = []

                for exam_type in exam_types:
                    # Get exam configs for this exam and student's class
                    configs = tenant_session.query(ExamSubjectConfig).filter_by(
                        exam_type_id=exam_type.id,
                        class_id=student.class_id
                    ).filter(
                        or_(
                            ExamSubjectConfig.section_id == student.section_id,
                            ExamSubjectConfig.section_id == None
                        )
                    ).all()

                    if not configs:
                        continue  # Skip exams with no configuration

                    subjects = []
                    outcomes = []
                    total_marks_obtained = 0
                    total_max_marks = 0
                    has_marks = False

                    for config in configs:
                        # Get subject info
                        subject = tenant_session.query(Subject).filter_by(
                            id=config.subject_id
                        ).first()

                        # Get marks entry
                        marks_entry = tenant_session.query(MarksEntry).filter_by(
                            exam_config_id=config.id,
                            student_id=student_id,
                            academic_year_id=academic_year_id
                        ).first()

                        state, total_marks, passed = _subject_outcome(config, marks_entry)
                        outcomes.append((state, total_marks, passed))
                        if state != 'not_entered':
                            has_marks = True
                            total_marks_obtained += total_marks
                            total_max_marks += config.total_max_marks
                            subjects.append({
                                'subject_name': subject.subject_name if subject else 'Unknown',
                                'max_marks': config.total_max_marks,
                                'obtained_marks': total_marks,
                                'min_passing_marks': config.min_passing_marks,
                                'is_absent': state == 'absent',
                                'not_entered': False,
                                'passed': passed,
                                'grade': 'AB' if state == 'absent' else ProgressCardService._calculate_grade(
                                    (total_marks / config.total_max_marks * 100) if config.total_max_marks > 0 else 0
                                )
                            })
                        else:
                            # No marks yet: "-" (it used to be 0 / grade F), left out of the total
                            subjects.append({
                                'subject_name': subject.subject_name if subject else 'Unknown',
                                'max_marks': config.total_max_marks,
                                'obtained_marks': None,
                                'min_passing_marks': config.min_passing_marks,
                                'is_absent': False,
                                'not_entered': True,
                                'passed': None,
                                'grade': '-'
                            })

                    # Only include exam if student has at least some marks
                    if has_marks:
                        percentage = (total_marks_obtained / total_max_marks * 100) if total_max_marks > 0 else 0
                        grade = ProgressCardService._calculate_grade(percentage)
                        rank = ProgressCardService._calculate_rank(student_id, exam_type.id, student.section_id, tenant_session)

                        exam_results.append({
                            'exam_id': str(exam_type.id),
                            'exam_name': exam_type.exam_name,
                            'total_marks': total_max_marks,
                            'obtained_marks': total_marks_obtained,
                            'percentage': round(percentage, 2),
                            'grade': grade,
                            'result': _overall_result(outcomes),  # Pass / Fail / Incomplete
                            'rank': rank,
                            'subjects': subjects
                        })

                return {
                    'student_info': {
                        'student_name': f"{school_user.first_name} {school_user.last_name}",
                        'roll_number': student.roll_no,
                        'class_name': class_info.class_name if class_info else 'Unknown',
                        'section_name': section.section_name if section else 'Unknown'
                    },
                    'exam_results': exam_results
                }
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to fetch annual report: {str(e)}")

    
    @staticmethod
    def _calculate_rank(student_id, exam_id, section_id, session):
        """Calculate student's rank in section"""
        try:
            # Get section info to get class_id
            section = session.query(Section).filter_by(id=section_id).first()
            if not section:
                return 0
            
            # Get all students in this section using user_id
            students = session.query(Student).filter_by(section_id=section_id).all()
            
            # Get all exam configs for this class
            configs = session.query(ExamSubjectConfig).filter_by(
                exam_type_id=exam_id,
                class_id=section.class_id
            ).filter(
                or_(
                    ExamSubjectConfig.section_id == section_id,
                    ExamSubjectConfig.section_id == None
                )
            ).all()
            
            student_marks = []
            for student in students:
                total = 0
                for config in configs:
                    # Use student.user_id as student_id in MarksEntry
                    marks_entry = session.query(MarksEntry).filter_by(
                        exam_config_id=config.id,
                        student_id=student.user_id  # ✅ Changed from student.id
                    ).first()
                    if marks_entry and not marks_entry.is_absent:
                        total += marks_entry.total_marks
                
                student_marks.append((student.user_id, total))
            
            # Sort by marks descending
            student_marks.sort(key=lambda x: x[1], reverse=True)
            
            # Find rank
            for idx, (sid, marks) in enumerate(student_marks):
                if sid == student_id:
                    return idx + 1
            
            return len(students)
        except Exception as e:
            _log.error(f"Error calculating rank: {str(e)}")
            return 0
