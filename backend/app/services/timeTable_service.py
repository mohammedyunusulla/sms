from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, func
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from app.utils.db_manager import switch_to_school_db

logger = logging.getLogger(__name__)


_schema_checked = set()


def ensure_timetable_schema(session, skid):
    """Existing school databases still have the old (teacher, day, time) unique key: drop it once per process."""
    if skid in _schema_checked:
        return
    from sqlalchemy import text
    session.execute(text("ALTER TABLE timetable_entries DROP CONSTRAINT IF EXISTS unique_teacher_schedule_per_time_slot"))
    session.commit()
    _schema_checked.add(skid)


def _year_name(session, year_id):
    from app.models.tenant.AcademicYear import AcademicYear
    year = session.query(AcademicYear).filter_by(id=year_id).first() if year_id else None
    return year.year_name if year else None


def live_timetable_ids(session, on_date, section_id=None):
    """
    The timetables people should see on a date: published (not draft) and active, in the academic year of that
    date, and for each section the most recently published one (so publishing semester 2 replaces semester 1).
    """
    from app.models.tenant.TimeTable import Timetable
    from app.models.tenant.AcademicYear import AcademicYear
    year = session.query(AcademicYear).filter(
        AcademicYear.start_date <= on_date, AcademicYear.end_date >= on_date
    ).first() or session.query(AcademicYear).filter_by(is_current=True).first()
    if not year:
        return set()
    query = session.query(Timetable.id, Timetable.section_id).filter(
        Timetable.academic_year_id == year.id,
        Timetable.is_active.is_(True),
        Timetable.is_draft.isnot(True),
    )
    if section_id is not None:
        query = query.filter(Timetable.section_id == section_id)
    latest = {}
    for tt_id, sec_id in query.order_by(Timetable.updated_at.desc().nullslast(), Timetable.id.desc()).all():
        latest.setdefault(sec_id, tt_id)
    return set(latest.values())


