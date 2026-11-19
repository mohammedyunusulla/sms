# services/exam_service.py

from app.models.tenant.ExamModels import ExamType, ExamSubjectConfig, ExamTimetable
from app.models.tenant.Class import Class
from app.models.tenant.Sections import Section
from app.models.tenant.SeatingArrangement import ExamSeatingConfig, SeatingPlan
from app.models.tenant.StudentEnrollment import StudentEnrollment
from app.models.tenant.Room import Room
from app.models.tenant.Teacher import Teacher
from app.models.tenant.SchoolUsers import SchoolUsers
from app.utils.db_manager import switch_to_school_db
from datetime import datetime, date, time

class ExamService:
    
    @staticmethod
    def create_exam_type(data, skid):
        """Create a new exam type"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Check for duplicate exam code
                existing = tenant_session.query(ExamType).filter_by(
                    exam_code=data['exam_code']
                ).first()
                
                if existing:
                    raise ValueError(f"Exam code '{data['exam_code']}' already exists")
                
                new_exam = ExamType(
                    exam_name=data['exam_name'],
                    exam_code=data['exam_code'],
                    exam_category=data.get('exam_category', 'Formative'),
                    sequence_order=data.get('sequence_order', 1)
                )
                
                tenant_session.add(new_exam)
                tenant_session.commit()
                tenant_session.refresh(new_exam)
                
                return new_exam.to_dict()
        except Exception as e:
            raise Exception(f"Failed to create exam type: {str(e)}")
    
    @staticmethod
    def get_all_exam_types(skid):
        """Get all exam types ordered by sequence"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                exam_types = tenant_session.query(ExamType).order_by(
                    ExamType.sequence_order
                ).all()

                return [exam.to_dict() for exam in exam_types]
        except Exception as e:
            raise Exception(f"Failed to fetch exam types: {str(e)}")

    @staticmethod
    def get_exam_type_by_id(exam_id, skid):
        """Get a single exam type by ID"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                exam = tenant_session.query(ExamType).filter_by(id=exam_id).first()

                if not exam:
                    return None

                return exam.to_dict()
        except Exception as e:
            raise Exception(f"Failed to fetch exam type: {str(e)}")
    
    @staticmethod
    def update_exam_type(exam_id, data, skid):
        """Update an existing exam type"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                exam = tenant_session.query(ExamType).filter_by(id=exam_id).first()
                
                if not exam:
                    raise ValueError("Exam type not found")
                
                # Check for duplicate exam code (excluding current exam)
                if data.get('exam_code') and data['exam_code'] != exam.exam_code:
                    existing = tenant_session.query(ExamType).filter_by(
                        exam_code=data['exam_code']
                    ).first()
                    if existing:
                        raise ValueError(f"Exam code '{data['exam_code']}' already exists")
                
                # Update fields
                exam.exam_name = data.get('exam_name', exam.exam_name)
                exam.exam_code = data.get('exam_code', exam.exam_code)
                exam.exam_category = data.get('exam_category', exam.exam_category)
                exam.sequence_order = data.get('sequence_order', exam.sequence_order)
                
                tenant_session.commit()
                tenant_session.refresh(exam)
                
                return exam.to_dict()
        except Exception as e:
            raise Exception(f"Failed to update exam type: {str(e)}")
    
    @staticmethod
    def delete_exam_type(exam_id, skid):
        """
        Delete an exam type - only when nothing real depends on it. Refused (with what is in the way)
        while it has marks, exam timetable entries or seating plans; its empty subject setups (no
        marks) are removed with it. This used to cascade-delete all marks silently.
        """
        from app.models.tenant.MarksModels import MarksEntry
        from app.utils.usage_check import blocked_message
        try:
            with switch_to_school_db(skid) as tenant_session:
                exam = tenant_session.query(ExamType).filter_by(id=exam_id).first()

                if not exam:
                    raise ValueError("Exam type not found")

                config_ids = [cid for (cid,) in tenant_session.query(ExamSubjectConfig.id).filter_by(exam_type_id=exam_id)]
                usage = []
                marks = tenant_session.query(MarksEntry).filter(MarksEntry.exam_config_id.in_(config_ids or [-1])).count()
                if marks:
                    usage.append(f"{marks} marks")
                timetable = tenant_session.query(ExamTimetable).filter_by(exam_type_id=exam_id).count()
                if timetable:
                    usage.append(f"{timetable} exam timetable entr{'y' if timetable == 1 else 'ies'}")
                seating = tenant_session.query(ExamSeatingConfig).filter_by(exam_type_id=exam_id).count()
                if seating:
                    usage.append(f"{seating} seating plan{'' if seating == 1 else 's'}")
                if usage:
                    raise ValueError(blocked_message(exam.exam_name, "exam", usage))

                # only empty subject setups are left: remove them with the exam type
                tenant_session.delete(exam)
                tenant_session.commit()

                return True
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to delete exam type: {str(e)}")
            

