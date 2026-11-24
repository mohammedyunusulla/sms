from app.models.main.User import User, UserRole
from app.models.main.School import School
from app.models.tenant.Attendance import Attendance
from app.models.tenant import SchoolUsers ,Student
from app import db
from sqlalchemy.exc import IntegrityError
from flask import jsonify
from app.utils.db_manager import switch_to_school_db
from app.utils.attendance_status import normalize_status, status_key
from app.utils.helpers import generate_student_id
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import and_, func
from datetime import datetime, date


def academic_year_for_date(tenant_session, day):
    """
    The academic year whose dates contain this day. Attendance is filed under it, so it can't be
    missing (update used to create rows with no year) or wrong (whatever year the header had selected).
    """
    from app.models.tenant.AcademicYear import AcademicYear
    year = tenant_session.query(AcademicYear).filter(
        AcademicYear.start_date <= day, AcademicYear.end_date >= day
    ).order_by(AcademicYear.start_date.desc()).first()
    if not year:
        raise ValueError(f"No academic year covers {day.strftime('%d %b %Y')}. Set up the academic year first.")
    return year.id


def attendance_day(value):
    """The attendance date: a real date, not in the future (Sundays are allowed for events / make-up days)."""
    from app.utils.validators import not_in_future
    return not_in_future(value, "Attendance date")


def check_in_section(tenant_session, student_ids, section_id, year_id):
    """Every student must be enrolled in this section in that academic year (any status, so past days stay editable)."""
    from app.models.tenant.StudentEnrollment import StudentEnrollment
    wanted = {int(i) for i in student_ids}
    if not wanted:
        return
    enrolled = {row[0] for row in tenant_session.query(StudentEnrollment.student_id).filter(
        StudentEnrollment.section_id == section_id,
        StudentEnrollment.academic_year_id == year_id,
        StudentEnrollment.student_id.in_(wanted),
    ).all()}
    missing = wanted - enrolled
    if missing:
        people = tenant_session.query(SchoolUsers).filter(SchoolUsers.id.in_(missing)).all()
        names = ", ".join(sorted(f"{u.first_name} {u.last_name or ''}".strip() for u in people)) or ", ".join(map(str, sorted(missing)))
        raise ValueError(f"Not in this section for that academic year: {names}")