class TimetableService:

    @staticmethod
    def generate_time_slots(config: Dict) -> List[Dict]:
        """Generate time slots based on configuration"""
        try:
            slots = []
            start_time = datetime.strptime(config['school_start_time'], '%H:%M').time()
            lunch_time = datetime.strptime(config['lunch_start_time'], '%H:%M').time()
            
            current_datetime = datetime.combine(datetime.today(), start_time)
            lunch_datetime = datetime.combine(datetime.today(), lunch_time)
            lunch_end_datetime = lunch_datetime + timedelta(minutes=config['lunch_duration'])
            
            period_count = 0
            
            for i in range(config['total_periods']):
                period_start = current_datetime
                period_end = current_datetime + timedelta(minutes=config['period_duration'])
                
                # Check if lunch break should be inserted
                if period_start.time() < lunch_time and period_end.time() > lunch_time and period_count > 0:
                    # Insert lunch break
                    slots.append({
                        'period': 'LUNCH',
                        'start_time': lunch_datetime.strftime('%H:%M'),
                        'end_time': lunch_end_datetime.strftime('%H:%M'),
                        'time_display': f"{lunch_datetime.strftime('%H:%M')} - {lunch_end_datetime.strftime('%H:%M')}",
                        'is_lunch': True,
                        'label': 'LUNCH BREAK'
                    })
                    current_datetime = lunch_end_datetime
                    
                    # Recalculate period after lunch
                    period_start = current_datetime
                    period_end = current_datetime + timedelta(minutes=config['period_duration'])
                
                period_count += 1
                slots.append({
                    'period': period_count,
                    'start_time': period_start.strftime('%H:%M'),
                    'end_time': period_end.strftime('%H:%M'),
                    'time_display': f"{period_start.strftime('%H:%M')} - {period_end.strftime('%H:%M')}",
                    'is_lunch': False,
                    'label': f'Period {period_count}'
                })
                
                current_datetime = period_end
            
            return slots
        except Exception as e:
            logger.error(f"Error generating time slots: {str(e)}")
            raise

    @staticmethod
    def check_teacher_conflicts(skid: str, teacher_id: int, day: str, start_time: str, end_time: str, 
                               academic_year_id: int, semester: str, 
                               exclude_timetable_id: Optional[int] = None) -> Dict:
        """
        Check if teacher has conflicts with existing timetable entries in school-specific DB
        """
        try:
            start_time_obj = datetime.strptime(start_time, '%H:%M').time()
            end_time_obj = datetime.strptime(end_time, '%H:%M').time()
            
            with switch_to_school_db(skid) as tenant_session:
                # Import models inside the function to avoid import issues
                from app.models.tenant.TimeTable import Timetable
                from app.models.tenant.TimeTableEntry import TimetableEntry
                from app.models.tenant.Class import Class
                from app.models.tenant.Sections import Section
                from app.models.tenant.Subject import Subject
                from app.models.tenant.Teacher import Teacher
                from app.models.tenant.SchoolUsers import SchoolUsers  # Add this import
                
                # Query for conflicting entries in the tenant database
                query = tenant_session.query(TimetableEntry).join(Timetable).filter(
                    TimetableEntry.teacher_id == teacher_id,
                    TimetableEntry.day_of_week == day,
                    Timetable.academic_year_id == academic_year_id,
                    Timetable.semester == semester,
                    Timetable.is_active == True,
                    TimetableEntry.is_active == True,
                    # Time overlap condition: (start1 < end2) AND (start2 < end1)
                    and_(
                        TimetableEntry.start_time < end_time_obj,
                        TimetableEntry.end_time > start_time_obj
                    )
                ).options(
                    joinedload(TimetableEntry.timetable).joinedload(Timetable.class_ref),
                    joinedload(TimetableEntry.timetable).joinedload(Timetable.section_obj),
                    joinedload(TimetableEntry.subject),
                    joinedload(TimetableEntry.teacher).joinedload(Teacher.user)  # Add nested joinedload for user
                )
                
                # Exclude current timetable if updating
                if exclude_timetable_id:
                    query = query.filter(TimetableEntry.timetable_id != exclude_timetable_id)
                
                conflicts = query.all()
                
                conflict_details = []
                for conflict in conflicts:
                    conflict_details.append({
                        'class_name': conflict.timetable.class_ref.class_name,
                        'section_name': conflict.timetable.section_obj.section_name,
                        'subject_name': conflict.subject.subject_name,
                        'subject_code': conflict.subject.subject_code,
                        'teacher_name': f"{conflict.teacher.user.first_name} {conflict.teacher.user.last_name}",  # Access through user relationship
                        'start_time': conflict.start_time.strftime('%H:%M'),
                        'end_time': conflict.end_time.strftime('%H:%M'),
                        'room_number': conflict.room_number,
                        'day': conflict.day_of_week,
                        'period_number': conflict.period_number
                    })
                
                return {
                    'has_conflict': len(conflicts) > 0,
                    'conflict_count': len(conflicts),
                    'conflicts': conflict_details
                }
                
        except Exception as e:
            logger.error(f"Error checking teacher conflicts: {str(e)}")
            raise


    @staticmethod
    def validate_timetable_conflicts(skid: str, data: Dict) -> Dict:
        """
        Enhanced validation with detailed conflict checking for specific school DB
        """
        try:
            # Basic validation
            required_fields = ['skid', 'class_id', 'section_id', 'academic_year_id', 'semester']
            for field in required_fields:
                if not data.get(field):
                    return {
                        'is_valid': False,
                        'validation_message': f"Missing required field: {field}",
                        'conflicts': [],
                        'conflict_details': {}
                    }
            
            entries = data.get('entries', {})
            if not entries:
                return {
                    'is_valid': False,
                    'validation_message': "No timetable entries provided",
                    'conflicts': [],
                    'conflict_details': {}
                }
            
            with switch_to_school_db(skid) as tenant_session:
                from app.models.tenant.TimeTable import Timetable
                
                # Check existing timetable
                existing_timetable = tenant_session.query(Timetable).filter(
                    Timetable.class_id == data['class_id'],
                    Timetable.section_id == data['section_id'],
                    Timetable.academic_year_id == data['academic_year_id'],
                    Timetable.semester == data['semester']
                ).first()
                
                exclude_timetable_id = existing_timetable.id if existing_timetable else None
                
                # Check for teacher conflicts and internal duplicates
                all_conflicts = []
                conflict_details = {}
                teacher_schedule_check = {}
                
                for entry_key, entry_data in entries.items():
                    day, time_slot = entry_key.split('-', 1)
                    teacher_id = entry_data.get('teacher_id')
                    
                    if not teacher_id:
                        return {
                            'is_valid': False,
                            'validation_message': f"Missing teacher for entry: {entry_key}",
                            'conflicts': [],
                            'conflict_details': {}
                        }
                    
                    # Parse time slot
                    if ' - ' in time_slot:
                        start_time, end_time = time_slot.split(' - ')
                    else:
                        continue
                    
                    # Check internal conflicts (within this timetable)
                    schedule_key = f"{teacher_id}-{day}-{time_slot}"
                    if schedule_key in teacher_schedule_check:
                        return {
                            'is_valid': False,
                            'validation_message': f"Teacher has multiple assignments on {day} at {time_slot}",
                            'conflicts': [],
                            'conflict_details': {}
                        }
                    teacher_schedule_check[schedule_key] = True
                    
                    # Check external conflicts (with other published timetables only)
                    teacher_conflicts = TimetableService.check_teacher_conflicts(
                        skid, teacher_id, day, start_time, end_time,
                        data['academic_year_id'], data['semester'], exclude_timetable_id
                    )
                    
                    if teacher_conflicts['has_conflict']:
                        all_conflicts.extend(teacher_conflicts['conflicts'])
                        conflict_details[entry_key] = {
                            'teacher_id': teacher_id,
                            'conflicts': teacher_conflicts['conflicts']
                        }
                
                if all_conflicts:
                    return {
                        'is_valid': False,
                        'validation_message': f"Found {len(all_conflicts)} teacher scheduling conflict(s)",
                        'conflicts': all_conflicts,
                        'conflict_details': conflict_details
                    }
                
                return {
                    'is_valid': True,
                    'validation_message': "No conflicts found",
                    'conflicts': [],
                    'conflict_details': {}
                }
                
        except Exception as e:
            logger.error(f"Error validating timetable conflicts: {str(e)}")
            raise

    @staticmethod
    def create_or_update_timetable(skid: str, data: Dict, is_draft: bool = False) -> Dict:
        """Create or update timetable with draft support"""
        try:
            # Validate data only if not saving as draft
            if not is_draft:
                validation_result = TimetableService.validate_timetable_conflicts(skid, data)
                if not validation_result['is_valid']:
                    return {
                        'success': False, 
                        'message': validation_result['validation_message'],
                        'conflicts': validation_result.get('conflicts', []),
                        'conflict_details': validation_result.get('conflict_details', {})
                    }
            
            with switch_to_school_db(skid) as tenant_session:
                from app.models.tenant.TimeTable import Timetable
                from app.models.tenant.TimeTableEntry import TimetableEntry
                ensure_timetable_schema(tenant_session, skid)

                # Check if timetable already exists
                existing_timetable = tenant_session.query(Timetable).filter(
                    Timetable.class_id == data['class_id'],
                    Timetable.section_id == data['section_id'],
                    Timetable.academic_year_id == data['academic_year_id'],
                    Timetable.semester == data['semester']
                ).first()
                
                if existing_timetable:
                    # Update existing timetable (and bring back one that was deleted: delete only marks it
                    # inactive, and re-saving used to leave it invisible)
                    timetable = existing_timetable
                    timetable.is_active = True
                    # Delete existing entries
                    tenant_session.query(TimetableEntry).filter(
                        TimetableEntry.timetable_id == timetable.id
                    ).delete()
                    action_text = "updated"
                else:
                    # Create new timetable
                    timetable = Timetable(
                        class_id=data['class_id'],
                        section_id=data['section_id'],
                        academic_year_id=data['academic_year_id'],
                        semester=data['semester']
                    )
                    tenant_session.add(timetable)
                    tenant_session.flush()  # Get the ID
                    action_text = "created"
                
                # Update configuration
                timetable.period_duration = data.get('period_duration', 45)
                timetable.school_start_time = datetime.strptime(data.get('school_start_time', '09:00'), '%H:%M').time()
                timetable.lunch_start_time = datetime.strptime(data.get('lunch_start_time', '12:30'), '%H:%M').time()
                timetable.lunch_duration = data.get('lunch_duration', 30)
                timetable.total_periods = data.get('total_periods', 7)
                timetable.is_draft = is_draft
                timetable.updated_at = datetime.utcnow()
                
                # Generate time slots
                time_slots = TimetableService.generate_time_slots({
                    'school_start_time': data.get('school_start_time', '09:00'),
                    'lunch_start_time': data.get('lunch_start_time', '12:30'),
                    'lunch_duration': data.get('lunch_duration', 30),
                    'period_duration': data.get('period_duration', 45),
                    'total_periods': data.get('total_periods', 7)
                })
                
                # Create time slot mapping
                time_slot_map = {slot['time_display']: slot for slot in time_slots if not slot['is_lunch']}
                
                # Create timetable entries
                entries_created = 0
                for entry_key, entry_data in data['entries'].items():
                    day, time_display = entry_key.split('-', 1)
                    
                    if time_display in time_slot_map:
                        slot_info = time_slot_map[time_display]
                        
                        entry = TimetableEntry(
                            timetable_id=timetable.id,
                            day_of_week=day,
                            period_number=slot_info['period'],
                            start_time=datetime.strptime(slot_info['start_time'], '%H:%M').time(),
                            end_time=datetime.strptime(slot_info['end_time'], '%H:%M').time(),
                            subject_id=entry_data.get('subject_id') or entry_data['subject']['id'],
                            teacher_id=entry_data.get('teacher_id') or entry_data['teacher']['id'],
                            room_number=entry_data.get('room', ''),
                            class_type=entry_data.get('type', 'Regular')
                        )
                        tenant_session.add(entry)
                        entries_created += 1
                
                tenant_session.commit()
                
                status_text = "draft" if is_draft else "finalized"
                
                return {
                    'success': True,
                    'message': f'Timetable {action_text} successfully as {status_text}',
                    'timetable_id': timetable.id,
                    'entries_created': entries_created,
                    'is_draft': is_draft
                }
                
        except IntegrityError as e:
            logger.error(f"Integrity error creating timetable: {str(e)}")
            return {'success': False, 'message': 'Timetable validation failed. Check for conflicts.'}
        except Exception as e:
            logger.error(f"Error creating timetable: {str(e)}")
            return {'success': False, 'message': f'Error creating timetable: {str(e)}'}

    @staticmethod
    def get_timetable_by_id(skid: str, timetable_id: int) -> Optional[Dict]:
        """Get timetable by ID with all entries"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                from app.models.tenant.TimeTable import Timetable
                from app.models.tenant.TimeTableEntry import TimetableEntry
                from app.models.tenant.Class import Class
                from app.models.tenant.Sections import Section
                from app.models.tenant.Subject import Subject
                from app.models.tenant.Teacher import Teacher
                from app.models.tenant.SchoolUsers import SchoolUsers
                
                timetable = tenant_session.query(Timetable).filter(
                    Timetable.id == timetable_id,
                    Timetable.is_active == True
                ).options(
                    joinedload(Timetable.entries).joinedload(TimetableEntry.subject),
                    joinedload(Timetable.entries).joinedload(TimetableEntry.teacher).joinedload(Teacher.user),
                    joinedload(Timetable.class_ref),
                    joinedload(Timetable.section_obj)
                ).first()
                
                if not timetable:
                    return None
                
                # Generate time slots
                time_slots = TimetableService.generate_time_slots({
                    'school_start_time': timetable.school_start_time.strftime('%H:%M'),
                    'lunch_start_time': timetable.lunch_start_time.strftime('%H:%M'),
                    'lunch_duration': timetable.lunch_duration,
                    'period_duration': timetable.period_duration,
                    'total_periods': timetable.total_periods
                })
                
                # Map entries
                entries_map = {}
                for entry in timetable.entries:
                    if entry.is_active:
                        key = f"{entry.day_of_week}-{entry.start_time.strftime('%H:%M')} - {entry.end_time.strftime('%H:%M')}"
                        entries_map[key] = {
                            'id': entry.id,
                            'subject': {
                                'id': entry.subject.id,
                                'subject_name': entry.subject.subject_name,
                                'subject_code': entry.subject.subject_code
                            },
                            'teacher': {
                                'id': entry.teacher.user_id,
                                'first_name': entry.teacher.user.first_name,
                                'last_name': entry.teacher.user.last_name
                            },
                            'room': entry.room_number,
                            'type': entry.class_type,
                            'period_number': entry.period_number
                        }
                
                return {
                    'id': timetable.id,
                    'class_id': timetable.class_id,  # ADD THIS
                    'section_id': timetable.section_id,  # ADD THIS
                    'class_name': timetable.class_ref.class_name,
                    'section_name': timetable.section_obj.section_name,
                    'academic_year_id': timetable.academic_year_id,
                    'academic_year': _year_name(tenant_session, timetable.academic_year_id),
                    'semester': timetable.semester,
                    'is_draft': timetable.is_draft,
                    'configuration': {
                        'period_duration': timetable.period_duration,
                        'school_start_time': timetable.school_start_time.strftime('%H:%M'),
                        'lunch_start_time': timetable.lunch_start_time.strftime('%H:%M'),
                        'lunch_duration': timetable.lunch_duration,
                        'total_periods': timetable.total_periods
                    },
                    'time_slots': time_slots,
                    'entries': entries_map,
                    'created_at': timetable.created_at.isoformat(),
                    'updated_at': timetable.updated_at.isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error fetching timetable by ID: {str(e)}")
            raise

    @staticmethod
    def get_all_timetables_by_school(skid: str, academic_year_id: int = None, 
                                   semester: str = None) -> List[Dict]:
        """Get all timetables for a school with draft filter"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                from app.models.tenant.TimeTable import Timetable
                from app.models.tenant.Class import Class
                from app.models.tenant.Sections import Section
                
                query = tenant_session.query(Timetable).filter(
                    Timetable.is_active == True
                )
                
                if academic_year_id:
                    query = query.filter(Timetable.academic_year_id == academic_year_id)
                if semester:
                    query = query.filter(Timetable.semester == semester)
                
                query = query.options(
                    joinedload(Timetable.class_ref),
                    joinedload(Timetable.section_obj),
                    joinedload(Timetable.entries)
                )

                timetables = query.all()

                days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                result = []
                for tt in timetables:
                    # the list showed "0 Time Slots" for every timetable: it never returned its periods
                    slots = sorted(
                        (e for e in tt.entries if e.is_active),
                        key=lambda e: (days.index(e.day_of_week) if e.day_of_week in days else 9, e.period_number),
                    )
                    result.append({
                        'id': tt.id,
                        'class_name': tt.class_ref.class_name,
                        'section_name': tt.section_obj.section_name,
                        'academic_year_id': tt.academic_year_id,
                        'semester': tt.semester,
                        'is_draft': getattr(tt, 'is_draft', False),
                        'timeSlots': [{
                            'id': e.id,
                            'dayOfWeek': days.index(e.day_of_week) if e.day_of_week in days else -1,
                            'startTime': e.start_time.strftime('%H:%M'),
                            'endTime': e.end_time.strftime('%H:%M'),
                        } for e in slots],
                        'created_at': tt.created_at.isoformat(),
                        'updated_at': tt.updated_at.isoformat()
                    })
                
                return result
                
        except Exception as e:
            logger.error(f"Error fetching timetables: {str(e)}")
            raise

    @staticmethod
    def get_draft_timetables(skid: str, academic_year_id: str = None, semester: str = None) -> List[Dict]:
        """Get only draft timetables for a school"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                from app.models.tenant.TimeTable import Timetable
                from app.models.tenant.Class import Class
                from app.models.tenant.Section import Section
                
                query = tenant_session.query(Timetable).filter(
                    Timetable.is_active == True,
                    Timetable.is_draft == True
                )
                
                if academic_year_id:
                    query = query.filter(Timetable.academic_year_id == academic_year_id)
                if semester:
                    query = query.filter(Timetable.semester == semester)
                
                query = query.options(
                    joinedload(Timetable.class_ref),
                    joinedload(Timetable.section_obj)
                )
                
                drafts = query.all()
                
                result = []
                for draft in drafts:
                    # Count entries
                    entry_count = tenant_session.query(TimetableEntry).filter(
                        TimetableEntry.timetable_id == draft.id,
                        TimetableEntry.is_active == True
                    ).count()
                    
                    result.append({
                        'id': draft.id,
                        'class_name': draft.class_ref.class_name,
                        'section_name': draft.section_obj.section_name,
                        'academic_year_id': draft.academic_year_id,
                        'semester': draft.semester,
                        'is_draft': True,
                        'entry_count': entry_count,
                        'created_at': draft.created_at.isoformat(),
                        'updated_at': draft.updated_at.isoformat()
                    })
                
                return result
                
        except Exception as e:
            logger.error(f"Error fetching draft timetables: {str(e)}")
            raise

    @staticmethod
    def publish_draft_timetable(skid: str, timetable_id: int) -> Dict:
        """Convert a draft timetable to published after validation"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                from app.models.tenant.TimeTable import Timetable
                from app.models.tenant.TimeTableEntry import TimetableEntry
                
                # Get the draft timetable
                timetable = tenant_session.query(Timetable).filter(
                    Timetable.id == timetable_id,
                    Timetable.is_draft == True,
                    Timetable.is_active == True
                ).first()
                
                if not timetable:
                    return {
                        'success': False,
                        'message': 'Draft timetable not found'
                    }
                
                # Get all entries for validation
                entries = tenant_session.query(TimetableEntry).filter(
                    TimetableEntry.timetable_id == timetable_id,
                    TimetableEntry.is_active == True
                ).all()
                
                # Transform entries for validation
                validation_data = {
                    'skid': skid,
                    'class_id': timetable.class_id,
                    'section_id': timetable.section_id,
                    'academic_year_id': timetable.academic_year_id,
                    'semester': timetable.semester,
                    'entries': {}
                }
                
                for entry in entries:
                    key = f"{entry.day_of_week}-{entry.start_time.strftime('%H:%M')} - {entry.end_time.strftime('%H:%M')}"
                    validation_data['entries'][key] = {
                        'subject_id': entry.subject_id,
                        'teacher_id': entry.teacher_id,
                        'room': entry.room_number,
                        'type': entry.class_type
                    }
                
                # Validate before publishing
                validation_result = TimetableService.validate_timetable_conflicts(skid, validation_data)
                
                if not validation_result['is_valid']:
                    return {
                        'success': False,
                        'message': f"Cannot publish draft: {validation_result['validation_message']}",
                        'conflicts': validation_result.get('conflicts', [])
                    }
                
                # Update draft to published
                timetable.is_draft = False
                timetable.updated_at = datetime.utcnow()
                
                tenant_session.commit()
                
                return {
                    'success': True,
                    'message': 'Draft timetable published successfully'
                }
                
        except Exception as e:
            logger.error(f"Error publishing draft timetable: {str(e)}")
            return {'success': False, 'message': f'Error publishing draft: {str(e)}'}

    @staticmethod
    def delete_timetable(timetable_id: int, skid: str) -> Dict:
        """Delete a timetable and all its entries"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                from app.models.tenant.TimeTable import Timetable
                from app.models.tenant.TimeTableEntry import TimetableEntry
                
                timetable = tenant_session.query(Timetable).filter(
                    Timetable.id == timetable_id,
                    Timetable.is_active == True
                ).first()
                
                if not timetable:
                    return {
                        'success': False,
                        'message': 'Timetable not found'
                    }
                
                # Soft delete entries
                tenant_session.query(TimetableEntry).filter(
                    TimetableEntry.timetable_id == timetable_id
                ).update({'is_active': False})
                
                # Soft delete timetable
                timetable.is_active = False
                timetable.updated_at = datetime.utcnow()
                
                tenant_session.commit()
                
                status_text = "draft" if timetable.is_draft else "published"
                return {
                    'success': True,
                    'message': f'Timetable ({status_text}) deleted successfully'
                }
                
        except Exception as e:
            logger.error(f"Error deleting timetable: {str(e)}")
            return {'success': False, 'message': f'Error deleting timetable: {str(e)}'}

    @staticmethod
    def get_teacher_schedule(teacher_id: int, academic_year_id: str, semester: str, skid: str = None) -> Dict:
        """Get teacher's complete schedule across all classes"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                from app.models.tenant.TimeTable import Timetable
                from app.models.tenant.TimeTableEntry import TimetableEntry
                from app.models.tenant.Class import Class
                from app.models.tenant.Section import Section
                from app.models.tenant.Subject import Subject
                
                # Get all entries for the teacher (only from published timetables)
                entries = tenant_session.query(TimetableEntry).join(Timetable).filter(
                    TimetableEntry.teacher_id == teacher_id,
                    Timetable.academic_year_id == academic_year_id,
                    Timetable.semester == semester,
                    Timetable.is_active == True,
                    Timetable.is_draft == False,  # Only published schedules
                    TimetableEntry.is_active == True
                ).options(
                    joinedload(TimetableEntry.subject),
                    joinedload(TimetableEntry.timetable).joinedload(Timetable.class_ref),
                    joinedload(TimetableEntry.timetable).joinedload(Timetable.section_obj)
                ).all()
                
                # Organize by day
                schedule = {}
                for entry in entries:
                    day = entry.day_of_week
                    if day not in schedule:
                        schedule[day] = []
                    
                    schedule[day].append({
                        'period_number': entry.period_number,
                        'start_time': entry.start_time.strftime('%H:%M'),
                        'end_time': entry.end_time.strftime('%H:%M'),
                        'subject_name': entry.subject.subject_name,
                        'subject_code': entry.subject.subject_code,
                        'class_name': entry.timetable.class_ref.class_name,
                        'section_name': entry.timetable.section_obj.section_name,
                        'room_number': entry.room_number,
                        'class_type': entry.class_type
                    })
                
                # Sort each day's entries by start time
                for day in schedule:
                    schedule[day].sort(key=lambda x: x['start_time'])
                
                return {
                    'teacher_id': teacher_id,
                    'academic_year_id': academic_year_id,
                    'semester': semester,
                    'schedule': schedule,
                    'total_periods': sum(len(day_schedule) for day_schedule in schedule.values())
                }
                
        except Exception as e:
            logger.error(f"Error fetching teacher schedule: {str(e)}")
            raise

    @staticmethod
    def get_student_timetable_by_day(skid, student_id, date):
        """
        Get student's class timetable for a specific day.

        Finds the student's enrolled section, then returns all periods
        for that section on the given day, including teacher names.

        Args:
            skid: School ID
            student_id: Student's school_user_id
            date: Date string in YYYY-MM-DD format

        Returns:
            List of periods with subject, time, and teacher details
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                from app.models.tenant.Student import Student
                from app.models.tenant.SchoolUsers import SchoolUsers
                from app.models.tenant.Teacher import Teacher
                from app.models.tenant.Subject import Subject
                from app.models.tenant.TimeTable import Timetable
                from app.models.tenant.TimeTableEntry import TimetableEntry

                # Get student's section
                student = tenant_session.query(Student).filter(
                    Student.user_id == student_id
                ).first()

                if not student:
                    raise ValueError("Student not found")

                if not student.section_id:
                    raise ValueError("Student is not enrolled in any section")

                # Parse date to get day of week
                date_obj = datetime.strptime(date, '%Y-%m-%d').date()
                day_name = date_obj.strftime('%A')

                # Only the section's live timetable: published, active, that date's year, latest published
                # (drafts, deleted timetables and other years/semesters used to be mixed in)
                live_ids = live_timetable_ids(tenant_session, date_obj, student.section_id)
                if not live_ids:
                    return []

                # Query timetable entries for the student's section on the given day
                entries = tenant_session.query(
                    TimetableEntry.id,
                    TimetableEntry.period_number,
                    TimetableEntry.start_time,
                    TimetableEntry.end_time,
                    TimetableEntry.room_number,
                    TimetableEntry.subject_id,
                    TimetableEntry.teacher_id,
                    Subject.subject_name.label('subject_name'),
                    SchoolUsers.first_name.label('teacher_first_name'),
                    SchoolUsers.last_name.label('teacher_last_name'),
                ).join(
                    Timetable, TimetableEntry.timetable_id == Timetable.id
                ).join(
                    Subject, TimetableEntry.subject_id == Subject.id
                ).join(
                    Teacher, TimetableEntry.teacher_id == Teacher.user_id
                ).join(
                    SchoolUsers, Teacher.user_id == SchoolUsers.id
                ).filter(
                    and_(
                        Timetable.id.in_(live_ids),
                        TimetableEntry.day_of_week == day_name,
                        TimetableEntry.is_active == True
                    )
                ).order_by(
                    TimetableEntry.period_number
                ).all()

                periods = []
                for entry in entries:
                    periods.append({
                        'id': entry.id,
                        'period_number': entry.period_number,
                        'start_time': entry.start_time.strftime('%H:%M'),
                        'end_time': entry.end_time.strftime('%H:%M'),
                        'subject_id': entry.subject_id,
                        'subject_name': entry.subject_name,
                        'teacher_id': entry.teacher_id,
                        'teacher_name': f"{entry.teacher_first_name} {entry.teacher_last_name}",
                        'room': entry.room_number,
                        'day': day_name
                    })

                return periods

        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to fetch student timetable: {str(e)}")

    @staticmethod
    def duplicate_timetable(skid: str, source_timetable_id: int, target_data: Dict) -> Dict:
        """Duplicate an existing timetable to a new class/section/semester"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                from app.models.tenant.TimeTable import Timetable
                from app.models.tenant.TimeTableEntry import TimetableEntry
                ensure_timetable_schema(tenant_session, skid)
                
                # Get source timetable
                source_timetable = tenant_session.query(Timetable).filter(
                    Timetable.id == source_timetable_id,
                    Timetable.is_active == True
                ).options(joinedload(Timetable.entries)).first()
                
                if not source_timetable:
                    return {
                        'success': False,
                        'message': 'Source timetable not found'
                    }
                
                # Check if target already exists
                existing = tenant_session.query(Timetable).filter(
                    Timetable.class_id == target_data['class_id'],
                    Timetable.section_id == target_data['section_id'],
                    Timetable.academic_year_id == target_data['academic_year_id'],
                    Timetable.semester == target_data['semester'],
                    Timetable.is_active == True
                ).first()
                
                if existing:
                    return {
                        'success': False,
                        'message': 'Timetable already exists for target class/section/semester'
                    }
                
                # Create new timetable
                new_timetable = Timetable(
                    class_id=target_data['class_id'],
                    section_id=target_data['section_id'],
                    academic_year_id=target_data['academic_year_id'],
                    semester=target_data['semester'],
                    period_duration=source_timetable.period_duration,
                    school_start_time=source_timetable.school_start_time,
                    lunch_start_time=source_timetable.lunch_start_time,
                    lunch_duration=source_timetable.lunch_duration,
                    total_periods=source_timetable.total_periods,
                    is_draft=True  # Always create as draft when duplicating
                )
                
                tenant_session.add(new_timetable)
                tenant_session.flush()
                
                # Copy entries
                entries_created = 0
                for source_entry in source_timetable.entries:
                    if source_entry.is_active:
                        new_entry = TimetableEntry(
                            timetable_id=new_timetable.id,
                            day_of_week=source_entry.day_of_week,
                            period_number=source_entry.period_number,
                            start_time=source_entry.start_time,
                            end_time=source_entry.end_time,
                            subject_id=source_entry.subject_id,
                            teacher_id=source_entry.teacher_id,
                            room_number=source_entry.room_number,
                            class_type=source_entry.class_type
                        )
                        tenant_session.add(new_entry)
                        entries_created += 1
                
                tenant_session.commit()
                
                return {
                    'success': True,
                    'message': f'Timetable duplicated successfully as draft with {entries_created} entries',
                    'timetable_id': new_timetable.id,
                    'entries_created': entries_created,
                    'is_draft': True
                }
                
        except Exception as e:
            logger.error(f"Error duplicating timetable: {str(e)}")
            return {'success': False, 'message': f'Error duplicating timetable: {str(e)}'}