#-----------------------------------------( EXAM - SUBJECT CONFIG SERVICES )--------------------------------------------


    
    @staticmethod
    def create_exam_config(data, skid):
        """Create exam subject configuration"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Check for duplicate configuration
                existing = tenant_session.query(ExamSubjectConfig).filter_by(
                    exam_type_id=data['exam_type_id'],
                    class_id=data['class_id'],
                    section_id=data.get('section_id'),
                    subject_id=data['subject_id']
                ).first()
                
                if existing:
                    raise ValueError("Configuration already exists for this exam-subject combination")
                
                # Validation: maxima > 0, split adds up, passing mark within the total
                from app.utils.validators import exam_setup_marks
                internal, external, total, passing, weightage = exam_setup_marks(
                    data.get('has_internal_external'), data.get('internal_max_marks'), data.get('external_max_marks'),
                    data.get('total_max_marks'), data.get('min_passing_marks'), data.get('weightage_percentage', 100.0))
                data.update(internal_max_marks=internal, external_max_marks=external, total_max_marks=total,
                            min_passing_marks=passing, weightage_percentage=weightage)

                new_config = ExamSubjectConfig(
                    exam_type_id=data['exam_type_id'],
                    class_id=data['class_id'],
                    section_id=data.get('section_id'),
                    subject_id=data['subject_id'],
                    has_internal_external=data.get('has_internal_external', False),
                    internal_max_marks=data.get('internal_max_marks', 0),
                    external_max_marks=data.get('external_max_marks', 0),
                    total_max_marks=data['total_max_marks'],
                    min_passing_marks=data['min_passing_marks'],
                    weightage_percentage=data.get('weightage_percentage', 100.0)
                )
                
                tenant_session.add(new_config)
                tenant_session.commit()
                tenant_session.refresh(new_config)
                
                return new_config.to_dict()
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to create configuration: {str(e)}")
    
    @staticmethod
    def get_exam_configs(filters, skid):
        """Get exam configurations with filters"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                query = tenant_session.query(ExamSubjectConfig)

                if filters.get('exam_type_id'):
                    query = query.filter_by(exam_type_id=filters['exam_type_id'])
                if filters.get('class_id'):
                    query = query.filter_by(class_id=filters['class_id'])
                if filters.get('section_id'):
                    query = query.filter_by(section_id=filters['section_id'])
                if filters.get('subject_id'):
                    query = query.filter_by(subject_id=filters['subject_id'])

                configs = query.all()
                return [config.to_dict() for config in configs]
        except Exception as e:
            raise Exception(f"Failed to fetch configurations: {str(e)}")

    @staticmethod
    def get_exam_config_by_id(config_id, skid):
        """Get a single exam configuration by ID"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                config = tenant_session.query(ExamSubjectConfig).filter_by(id=config_id).first()

                if not config:
                    return None

                return config.to_dict()
        except Exception as e:
            raise Exception(f"Failed to fetch configuration: {str(e)}")
    
    @staticmethod
    def update_exam_config(config_id, data, skid):
        """Update exam configuration"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                config = tenant_session.query(ExamSubjectConfig).filter_by(id=config_id).first()
                
                if not config:
                    raise ValueError("Configuration not found")
                
                # Validate the setup as it will be after the update (sent values over current ones)
                from app.utils.validators import exam_setup_marks
                has_ie = data.get('has_internal_external', config.has_internal_external)
                internal, external, total, passing, weightage = exam_setup_marks(
                    has_ie,
                    data.get('internal_max_marks', config.internal_max_marks),
                    data.get('external_max_marks', config.external_max_marks),
                    data.get('total_max_marks', config.total_max_marks),
                    data.get('min_passing_marks', config.min_passing_marks),
                    data.get('weightage_percentage', config.weightage_percentage),
                )
                # Lowering a maximum must not leave entered marks above it
                from app.models.tenant.MarksModels import MarksEntry
                from sqlalchemy import or_
                over = tenant_session.query(MarksEntry).filter(
                    MarksEntry.exam_config_id == config_id,
                    or_(MarksEntry.total_marks > total,
                        MarksEntry.internal_marks > (internal if has_ie else total),
                        MarksEntry.external_marks > (external if has_ie else total)),
                ).count()
                if over:
                    raise ValueError(f"{over} student{'' if over == 1 else 's'} already ha{'s' if over == 1 else 've'} marks above the new maximum. Correct those marks first.")

                # Update fields
                config.has_internal_external = has_ie
                config.internal_max_marks = internal
                config.external_max_marks = external
                config.total_max_marks = total
                config.min_passing_marks = passing
                config.weightage_percentage = weightage
                
                tenant_session.commit()
                tenant_session.refresh(config)

                return config.to_dict()
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to update configuration: {str(e)}")
    
    @staticmethod
    def delete_exam_config(config_id, skid):
        """Delete exam configuration"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                config = tenant_session.query(ExamSubjectConfig).filter_by(id=config_id).first()
                
                if not config:
                    raise ValueError("Configuration not found")

                # Never delete marks silently: refuse while marks exist for this subject setup
                from app.models.tenant.MarksModels import MarksEntry
                marks_count = tenant_session.query(MarksEntry).filter_by(exam_config_id=config_id).count()
                if marks_count > 0:
                    subject = config.subject.subject_name if config.subject else "this subject"
                    raise ValueError(
                        f"Can't delete the {subject} setup: it has {marks_count} mark{'' if marks_count == 1 else 's'} entered. "
                        "Remove those marks first."
                    )

                tenant_session.delete(config)
                tenant_session.commit()

                return True
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to delete configuration: {str(e)}")
    
    @staticmethod
    def bulk_copy_configurations(data, skid):
        """Bulk copy configurations from one exam/class to another"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Fetch source configurations
                source_configs = tenant_session.query(ExamSubjectConfig).filter_by(
                    exam_type_id=data['from_exam_type_id'],
                    class_id=data['from_class_id']
                ).all()
                
                if not source_configs:
                    raise ValueError("No configurations found to copy")
                
                copied_count = 0
                skipped_count = 0
                
                for source in source_configs:
                    # Check if configuration already exists in target
                    existing = tenant_session.query(ExamSubjectConfig).filter_by(
                        exam_type_id=data['to_exam_type_id'],
                        class_id=data['to_class_id'],
                        section_id=data.get('to_section_id'),
                        subject_id=source.subject_id
                    ).first()
                    
                    if existing:
                        skipped_count += 1
                        continue
                    
                    # Create new configuration
                    new_config = ExamSubjectConfig(
                        exam_type_id=data['to_exam_type_id'],
                        class_id=data['to_class_id'],
                        section_id=data.get('to_section_id'),
                        subject_id=source.subject_id,
                        has_internal_external=source.has_internal_external,
                        internal_max_marks=source.internal_max_marks,
                        external_max_marks=source.external_max_marks,
                        total_max_marks=source.total_max_marks,
                        min_passing_marks=source.min_passing_marks,
                        weightage_percentage=source.weightage_percentage
                    )
                    
                    tenant_session.add(new_config)
                    copied_count += 1
                
                tenant_session.commit()
                
                return {
                    'copied_count': copied_count,
                    'skipped_count': skipped_count,
                    'total_source': len(source_configs)
                }
        except Exception as e:
            raise Exception(f"Failed to copy configurations: {str(e)}")


