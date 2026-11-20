# ============================================================
# app/services/seating_service.py
from app.utils.db_manager import switch_to_school_db
from app.models.tenant import (
    ExamSeatingConfig, SeatingPlan, Room, Student, StudentEnrollment,
    SchoolUsers, ExamType, AcademicYear, Class, Section, Teacher
)


class SeatingService:

    @staticmethod
    def create_config(data, skid):
        """Create a seating configuration."""
        try:
            with switch_to_school_db(skid) as session:
                room = session.query(Room).filter_by(id=data['room_id']).first()
                if not room:
                    raise ValueError("Room not found")
                if not room.seating_layout or len(room.seating_layout) == 0:
                    raise ValueError("Room does not have seating layout configured")

                # Validate no conflicts before saving
                conflicts = SeatingService._check_conflicts(session, data, exclude_config_id=None)
                if conflicts:
                    raise ValueError('; '.join(conflicts))

                config = ExamSeatingConfig(
                    academic_year_id=data['academic_year_id'],
                    exam_type_id=data['exam_type_id'],
                    room_id=data['room_id'],
                    class_assignments=data['class_assignments'],
                    exam_date=data['exam_date'],
                    start_time=data['start_time'],
                    end_time=data['end_time'],
                    invigilator_id=data.get('invigilator_id'),
                    notes=data.get('notes'),
                )
                session.add(config)
                session.flush()

                result = config.to_dict()
                result['room'] = room.to_dict()
                result['exam_type_name'] = SeatingService._get_exam_type_name(session, config.exam_type_id)
                result['class_assignment_details'] = SeatingService._enrich_class_assignments(
                    session, data['class_assignments']
                )
                result['invigilator_name'] = SeatingService._get_invigilator_name(session, config.invigilator_id)
                result['student_count'] = 0
                session.commit()
                return result
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to create seating config: {str(e)}")

    @staticmethod
    def update_config(config_id, data, skid):
        """
        Update a seating configuration.
        If already generated: only class_assignments, invigilator_id, notes can change.
        Core fields (room, date, time) are locked after generation.
        """
        try:
            with switch_to_school_db(skid) as session:
                config = session.query(ExamSeatingConfig).filter_by(id=config_id).first()
                if not config:
                    raise ValueError("Seating config not found")

                if config.is_generated:
                    # Only allow safe updates after generation
                    locked = [f for f in ['room_id', 'exam_type_id', 'exam_date', 'start_time', 'end_time'] if f in data]
                    if locked:
                        raise ValueError(
                            f"Cannot change {', '.join(locked)} after seating has been generated. "
                            "Clear the plan first to make structural changes."
                        )
                    allowed = ['class_assignments', 'invigilator_id', 'notes']
                    for field in allowed:
                        if field in data:
                            setattr(config, field, data[field])
                else:
                    # Build effective data for conflict check
                    effective = {
                        'academic_year_id': data.get('academic_year_id', config.academic_year_id),
                        'exam_type_id': data.get('exam_type_id', config.exam_type_id),
                        'room_id': data.get('room_id', config.room_id),
                        'exam_date': data.get('exam_date', str(config.exam_date)),
                        'start_time': data.get('start_time', str(config.start_time)[:5]),
                        'class_assignments': data.get('class_assignments', config.class_assignments),
                    }
                    conflicts = SeatingService._check_conflicts(session, effective, exclude_config_id=config_id)
                    if conflicts:
                        raise ValueError('; '.join(conflicts))

                    for field in ['room_id', 'class_assignments', 'exam_date', 'start_time', 'end_time',
                                  'invigilator_id', 'notes', 'exam_type_id']:
                        if field in data:
                            setattr(config, field, data[field])

                session.commit()
                session.refresh(config)

                result = config.to_dict()
                room = session.query(Room).filter_by(id=config.room_id).first()
                result['room'] = room.to_dict() if room else None
                result['exam_type_name'] = SeatingService._get_exam_type_name(session, config.exam_type_id)
                result['class_assignment_details'] = SeatingService._enrich_class_assignments(
                    session, config.class_assignments
                )
                result['invigilator_name'] = SeatingService._get_invigilator_name(session, config.invigilator_id)
                result['student_count'] = session.query(SeatingPlan).filter_by(config_id=config.id).count()
                return result
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to update seating config: {str(e)}")

    @staticmethod
    def delete_config(config_id, skid):
        """Delete a seating config and its generated plans."""
        try:
            with switch_to_school_db(skid) as session:
                config = session.query(ExamSeatingConfig).filter_by(id=config_id).first()
                if not config:
                    raise ValueError("Seating config not found")
                session.delete(config)
                session.commit()
                return True
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to delete seating config: {str(e)}")

    @staticmethod
    def get_configs(skid, filters=None):
        """Get all seating configs with optional filters."""
        try:
            with switch_to_school_db(skid) as session:
                query = session.query(ExamSeatingConfig)
                if filters:
                    if filters.get('academic_year_id'):
                        query = query.filter(ExamSeatingConfig.academic_year_id == filters['academic_year_id'])
                    if filters.get('exam_type_id'):
                        query = query.filter(ExamSeatingConfig.exam_type_id == filters['exam_type_id'])
                    if filters.get('exam_date'):
                        query = query.filter(ExamSeatingConfig.exam_date == filters['exam_date'])

                configs = query.order_by(ExamSeatingConfig.exam_date, ExamSeatingConfig.start_time).all()
                results = []
                for config in configs:
                    item = config.to_dict()
                    room = session.query(Room).filter_by(id=config.room_id).first()
                    item['room'] = room.to_dict() if room else None
                    item['exam_type_name'] = SeatingService._get_exam_type_name(session, config.exam_type_id)
                    item['class_assignment_details'] = SeatingService._enrich_class_assignments(
                        session, config.class_assignments
                    )
                    item['student_count'] = session.query(SeatingPlan).filter_by(config_id=config.id).count()
                    item['invigilator_name'] = SeatingService._get_invigilator_name(session, config.invigilator_id)
                    results.append(item)
                return results
        except Exception as e:
            raise Exception(f"Failed to retrieve seating configs: {str(e)}")

    @staticmethod
    def get_config_by_id(config_id, skid):
        """Get a single seating config with its generated plan."""
        try:
            with switch_to_school_db(skid) as session:
                config = session.query(ExamSeatingConfig).filter_by(id=config_id).first()
                if not config:
                    raise ValueError("Seating config not found")

                result = config.to_dict()
                room = session.query(Room).filter_by(id=config.room_id).first()
                result['room'] = room.to_dict() if room else None
                result['exam_type_name'] = SeatingService._get_exam_type_name(session, config.exam_type_id)
                result['class_assignment_details'] = SeatingService._enrich_class_assignments(
                    session, config.class_assignments
                )
                result['invigilator_name'] = SeatingService._get_invigilator_name(session, config.invigilator_id)

                plans = session.query(SeatingPlan).filter_by(config_id=config.id)\
                    .order_by(SeatingPlan.seat_row, SeatingPlan.seat_column).all()

                seating_grid = []
                for plan in plans:
                    student = session.query(Student).filter_by(user_id=plan.student_id).first()
                    user = session.query(SchoolUsers).filter_by(id=plan.student_id).first()
                    enrollment = session.query(StudentEnrollment).filter_by(
                        student_id=plan.student_id,
                        academic_year_id=config.academic_year_id,
                        status='active'
                    ).first()
                    seating_grid.append({
                        **plan.to_dict(),
                        'student_name': user.full_name if user else 'Unknown',
                        'roll_no': student.roll_no if student else None,
                        'class_id': enrollment.class_id if enrollment else None,
                        'section_id': enrollment.section_id if enrollment else None,
                        'class_name': SeatingService._get_class_name(session, enrollment.class_id) if enrollment else None,
                        'section_name': SeatingService._get_section_name(session, enrollment.section_id) if enrollment else None,
                    })

                result['seating_grid'] = seating_grid
                result['student_count'] = len(seating_grid)
                return result
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to retrieve seating config: {str(e)}")

    @staticmethod
    def generate_seating(config_id, skid):
        """
        Generate seating using per-class column assignments.
        - Column-aware: each class fills only its assigned columns.
        - Incremental: skips students already seated in another room at the same sitting (same date, overlapping time).
        - Overflow: stops when assigned columns are full; remaining students stay unassigned.
        """
        try:
            with switch_to_school_db(skid) as session:
                config = session.query(ExamSeatingConfig).filter_by(id=config_id).first()
                if not config:
                    raise ValueError("Seating config not found")

                room = session.query(Room).filter_by(id=config.room_id).first()
                if not room or not room.seating_layout:
                    raise ValueError("Room seating layout is not configured")

                class_assignments = config.class_assignments or []
                if not class_assignments:
                    raise ValueError("No classes assigned to this room")

                # Students already seated in another room for the SAME sitting (same date, overlapping time),
                # whatever the exam type: nobody can sit in two rooms at once. It used to skip anyone seated
                # anywhere for this exam type and year, so a second paper on another day seated almost nobody.
                already_seated_elsewhere = set(
                    row[0] for row in
                    session.query(SeatingPlan.student_id)
                    .join(ExamSeatingConfig, SeatingPlan.config_id == ExamSeatingConfig.id)
                    .filter(
                        ExamSeatingConfig.academic_year_id == config.academic_year_id,
                        ExamSeatingConfig.exam_date == config.exam_date,
                        ExamSeatingConfig.start_time < config.end_time,
                        ExamSeatingConfig.end_time > config.start_time,
                        ExamSeatingConfig.id != config.id,
                    ).all()
                )

                # Seats already occupied in THIS config (incremental: keep existing)
                occupied_seats = {
                    (row[0], row[1])
                    for row in session.query(SeatingPlan.seat_row, SeatingPlan.seat_column)
                    .filter(SeatingPlan.config_id == config.id).all()
                }
                already_seated_here = set(
                    row[0] for row in
                    session.query(SeatingPlan.student_id)
                    .filter(SeatingPlan.config_id == config.id).all()
                )

                all_seated = already_seated_elsewhere | already_seated_here

                new_plans = []
                total_unassigned = 0

                for assignment in class_assignments:
                    class_id = assignment['class_id']
                    section_id = assignment.get('section_id')
                    target_columns = sorted(assignment.get('columns') or [])

                    if not target_columns:
                        continue

                    # Fetch unassigned students for this class/section
                    q = session.query(StudentEnrollment).filter(
                        StudentEnrollment.academic_year_id == config.academic_year_id,
                        StudentEnrollment.class_id == class_id,
                        StudentEnrollment.status == 'active',
                    )
                    if section_id:
                        q = q.filter(StudentEnrollment.section_id == section_id)
                    enrollments = q.order_by(StudentEnrollment.student_id).all()

                    unassigned = [e.student_id for e in enrollments if e.student_id not in all_seated]

                    student_ptr = 0
                    for abs_col in target_columns:
                        side_name, rel_col, side = SeatingService._abs_col_to_side(abs_col, room.seating_layout)
                        if side is None:
                            continue
                        for row in range(1, side['rows'] + 1):
                            if student_ptr >= len(unassigned):
                                break
                            if (row, abs_col) in occupied_seats:
                                continue
                            student_id = unassigned[student_ptr]
                            student_ptr += 1
                            all_seated.add(student_id)
                            occupied_seats.add((row, abs_col))

                            plan = SeatingPlan(
                                config_id=config.id,
                                student_id=student_id,
                                seat_row=row,
                                seat_column=abs_col,
                                seat_label=f"{side_name}-R{row}-C{rel_col}",
                            )
                            session.add(plan)
                            new_plans.append(plan)

                    total_unassigned += max(0, len(unassigned) - student_ptr)

                config.is_generated = True
                session.commit()

                msg = f"Seated {len(new_plans)} students"
                if total_unassigned > 0:
                    msg += f"; {total_unassigned} student(s) still need another room"
                return {
                    'config_id': config.id,
                    'newly_seated': len(new_plans),
                    'unassigned_remaining': total_unassigned,
                    'message': msg,
                }
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to generate seating: {str(e)}")

    @staticmethod
    def clear_seating(config_id, skid):
        """Clear the generated seating plan."""
        try:
            with switch_to_school_db(skid) as session:
                config = session.query(ExamSeatingConfig).filter_by(id=config_id).first()
                if not config:
                    raise ValueError("Seating config not found")
                deleted = session.query(SeatingPlan).filter_by(config_id=config.id).delete()
                config.is_generated = False
                session.commit()
                return {'deleted_count': deleted}
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to clear seating: {str(e)}")

    @staticmethod
    def validate_config(data, skid, config_id=None):
        """
        Validate a config payload for conflicts.
        Returns list of error strings — empty list means no conflicts.
        """
        try:
            with switch_to_school_db(skid) as session:
                return SeatingService._check_conflicts(session, data, exclude_config_id=config_id)
        except Exception as e:
            raise Exception(f"Validation failed: {str(e)}")

    @staticmethod
    def swap_seats(data, skid):
        """
        Move or swap students between seats (within or across rooms).
        data:
          seat_a: { config_id, student_id, seat_row, seat_col }
          seat_b: { config_id, student_id (optional), seat_row, seat_col, seat_label (optional) }
        """
        try:
            with switch_to_school_db(skid) as session:
                a = data['seat_a']
                b = data['seat_b']

                plan_a = session.query(SeatingPlan).filter_by(
                    config_id=a['config_id'], student_id=a['student_id']
                ).first()
                if not plan_a:
                    raise ValueError("Source student seat not found")

                if b.get('student_id'):
                    # Swap two students
                    plan_b = session.query(SeatingPlan).filter_by(
                        config_id=b['config_id'], student_id=b['student_id']
                    ).first()
                    if not plan_b:
                        raise ValueError("Target student seat not found")

                    # Cross-room: validate student not duplicated
                    if a['config_id'] != b['config_id']:
                        # Check student_a won't be double-seated in config_b's exam slot
                        # (already handled by unique constraints — swap is fine)
                        pass

                    # Swap in three steps: changing both seats in one flush briefly put two students on the same
                    # seat, which uq_seating_plan_seat rejected (500 UniqueViolation). Park A on a seat that can't
                    # exist, move B into A's seat, then put A into B's old seat.
                    a_row, a_col, a_label, a_config = plan_a.seat_row, plan_a.seat_column, plan_a.seat_label, plan_a.config_id
                    b_row, b_col, b_label, b_config = plan_b.seat_row, plan_b.seat_column, plan_b.seat_label, plan_b.config_id
                    plan_a.seat_row, plan_a.seat_column = -1, -1
                    session.flush()

                    plan_b.seat_row = a_row
                    plan_b.seat_column = a_col
                    plan_b.seat_label = a_label
                    plan_b.config_id = a_config
                    session.flush()

                    plan_a.seat_row = b_row
                    plan_a.seat_column = b_col
                    plan_a.seat_label = b_label
                    plan_a.config_id = b_config
                    session.flush()
                else:
                    # Move to empty seat
                    occupied = session.query(SeatingPlan).filter_by(
                        config_id=b['config_id'],
                        seat_row=b['seat_row'],
                        seat_column=b['seat_col'],
                    ).first()
                    if occupied:
                        raise ValueError("Target seat is already occupied")

                    # Cross-room: check student_a not already in config_b
                    if a['config_id'] != b['config_id']:
                        duplicate = session.query(SeatingPlan).filter_by(
                            config_id=b['config_id'], student_id=a['student_id']
                        ).first()
                        if duplicate:
                            raise ValueError("Student is already seated in the target room")

                    plan_a.config_id = b['config_id']
                    plan_a.seat_row = b['seat_row']
                    plan_a.seat_column = b['seat_col']
                    plan_a.seat_label = b.get('seat_label', f"R{b['seat_row']}-C{b['seat_col']}")

                    # Update source config's is_generated if moving out
                    if a['config_id'] != b['config_id']:
                        src_config = session.query(ExamSeatingConfig).filter_by(id=a['config_id']).first()
                        dst_config = session.query(ExamSeatingConfig).filter_by(id=b['config_id']).first()
                        if dst_config and not dst_config.is_generated:
                            dst_config.is_generated = True

                session.commit()
                return {'success': True}
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to swap seats: {str(e)}")

    # ── Internal helpers ──

    @staticmethod
    def _check_conflicts(session, data, exclude_config_id=None):
        """Run all conflict checks. Returns list of error strings."""
        errors = []

        # 1. Room double-booking
        q = session.query(ExamSeatingConfig).filter(
            ExamSeatingConfig.academic_year_id == data['academic_year_id'],
            ExamSeatingConfig.exam_type_id == data['exam_type_id'],
            ExamSeatingConfig.room_id == data['room_id'],
            ExamSeatingConfig.exam_date == data['exam_date'],
            ExamSeatingConfig.start_time == data['start_time'],
        )
        if exclude_config_id:
            q = q.filter(ExamSeatingConfig.id != exclude_config_id)
        if q.first():
            room = session.query(Room).filter_by(id=data['room_id']).first()
            errors.append(
                f"Room '{room.room_name if room else data['room_id']}' is already assigned for this exam slot"
            )

        # 2. Column overlap within same config
        assignments = data.get('class_assignments', [])
        col_owner: dict = {}
        for a in assignments:
            cls = session.query(Class).filter_by(id=a['class_id']).first()
            cls_name = cls.class_name if cls else str(a['class_id'])
            for col in (a.get('columns') or []):
                if col in col_owner:
                    errors.append(
                        f"Column {col} is assigned to both '{col_owner[col]}' and '{cls_name}'"
                    )
                else:
                    col_owner[col] = cls_name

        return errors

    @staticmethod
    def _abs_col_to_side(abs_col, seating_layout):
        """Convert absolute column to (side_name, relative_col, side_dict)."""
        offset = 0
        for side in seating_layout:
            side_cols = side['columns']
            if offset < abs_col <= offset + side_cols:
                return side.get('name', 'S'), abs_col - offset, side
            offset += side_cols
        return None, None, None

    @staticmethod
    def _enrich_class_assignments(session, class_assignments):
        if not class_assignments:
            return []
        details = []
        for a in class_assignments:
            cls = session.query(Class).filter_by(id=a['class_id']).first()
            sec = session.query(Section).filter_by(id=a.get('section_id')).first() if a.get('section_id') else None
            details.append({
                'class_id': a['class_id'],
                'section_id': a.get('section_id'),
                'columns': a.get('columns', []),
                'class_name': cls.class_name if cls else 'Unknown',
                'section_name': sec.section_name if sec else 'All Sections',
            })
        return details

    @staticmethod
    def _get_exam_type_name(session, exam_type_id):
        et = session.query(ExamType).filter_by(id=exam_type_id).first()
        return et.exam_name if et else None

    @staticmethod
    def _get_invigilator_name(session, invigilator_id):
        if not invigilator_id:
            return None
        teacher = session.query(Teacher).filter_by(user_id=invigilator_id).first()
        if teacher and teacher.user:
            return f"{teacher.user.first_name} {teacher.user.last_name}"
        return None

    @staticmethod
    def _get_class_name(session, class_id):
        if not class_id:
            return None
        cls = session.query(Class).filter_by(id=class_id).first()
        return cls.class_name if cls else None

    @staticmethod
    def _get_section_name(session, section_id):
        if not section_id:
            return None
        sec = session.query(Section).filter_by(id=section_id).first()
        return sec.section_name if sec else None