class AttendanceService:

    @staticmethod
    def record_attendance_bulk(data, skid, actor_id=None):
        """
        Record attendance for multiple students in bulk
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                if not data.get('records'):
                    raise ValueError("No attendance records to save")
                
                # One section and one date per save; the date can't be in the future
                section_id = data['records'][0]['section_id']
                day = attendance_day(data['records'][0]['date'])
                if any(r.get('section_id') != section_id or attendance_day(r.get('date')) != day for r in data['records']):
                    raise ValueError("All records must be for the same section and date")
                check_in_section(tenant_session, [r['student_id'] for r in data['records']], section_id,
                                 academic_year_for_date(tenant_session, day))

                # First check if attendance already exists for this date and section
                existing_records = tenant_session.query(Attendance).filter(
                    and_(
                        Attendance.section_id == section_id,
                        Attendance.date == day
                    )
                ).all()
                
                if existing_records:
                    raise ValueError("Attendance already exists for this date and section. Use update instead.")
                
                # Prepare records for bulk insert (each filed under the academic year of its date)
                records = []
                years_by_date = {}
                for r in data['records']:
                    day = datetime.strptime(r['date'], '%Y-%m-%d').date()
                    if day not in years_by_date:
                        years_by_date[day] = academic_year_for_date(tenant_session, day)
                    record = {
                        'student_user_id': r['student_id'],
                        'class_id': r['class_id'],
                        'section_id': r['section_id'],
                        'academic_year_id': years_by_date[day],
                        'status': normalize_status(r['status']),
                        'remarks': r.get('remarks', ''),
                        'date': datetime.strptime(r['date'], '%Y-%m-%d').date(),
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow(),
                        'marked_by': actor_id,  # who marked it (school_users.id)
                    }
                    records.append(record)
                
                # Bulk insert
                tenant_session.bulk_insert_mappings(Attendance, records)
                tenant_session.commit()

                from app.services import push_events
                push_events.students_marked_absent(
                    skid, tenant_session,
                    [r['student_user_id'] for r in records if r['status'] == 'ABSENT'],
                    attendance_day(data['records'][0]['date']),
                )

                return {
                    'total_records': len(records),
                    'date': data['records'][0]['date'],
                    'section_id': data['records'][0]['section_id']
                }
                
        except ValueError:
            raise
        except Exception as e:
            if tenant_session:
                tenant_session.rollback()
            raise e

    @staticmethod
    def update_attendance_bulk(data, skid, actor_id=None):
        """
        Update attendance records in bulk
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                records = data['records']
                if not records:
                    raise ValueError("No attendance records to save")
                attendance_date = attendance_day(records[0]['date'])
                section_id = data['section_id']
                academic_year_id = academic_year_for_date(tenant_session, attendance_date)
                if any(attendance_day(r.get('date')) != attendance_date for r in records):
                    raise ValueError("All records must be for the same date")
                # Students without a row yet must be in the section; existing rows stay correctable
                # (e.g. a student who has since moved section)
                has_row = {row[0] for row in tenant_session.query(Attendance.student_user_id).filter(
                    Attendance.section_id == section_id, Attendance.date == attendance_date).all()}
                check_in_section(tenant_session, [r['student_id'] for r in records if int(r['student_id']) not in has_row],
                                 section_id, academic_year_id)

                updated_records = []
                status_before, status_after = {}, {}  # for absence alerts: only students who became absent

                for record_data in records:
                    student_id = record_data['student_id']
                    status = normalize_status(record_data['status'])
                    remarks = record_data.get('remarks', '')
                    
                    # Find existing attendance record
                    existing_record = tenant_session.query(Attendance).filter(
                        and_(
                            Attendance.student_user_id == student_id,
                            Attendance.date == attendance_date,
                            Attendance.section_id == section_id
                        )
                    ).first()
                    
                    status_before[int(student_id)] = existing_record.status if existing_record else None
                    status_after[int(student_id)] = status
                    if existing_record:
                        # Update existing record
                        existing_record.status = status
                        existing_record.remarks = remarks
                        existing_record.academic_year_id = academic_year_id  # also repairs rows saved without a year
                        existing_record.updated_at = datetime.utcnow()  # UTC, like created_at
                        existing_record.updated_by = actor_id  # who last changed it
                        updated_records.append(existing_record)
                    else:
                        # This shouldn't happen in edit mode, but handle it anyway
                        new_record = Attendance(
                            student_user_id=student_id,
                            class_id=record_data['class_id'],
                            section_id=section_id,
                            date=attendance_date,
                            academic_year_id=academic_year_id,
                            status=status,
                            remarks=remarks,
                            marked_by=actor_id,
                        )
                        tenant_session.add(new_record)
                        updated_records.append(new_record)
                
                tenant_session.commit()

                from app.services import push_events
                push_events.students_marked_absent(
                    skid, tenant_session, push_events.newly_absent(status_before, status_after), attendance_date)

                return {
                    'updated_count': len(updated_records),
                    'date': attendance_date.strftime('%Y-%m-%d')
                }
                
        except ValueError:
            raise  # validation errors (e.g. invalid status) -> 400 in the route
        except Exception as e:
            if tenant_session:
                tenant_session.rollback()
            raise Exception(f"Error updating bulk attendance: {str(e)}")


    @staticmethod
    def get_attendance(skid, section_id, attendance_date):
        """
        Get attendance records for a specific section and date
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                records = tenant_session.query(Attendance).filter(
                    and_(
                        Attendance.section_id == section_id,
                        Attendance.date == datetime.strptime(attendance_date, '%Y-%m-%d').date()
                    )
                ).all()
                
                result = []
                for record in records:
                    result.append({
                        'id': record.id,
                        'student_id': record.student_user_id,
                        'section_id': record.section_id,
                        'status': status_key(record.status),  # old rows were stored as 'Present' / 'present'
                        'remarks': record.remarks,
                        'date': record.date.strftime('%Y-%m-%d'),
                        'created_at': record.created_at.isoformat() if record.created_at else None,
                        'updated_at': record.updated_at.isoformat() if record.updated_at else None
                    })
                
                return result
                
        except Exception as e:
            raise e


    @staticmethod
    def delete_attendance(skid, section_id, attendance_date):
        """
        Delete attendance records for a specific section and date
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                records = tenant_session.query(Attendance).filter(
                    and_(
                        Attendance.section_id == section_id,
                        Attendance.date == datetime.strptime(attendance_date, '%Y-%m-%d').date()
                    )
                ).all()
                
                deleted_count = len(records)
                
                for record in records:
                    tenant_session.delete(record)
                
                tenant_session.commit()
                
                return {
                    'deleted_records': deleted_count,
                    'date': attendance_date,
                    'section_id': section_id
                }
                
        except Exception as e:
            if tenant_session:
                tenant_session.rollback()
            raise e

    
    @staticmethod
    def get_single_day_attendance(skid, academic_year_id, class_id, section_id, attendance_date):
        """
        Get attendance records for a specific date with statistics
        
        Args:
            skid: School ID
            class_id: Class ID
            section_id: Section ID
            attendance_date: Date object
            
        Returns:
            dict: {
                'records': list of attendance records,
                'statistics': attendance statistics
            }
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Fetch attendance records with student and user details
                records = tenant_session.query(Attendance).filter(
                    and_(
                        Attendance.academic_year_id == academic_year_id,
                        Attendance.class_id == class_id,
                        Attendance.section_id == section_id,
                        Attendance.date == attendance_date
                    )
                ).all()
                
                # Get total students in section (only active users)
                total_students = tenant_session.query(Student).join(
                    SchoolUsers, Student.user_id == SchoolUsers.id
                ).filter(
                    Student.section_id == section_id,
                    SchoolUsers.is_active == True
                ).count()
                
                # Calculate statistics
                present = len([r for r in records if status_key(r.status) == 'PRESENT'])
                absent = len([r for r in records if status_key(r.status) == 'ABSENT'])
                late = len([r for r in records if status_key(r.status) == 'LATE'])
                leave = len([r for r in records if status_key(r.status) == 'LEAVE'])
                not_marked = total_students - len(records)
                
                attendance_rate = round((present / total_students * 100), 2) if total_students > 0 else 0
                
                # Names of whoever marked / last changed these records
                actor_ids = {i for r in records for i in (r.marked_by, r.updated_by) if i}
                actor_names = {u.id: f"{u.first_name} {u.last_name or ''}".strip()
                               for u in tenant_session.query(SchoolUsers).filter(SchoolUsers.id.in_(actor_ids)).all()} if actor_ids else {}

                # Format attendance records with student details from SchoolUsers
                formatted_records = []
                for record in records:
                    # Join Student with SchoolUsers to get complete details
                    student = tenant_session.query(Student).filter(
                        Student.user_id == record.student_user_id
                    ).first()
                    
                    if student and student.user:
                        formatted_records.append({
                            'id': record.id,
                            'student': {
                                'id': student.user_id,
                                'name': f"{student.user.first_name} {student.user.last_name}",
                                'roll_no': student.roll_no,
                                'email': student.user.email,
                                'phone': student.user.phone
                            },
                            'status': status_key(record.status),  # old rows were stored as 'Present' / 'present'
                            'remarks': record.remarks,
                            'date': record.date.strftime('%Y-%m-%d'),
                            'created_at': record.created_at.strftime('%Y-%m-%d %H:%M:%S') if record.created_at else None,
                            'updated_at': record.updated_at.strftime('%Y-%m-%d %H:%M:%S') if record.updated_at else None,
                            'marked_by_name': actor_names.get(record.marked_by),
                            'updated_by_name': actor_names.get(record.updated_by),
                        })
                
                # Who marked the day and who last changed it (times are UTC; NULL actors = saved before this was recorded)
                marked = [r for r in records if r.marked_by]
                changed = [r for r in records if r.updated_by and r.updated_at]
                first = min(marked, key=lambda r: r.created_at or datetime.max) if marked else None
                last = max(changed, key=lambda r: r.updated_at) if changed else None
                audit = {
                    'recorded': bool(first or last),
                    'marked_by_name': actor_names.get(first.marked_by) if first else None,
                    'marked_at': first.created_at.strftime('%Y-%m-%dT%H:%M:%SZ') if first and first.created_at else None,
                    'updated_by_name': actor_names.get(last.updated_by) if last else None,
                    'updated_at': last.updated_at.strftime('%Y-%m-%dT%H:%M:%SZ') if last else None,
                }

                # Sort by roll number
                formatted_records.sort(key=lambda x: x['student']['roll_no'] or '')
                
                statistics = {
                    'total_students': total_students,
                    'present': present,
                    'absent': absent,
                    'late': late,
                    'leave': leave,
                    'not_marked': not_marked,
                    'attendance_rate': attendance_rate
                }
                
                return {
                    'records': formatted_records,
                    'statistics': statistics,
                    'audit': audit,
                }
                
        except Exception as e:
            raise Exception(f"Error fetching single day attendance: {str(e)}")
    
    
    @staticmethod
    def get_monthly_attendance(skid, academic_year_id, class_id, section_id, start_date, end_date):
        """
        Get monthly attendance with day-by-day details for all students
        
        Args:
            skid: School ID
            class_id: Class ID
            section_id: Section ID
            start_date: Date object (start of period)
            end_date: Date object (end of period)
            
        Returns:
            dict: {
                'students': list of students with daily attendance,
                'dates': list of all dates in range,
                'summary': overall statistics
            }
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Get all active students in the section with user details
                students = tenant_session.query(Student).join(
                    SchoolUsers, Student.user_id == SchoolUsers.id
                ).filter(
                    Student.section_id == section_id,
                    SchoolUsers.is_active == True
                ).order_by(Student.roll_no).all()
                
                # Generate all dates in the range (excluding weekends if needed)
                from datetime import timedelta
                date_list = []
                current_date = start_date
                while current_date <= end_date:
                    # You can add weekend filtering here if needed
                    # if current_date.weekday() < 5:  # Monday=0, Friday=4
                    date_list.append(current_date)
                    current_date += timedelta(days=1)
                
                monthly_data = []
                overall_stats = {
                    'total_students': len(students),
                    'total_days': len(date_list),
                    'total_present': 0,
                    'total_absent': 0,
                    'total_late': 0,
                    'total_leave': 0
                }
                
                for student in students:
                    # Get all attendance records for this student in date range
                    records = tenant_session.query(Attendance).filter(
                        and_(
                            Attendance.academic_year_id == academic_year_id,
                            Attendance.student_user_id == student.user_id,
                            Attendance.date >= start_date,
                            Attendance.date <= end_date
                        )
                    ).all()
                    
                    # Create a dictionary for quick lookup by date
                    attendance_by_date = {
                        record.date: {
                            'status': status_key(record.status),  # old rows were stored as 'Present' / 'present'
                            'remarks': record.remarks,
                            'id': record.id
                        }
                        for record in records
                    }
                    
                    # Build daily attendance array
                    daily_attendance = []
                    present_count = 0
                    absent_count = 0
                    late_count = 0
                    leave_count = 0
                    
                    for date in date_list:
                        if date in attendance_by_date:
                            att_data = attendance_by_date[date]
                            status = att_data['status']
                            
                            daily_attendance.append({
                                'date': date.strftime('%Y-%m-%d'),
                                'status': status,
                                'remarks': att_data['remarks'],
                                'attendance_id': att_data['id']
                            })
                            
                            # Count by status
                            if status_key(status) == 'PRESENT':
                                present_count += 1
                                overall_stats['total_present'] += 1
                            elif status_key(status) == 'ABSENT':
                                absent_count += 1
                                overall_stats['total_absent'] += 1
                            elif status_key(status) == 'LATE':
                                late_count += 1
                                overall_stats['total_late'] += 1
                            elif status_key(status) == 'LEAVE':
                                leave_count += 1
                                overall_stats['total_leave'] += 1
                        else:
                            # No attendance marked for this date
                            daily_attendance.append({
                                'date': date.strftime('%Y-%m-%d'),
                                'status': 'Not Marked',
                                'remarks': None,
                                'attendance_id': None
                            })
                    
                    # Calculate totals
                    total_days = len(records)  # Only days where attendance was marked
                    attended_count = present_count + late_count
                    attendance_percentage = round((attended_count / total_days * 100), 2) if total_days > 0 else 0
                    
                    monthly_data.append({
                        'student': {
                            'id': student.user_id,
                            'name': f"{student.user.first_name} {student.user.last_name}",
                            'roll_no': student.roll_no,
                            'email': student.user.email,
                            'phone': student.user.phone
                        },
                        'daily_attendance': daily_attendance,
                        'summary': {
                            'total_days': total_days,
                            'present_count': present_count,
                            'absent_count': absent_count,
                            'late_count': late_count,
                            'leave_count': leave_count,
                            'not_marked_count': len(date_list) - total_days,
                            'attendance_percentage': attendance_percentage,
                            'status': 'Excellent' if attendance_percentage >= 90 else 'Good' if attendance_percentage >= 75 else 'Warning' if attendance_percentage >= 60 else 'Critical'
                        }
                    })
                
                # Overall rate: (present + late) out of the attendance actually marked, the same rule as each
                # student's % (it used to divide by students x every calendar day, weekends and unmarked days included)
                total_marked = (overall_stats['total_present'] + overall_stats['total_absent']
                                + overall_stats['total_late'] + overall_stats['total_leave'])
                overall_attendance_rate = round(
                    ((overall_stats['total_present'] + overall_stats['total_late']) / total_marked * 100), 2
                ) if total_marked > 0 else 0
                overall_stats['total_marked'] = total_marked
                
                overall_stats['overall_attendance_rate'] = overall_attendance_rate
                
                return {
                    'students': monthly_data,
                    'dates': [d.strftime('%Y-%m-%d') for d in date_list],
                    'summary': overall_stats
                }
                
        except Exception as e:
            raise Exception(f"Error fetching monthly attendance: {str(e)}")

    
    @staticmethod
    def get_date_range_attendance(skid, class_id, section_id, start_date, end_date):
        """
        Get attendance records for a date range (for detailed view)
        
        Args:
            skid: School ID
            class_id: Class ID
            section_id: Section ID
            start_date: Date object
            end_date: Date object
            
        Returns:
            list: Attendance records grouped by date
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                records = tenant_session.query(Attendance).filter(
                    and_(
                        Attendance.class_id == class_id,
                        Attendance.section_id == section_id,
                        Attendance.date >= start_date,
                        Attendance.date <= end_date
                    )
                ).order_by(Attendance.date.desc()).all()
                
                # Group by date
                date_wise_records = {}
                for record in records:
                    date_key = record.date.strftime('%Y-%m-%d')
                    
                    if date_key not in date_wise_records:
                        date_wise_records[date_key] = []
                    
                    # Get student with user details
                    student = tenant_session.query(Student).filter(
                        Student.user_id == record.student_user_id
                    ).first()
                    
                    if student and student.user:
                        date_wise_records[date_key].append({
                            'id': record.id,
                            'student': {
                                'id': student.user_id,
                                'name': f"{student.user.first_name} {student.user.last_name}",
                                'roll_no': student.roll_no
                            },
                            'status': status_key(record.status),  # old rows were stored as 'Present' / 'present'
                            'remarks': record.remarks
                        })
                
                # Convert to list format with statistics per date
                result = []
                for date_key, date_records in sorted(date_wise_records.items(), reverse=True):
                    present_count = len([r for r in date_records if status_key(r['status']) == 'PRESENT'])
                    absent_count = len([r for r in date_records if status_key(r['status']) == 'ABSENT'])
                    late_count = len([r for r in date_records if status_key(r['status']) == 'LATE'])
                    leave_count = len([r for r in date_records if status_key(r['status']) == 'LEAVE'])
                    
                    # Sort records by roll number
                    date_records.sort(key=lambda x: x['student']['roll_no'] or '')
                    
                    result.append({
                        'date': date_key,
                        'total_marked': len(date_records),
                        'present': present_count,
                        'absent': absent_count,
                        'late': late_count,
                        'leave': leave_count,
                        'records': date_records
                    })
                
                return result
                
        except Exception as e:
            raise Exception(f"Error fetching date range attendance: {str(e)}")
    
    
    @staticmethod
    def update_attendance_record(skid, attendance_id, status, remarks=None):
        """
        Update an existing attendance record
        
        Args:
            skid: School ID
            attendance_id: Attendance record ID
            status: New status
            remarks: Updated remarks (optional)
            
        Returns:
            dict: Updated attendance record
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                record = tenant_session.query(Attendance).filter(
                    Attendance.id == attendance_id
                ).first()
                
                if not record:
                    raise ValueError("Attendance record not found")
                
                # Update fields
                old_status = record.status
                record.status = normalize_status(status)
                if remarks is not None:
                    record.remarks = remarks
                record.updated_at = datetime.now()

                tenant_session.commit()

                from app.services import push_events
                push_events.students_marked_absent(
                    skid, tenant_session,
                    push_events.newly_absent({record.student_user_id: old_status}, {record.student_user_id: record.status}),
                    record.date)
                
                # Fetch student details with user information
                student = tenant_session.query(Student).filter(
                    Student.user_id == record.student_user_id
                ).first()
                
                return {
                    'id': record.id,
                    'student': {
                        'id': student.user_id,
                        'name': f"{student.user.first_name} {student.user.last_name}",
                        'roll_no': student.roll_no
                    } if student and student.user else None,
                    'status': status_key(record.status),  # old rows were stored as 'Present' / 'present'
                    'remarks': record.remarks,
                    'date': record.date.strftime('%Y-%m-%d'),
                    'updated_at': record.updated_at.strftime('%Y-%m-%d %H:%M:%S')
                }
                
        except Exception as e:
            if tenant_session:
                tenant_session.rollback()
            raise Exception(f"Error updating attendance: {str(e)}")
    
    
    @staticmethod
    def get_attendance_by_student(skid, student_id, start_date=None, end_date=None):
        """
        Get attendance records for a specific student
        
        Args:
            skid: School ID
            student_id: Student user ID
            start_date: Optional start date
            end_date: Optional end date
            
        Returns:
            dict: Student attendance details with statistics
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Build query
                query = tenant_session.query(Attendance).filter(
                    Attendance.student_user_id == student_id
                )
                
                if start_date:
                    query = query.filter(Attendance.date >= start_date)
                if end_date:
                    query = query.filter(Attendance.date <= end_date)
                
                records = query.order_by(Attendance.date.desc()).all()
                
                # Get student details with user information
                student = tenant_session.query(Student).join(
                    SchoolUsers, Student.user_id == SchoolUsers.id
                ).filter(
                    Student.user_id == student_id
                ).first()
                
                if not student:
                    raise ValueError("Student not found")
                
                # Get class and section names if available
                class_name = None
                section_name = None
                
                if student.section_obj:
                    section_name = student.section_obj.section_name
                    if student.section_obj.class_obj:
                        class_name = student.section_obj.class_obj.class_name
                
                # Calculate statistics
                total_days = len(records)
                present_count = len([r for r in records if status_key(r.status) == 'PRESENT'])
                absent_count = len([r for r in records if status_key(r.status) == 'ABSENT'])
                late_count = len([r for r in records if status_key(r.status) == 'LATE'])
                leave_count = len([r for r in records if status_key(r.status) == 'LEAVE'])
                
                attended_count = present_count + late_count
                attendance_percentage = round((attended_count / total_days * 100), 2) if total_days > 0 else 0
                
                # Format records
                formatted_records = []
                for record in records:
                    formatted_records.append({
                        'id': record.id,
                        'date': record.date.strftime('%Y-%m-%d'),
                        'status': status_key(record.status),  # old rows were stored as 'Present' / 'present'
                        'remarks': record.remarks,
                        'created_at': record.created_at.strftime('%Y-%m-%d %H:%M:%S') if record.created_at else None
                    })
                
                return {
                    'student': {
                        'id': student.user_id,
                        'name': f"{student.user.first_name} {student.user.last_name}",
                        'roll_no': student.roll_no,
                        'email': student.user.email,
                        'phone': student.user.phone,
                        'class': class_name,
                        'section': section_name,
                        'admission_date': student.admission_date.strftime('%Y-%m-%d') if student.admission_date else None
                    },
                    'statistics': {
                        'total_days': total_days,
                        'present_count': present_count,
                        'absent_count': absent_count,
                        'late_count': late_count,
                        'leave_count': leave_count,
                        'attendance_percentage': attendance_percentage,
                        'status': 'Excellent' if attendance_percentage >= 90 else 'Good' if attendance_percentage >= 75 else 'Warning' if attendance_percentage >= 60 else 'Critical'
                    },
                    'records': formatted_records
                }
                
        except Exception as e:
            raise Exception(f"Error fetching student attendance: {str(e)}")
    
    
    @staticmethod
    def get_class_students_list(skid, class_id, section_id):
        """
        Get list of all students in a class/section for attendance marking
        
        Args:
            skid: School ID
            class_id: Class ID
            section_id: Section ID
            
        Returns:
            list: List of students with their details
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                students = tenant_session.query(Student).join(
                    SchoolUsers, Student.user_id == SchoolUsers.id
                ).filter(
                    Student.class_id == class_id,
                    Student.section_id == section_id,
                    SchoolUsers.is_active == True
                ).order_by(Student.roll_no).all()
                
                student_list = []
                for student in students:
                    student_list.append({
                        'id': student.user_id,
                        'roll_no': student.roll_no,
                        'name': f"{student.user.first_name} {student.user.last_name}",
                        'first_name': student.user.first_name,
                        'last_name': student.user.last_name,
                        'email': student.user.email,
                        'phone': student.user.phone,
                        'gender': student.user.gender,
                        'date_of_birth': student.user.date_of_birth.strftime('%Y-%m-%d') if student.user.date_of_birth else None,
                        'admission_date': student.admission_date.strftime('%Y-%m-%d') if student.admission_date else None
                    })
                
                return student_list
                
        except Exception as e:
            raise Exception(f"Error fetching students list: {str(e)}")