#-----------------------------------------( EXAM TIMETABLE SERVICES )--------------------------------------------


    @staticmethod
    def _enrich_timetable_entry(entry, tenant_session):
        """Add related names to a timetable dict"""
        result = entry.to_dict()

        # Add exam type name
        if entry.exam_type:
            result['exam_name'] = entry.exam_type.exam_name
        # Add class name
        if entry.class_:
            result['class_name'] = entry.class_.class_name
        # Add section name
        if entry.section:
            result['section_name'] = entry.section.section_name
        else:
            result['section_name'] = None
        # Add subject name
        if entry.subject:
            result['subject_name'] = entry.subject.subject_name

        # Format date and time for JSON serialization
        if result.get('exam_date'):
            result['exam_date'] = str(result['exam_date'])
        if result.get('start_time'):
            result['start_time'] = result['start_time'].strftime('%H:%M') if isinstance(result['start_time'], time) else str(result['start_time'])
        if result.get('end_time'):
            result['end_time'] = result['end_time'].strftime('%H:%M') if isinstance(result['end_time'], time) else str(result['end_time'])

        return result

    @staticmethod
    def create_exam_timetable(data, skid):
        """Create an exam timetable entry"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                if not data.get('academic_year_id'):
                    raise ValueError("academic_year_id is required")

                # Check for duplicate
                existing = tenant_session.query(ExamTimetable).filter_by(
                    academic_year_id=data['academic_year_id'],
                    exam_type_id=data['exam_type_id'],
                    class_id=data['class_id'],
                    section_id=data.get('section_id'),
                    subject_id=data['subject_id']
                ).first()

                if existing:
                    raise ValueError("Timetable entry already exists for this exam-class-subject combination")

                # Parse date and times
                exam_date = data['exam_date']
                if isinstance(exam_date, str):
                    exam_date = datetime.strptime(exam_date, '%Y-%m-%d').date()

                start_time = data['start_time']
                if isinstance(start_time, str):
                    start_time = datetime.strptime(start_time, '%H:%M').time()

                end_time = data['end_time']
                if isinstance(end_time, str):
                    end_time = datetime.strptime(end_time, '%H:%M').time()

                if end_time <= start_time:
                    raise ValueError("End time must be after start time")

                # Calculate duration if not provided
                duration = data.get('duration_minutes')
                if not duration:
                    start_dt = datetime.combine(datetime.today(), start_time)
                    end_dt = datetime.combine(datetime.today(), end_time)
                    duration = int((end_dt - start_dt).total_seconds() / 60)

                entry = ExamTimetable(
                    academic_year_id=data['academic_year_id'],
                    exam_type_id=data['exam_type_id'],
                    class_id=data['class_id'],
                    section_id=data.get('section_id'),
                    subject_id=data['subject_id'],
                    exam_date=exam_date,
                    start_time=start_time,
                    end_time=end_time,
                    duration_minutes=duration,
                    notes=data.get('notes')
                )

                tenant_session.add(entry)
                tenant_session.commit()
                tenant_session.refresh(entry)

                return ExamService._enrich_timetable_entry(entry, tenant_session)
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to create exam timetable entry: {str(e)}")

    @staticmethod
    def get_exam_timetables(filters, skid):
        """Get exam timetable entries with filters"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                query = tenant_session.query(ExamTimetable)

                if filters.get('academic_year_id'):
                    query = query.filter_by(academic_year_id=filters['academic_year_id'])
                if filters.get('exam_type_id'):
                    query = query.filter_by(exam_type_id=filters['exam_type_id'])
                if filters.get('class_id'):
                    query = query.filter_by(class_id=filters['class_id'])
                if filters.get('section_id'):
                    query = query.filter_by(section_id=filters['section_id'])

                entries = query.order_by(ExamTimetable.exam_date, ExamTimetable.start_time).all()
                return [ExamService._enrich_timetable_entry(e, tenant_session) for e in entries]
        except Exception as e:
            raise Exception(f"Failed to fetch exam timetables: {str(e)}")

    @staticmethod
    def get_exam_timetable_by_id(entry_id, skid):
        """Get a single exam timetable entry"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                entry = tenant_session.query(ExamTimetable).filter_by(id=entry_id).first()
                if not entry:
                    return None
                return ExamService._enrich_timetable_entry(entry, tenant_session)
        except Exception as e:
            raise Exception(f"Failed to fetch exam timetable entry: {str(e)}")

    @staticmethod
    def update_exam_timetable(entry_id, data, skid):
        """Update an exam timetable entry"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                entry = tenant_session.query(ExamTimetable).filter_by(id=entry_id).first()

                if not entry:
                    raise ValueError("Exam timetable entry not found")

                # Parse and update date/time fields
                if 'exam_date' in data:
                    val = data['exam_date']
                    entry.exam_date = datetime.strptime(val, '%Y-%m-%d').date() if isinstance(val, str) else val

                if 'start_time' in data:
                    val = data['start_time']
                    entry.start_time = datetime.strptime(val, '%H:%M').time() if isinstance(val, str) else val

                if 'end_time' in data:
                    val = data['end_time']
                    entry.end_time = datetime.strptime(val, '%H:%M').time() if isinstance(val, str) else val

                # Validate time ordering
                if entry.end_time <= entry.start_time:
                    raise ValueError("End time must be after start time")

                # Recalculate duration
                start_dt = datetime.combine(datetime.today(), entry.start_time)
                end_dt = datetime.combine(datetime.today(), entry.end_time)
                entry.duration_minutes = data.get('duration_minutes', int((end_dt - start_dt).total_seconds() / 60))

                # Update other fields
                if 'notes' in data:
                    entry.notes = data['notes']

                tenant_session.commit()
                tenant_session.refresh(entry)

                return ExamService._enrich_timetable_entry(entry, tenant_session)
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to update exam timetable entry: {str(e)}")

    @staticmethod
    def delete_exam_timetable(entry_id, skid):
        """Delete an exam timetable entry"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                entry = tenant_session.query(ExamTimetable).filter_by(id=entry_id).first()

                if not entry:
                    raise ValueError("Exam timetable entry not found")

                tenant_session.delete(entry)
                tenant_session.commit()

                return True
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to delete exam timetable entry: {str(e)}")

    @staticmethod
    def bulk_delete_exam_timetables(entry_ids, skid):
        """Bulk delete exam timetable entries"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                deleted = 0
                for eid in entry_ids:
                    entry = tenant_session.query(ExamTimetable).filter_by(id=eid).first()
                    if entry:
                        tenant_session.delete(entry)
                        deleted += 1

                tenant_session.commit()
                return {'deleted_count': deleted}
        except Exception as e:
            raise Exception(f"Failed to bulk delete exam timetable entries: {str(e)}")

    @staticmethod
    def get_student_exam_timetable(skid, student_id, exam_type_id, academic_year_id=None):
        """
        Get a student's exam timetable enriched with room, seat, and invigilator
        from the seating arrangement.
        """
        try:
            with switch_to_school_db(skid) as session:
                # Get student's enrollment to know their class/section
                enrollment_query = session.query(StudentEnrollment).filter(
                    StudentEnrollment.student_id == student_id,
                    StudentEnrollment.status == 'active'
                )
                if academic_year_id:
                    enrollment_query = enrollment_query.filter(
                        StudentEnrollment.academic_year_id == academic_year_id
                    )
                enrollment = enrollment_query.first()
                if not enrollment:
                    raise ValueError("Student enrollment not found")

                # Get exam timetable entries for this class
                tt_query = session.query(ExamTimetable).filter(
                    ExamTimetable.exam_type_id == exam_type_id,
                    ExamTimetable.class_id == enrollment.class_id,
                )
                if academic_year_id:
                    tt_query = tt_query.filter(ExamTimetable.academic_year_id == academic_year_id)

                # Include entries for student's section OR entries with no section (all sections)
                if enrollment.section_id:
                    from sqlalchemy import or_
                    tt_query = tt_query.filter(
                        or_(
                            ExamTimetable.section_id == enrollment.section_id,
                            ExamTimetable.section_id.is_(None)
                        )
                    )

                entries = tt_query.order_by(ExamTimetable.exam_date, ExamTimetable.start_time).all()

                results = []
                for entry in entries:
                    item = ExamService._enrich_timetable_entry(entry, session)

                    # Find the student's seating assignment for this exam slot
                    seating_config = session.query(ExamSeatingConfig).join(
                        SeatingPlan, SeatingPlan.config_id == ExamSeatingConfig.id
                    ).filter(
                        SeatingPlan.student_id == student_id,
                        ExamSeatingConfig.exam_type_id == exam_type_id,
                        ExamSeatingConfig.exam_date == entry.exam_date,
                        ExamSeatingConfig.start_time == entry.start_time,
                    ).first()

                    if seating_config:
                        # Get the specific seat plan
                        seat_plan = session.query(SeatingPlan).filter(
                            SeatingPlan.config_id == seating_config.id,
                            SeatingPlan.student_id == student_id,
                        ).first()

                        room = session.query(Room).filter_by(id=seating_config.room_id).first()
                        item['room'] = room.room_name if room else None
                        item['seat_label'] = seat_plan.seat_label if seat_plan else None
                        item['seat_row'] = seat_plan.seat_row if seat_plan else None
                        item['seat_column'] = seat_plan.seat_column if seat_plan else None

                        # Get invigilator name
                        if seating_config.invigilator_id:
                            teacher = session.query(Teacher).filter_by(
                                user_id=seating_config.invigilator_id
                            ).first()
                            if teacher and teacher.user:
                                item['invigilator_name'] = f"{teacher.user.first_name} {teacher.user.last_name}"
                            else:
                                item['invigilator_name'] = None
                        else:
                            item['invigilator_name'] = None
                    else:
                        item['room'] = None
                        item['seat_label'] = None
                        item['seat_row'] = None
                        item['seat_column'] = None
                        item['invigilator_name'] = None

                    results.append(item)

                return results
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to get student exam timetable: {str(e)}")

    @staticmethod
    def get_invigilator_schedule(skid, teacher_id, exam_type_id, academic_year_id=None):
        """
        Get all exam seating configs where the given teacher is the invigilator.
        Returns each config enriched with exam timetable subject info.
        """
        try:
            with switch_to_school_db(skid) as session:
                query = session.query(ExamSeatingConfig).filter(
                    ExamSeatingConfig.invigilator_id == teacher_id,
                    ExamSeatingConfig.exam_type_id == exam_type_id,
                )
                if academic_year_id:
                    query = query.filter(ExamSeatingConfig.academic_year_id == academic_year_id)

                configs = query.order_by(ExamSeatingConfig.exam_date, ExamSeatingConfig.start_time).all()

                results = []
                for config in configs:
                    room = session.query(Room).filter_by(id=config.room_id).first()

                    # Find matching exam timetable entries for this slot (may cover multiple classes)
                    tt_entries = session.query(ExamTimetable).filter(
                        ExamTimetable.exam_type_id == exam_type_id,
                        ExamTimetable.exam_date == config.exam_date,
                        ExamTimetable.start_time == config.start_time,
                    )
                    if academic_year_id:
                        tt_entries = tt_entries.filter(ExamTimetable.academic_year_id == academic_year_id)
                    tt_entries = tt_entries.all()

                    subjects = list({e.subject.subject_name for e in tt_entries if e.subject})
                    classes = []
                    for assignment in (config.class_assignments or []):
                        class_id = assignment.get('class_id')
                        section_id = assignment.get('section_id')
                        cls = session.query(Class).filter_by(id=class_id).first() if class_id else None
                        sec = session.query(Section).filter_by(id=section_id).first() if section_id else None
                        label = cls.class_name if cls else f"Class {class_id}"
                        if sec:
                            label += f" - {sec.section_name}"
                        classes.append(label)

                    exam_date = str(config.exam_date)
                    start_time = config.start_time.strftime('%H:%M') if config.start_time else None
                    end_time = config.end_time.strftime('%H:%M') if config.end_time else None

                    # Count students seated
                    student_count = session.query(SeatingPlan).filter_by(config_id=config.id).count()

                    results.append({
                        'id': config.id,
                        'exam_date': exam_date,
                        'start_time': start_time,
                        'end_time': end_time,
                        'room': room.room_name if room else None,
                        'room_capacity': room.capacity if room else None,
                        'subjects': subjects,
                        'classes': classes,
                        'student_count': student_count,
                        'notes': config.notes,
                    })

                return results
        except Exception as e:
            raise Exception(f"Failed to get invigilator schedule: {str(e)}")
