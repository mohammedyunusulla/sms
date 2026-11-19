from app import db
from app.utils.db_manager import switch_to_school_db
from app.models.tenant.TimeTableEntry import TimetableEntry
from app.models.tenant.Announcement import Announcement
from app.models.tenant.Attendance import Attendance
from app.models.tenant.Student import Student
from app.models.tenant.SchoolUsers import SchoolUsers
from app.models.tenant.Subject import Subject
from app.models.tenant.Class import Class
from app.models.tenant.Sections import Section
from sqlalchemy import and_, or_, func, distinct
from app.utils.attendance_status import status_column
from datetime import datetime, date, timedelta


class TeacherDashboardService:

    @staticmethod
    def get_teacher_timetable_by_day(skid, teacher_id, date):
        """
        Get teacher's timetable for a specific day

        Args:
            skid: School ID
            teacher_id: Teacher user ID
            date: Date string in YYYY-MM-DD format

        Returns:
            List of periods with details for the specified day
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Parse date and get day of week
                date_obj = datetime.strptime(date, '%Y-%m-%d').date()
                day_name = date_obj.strftime('%A')  # Monday, Tuesday, etc.

                # Import Timetable model
                from app.models.tenant.TimeTable import Timetable

                # Query timetable entries for the teacher on the specified day
                entries = tenant_session.query(
                    TimetableEntry.id,
                    TimetableEntry.period_number,
                    TimetableEntry.start_time,
                    TimetableEntry.end_time,
                    TimetableEntry.room_number,
                    TimetableEntry.subject_id,
                    Subject.subject_name.label('subject_name'),
                    Class.class_name.label('class_name'),
                    Section.section_name.label('section_name'),
                    TimetableEntry.timetable_id
                ).join(
                    Subject, TimetableEntry.subject_id == Subject.id
                ).join(
                    Timetable, TimetableEntry.timetable_id == Timetable.id
                ).join(
                    Class, Timetable.class_id == Class.id
                ).join(
                    Section, Timetable.section_id == Section.id
                ).filter(
                    and_(
                        TimetableEntry.teacher_id == teacher_id,
                        TimetableEntry.day_of_week == day_name,
                        TimetableEntry.is_active == True
                    )
                ).order_by(
                    TimetableEntry.period_number
                ).all()

                # Format results
                periods = []
                for entry in entries:
                    periods.append({
                        'id': entry.id,
                        'period_number': entry.period_number,
                        'start_time': entry.start_time.strftime('%H:%M'),
                        'end_time': entry.end_time.strftime('%H:%M'),
                        'subject_name': entry.subject_name,
                        'subject_id': entry.subject_id,
                        'class_name': entry.class_name,
                        'section_name': entry.section_name,
                        'room': entry.room_number,
                        'day': day_name
                    })

                return periods

        except Exception as e:
            raise Exception(f"Failed to fetch teacher timetable: {str(e)}")

    @staticmethod
    def get_teacher_announcements(skid, limit=10):
        """
        Get latest announcements relevant to teachers

        Args:
            skid: School ID
            limit: Maximum number of announcements to return

        Returns:
            List of announcements sorted by newest first
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                now = datetime.utcnow()

                # Query published announcements targeting teachers
                announcements = tenant_session.query(
                    Announcement.id,
                    Announcement.title,
                    Announcement.description.label('content'),
                    Announcement.announcement_type,
                    Announcement.priority,
                    Announcement.created_at,
                    Announcement.created_by,
                    SchoolUsers.first_name,
                    SchoolUsers.last_name
                ).join(
                    SchoolUsers, Announcement.created_by == SchoolUsers.id
                ).filter(
                    and_(
                        Announcement.is_published == True,
                        Announcement.is_active == True,
                        or_(
                            Announcement.expiry_date.is_(None),
                            Announcement.expiry_date > now
                        ),
                        or_(
                            Announcement.target_audience == 'All Users',
                            Announcement.target_audience == 'All Teachers'
                        )
                    )
                ).order_by(
                    Announcement.created_at.desc()
                ).limit(limit).all()

                # Format results
                result = []
                for ann in announcements:
                    result.append({
                        'id': ann.id,
                        'title': ann.title,
                        'content': ann.content,
                        'type': ann.announcement_type,
                        'priority': ann.priority,
                        'created_at': ann.created_at.isoformat() if ann.created_at else None,
                        'author': f"{ann.first_name} {ann.last_name}" if ann.first_name else 'Admin'
                    })

                return result

        except Exception as e:
            raise Exception(f"Failed to fetch announcements: {str(e)}")

    @staticmethod
    def get_today_absentees(skid, academic_year_id, date, teacher_id=None):
        """
        Get today's student absentees with count and preview
        Args:
            skid: School ID
            academic_year_id: Academic year ID
            date: Date string in YYYY-MM-DD format 
        Returns:
            Dict with count and preview list (max 3 students)
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                attendance_date = datetime.strptime(date, '%Y-%m-%d').date()
                
                # Base filter conditions
                conditions = [
                    Attendance.date == attendance_date,
                    Attendance.academic_year_id == academic_year_id,
                    status_column(Attendance.status) == 'ABSENT',
                    SchoolUsers.is_active == True
                ]
                # A teacher only sees absentees from the sections they work in (it used to be the whole school)
                if teacher_id is not None:
                    from app.utils.teaching_scope import teacher_section_ids
                    section_ids = teacher_section_ids(tenant_session, teacher_id)
                    if not section_ids:
                        return {'count': 0, 'preview': [], 'date': date}
                    conditions.append(Attendance.section_id.in_(section_ids))
                base_filters = and_(*conditions)
                
                # Query 1: Get total count efficiently
                total_count = tenant_session.query(
                    func.count(Attendance.id)
                ).join(
                    SchoolUsers, Attendance.student_user_id == SchoolUsers.id
                ).filter(base_filters).scalar() or 0
                
                # Query 2: Get preview (max 3 records only)
                preview_query = tenant_session.query(
                    Student.user_id,
                    SchoolUsers.first_name,
                    SchoolUsers.last_name,
                    Student.roll_no,
                    Class.class_name,
                    Section.section_name,
                    Attendance.remarks
                ).join(
                    SchoolUsers, Student.user_id == SchoolUsers.id
                ).join(
                    Attendance, Attendance.student_user_id == Student.user_id
                ).outerjoin(
                    Class, Attendance.class_id == Class.id
                ).outerjoin(
                    Section, Attendance.section_id == Section.id
                ).filter(base_filters).limit(3).all()
                
                # Format preview list
                preview_list = [
                    {
                        'student_id': absentee.user_id,
                        'full_name': f"{absentee.first_name} {absentee.last_name}",
                        'roll_no': absentee.roll_no,
                        'class_name': absentee.class_name,
                        'section_name': absentee.section_name,
                        'remarks': absentee.remarks
                    }
                    for absentee in preview_query
                ]
                
                return {
                    'count': total_count,
                    'preview': preview_list,
                    'date': date
                }
        
        except Exception as e:
            raise Exception(f"Failed to fetch absentees data: {str(e)}")


    @staticmethod
    def get_assigned_students_count(skid, teacher_id):
        """
        Get total count of unique students assigned to a teacher

        Args:
            skid: School ID
            teacher_id: Teacher user ID

        Returns:
            Integer count of unique students
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Import Timetable model
                from app.models.tenant.TimeTable import Timetable

                # Get all unique section IDs taught by the teacher
                section_ids = tenant_session.query(
                    distinct(Timetable.section_id)
                ).join(
                    TimetableEntry, TimetableEntry.timetable_id == Timetable.id
                ).filter(
                    and_(
                        TimetableEntry.teacher_id == teacher_id,
                        TimetableEntry.is_active == True
                    )
                ).all()

                if not section_ids:
                    return 0

                # Flatten section IDs
                section_id_list = [sid[0] for sid in section_ids if sid[0] is not None]

                if not section_id_list:
                    return 0

                # Count unique students in these sections
                student_count = tenant_session.query(
                    func.count(distinct(Student.user_id))
                ).filter(
                    Student.section_id.in_(section_id_list)
                ).scalar()

                return student_count or 0

        except Exception as e:
            raise Exception(f"Failed to fetch student count: {str(e)}")

    @staticmethod
    def get_teacher_week_timetable(skid, teacher_id, start_date=None):
        """
        Get teacher's timetable for a full week (Monday-Saturday)

        Args:
            skid: School ID
            teacher_id: Teacher user ID
            start_date: Week start date (Monday) in YYYY-MM-DD format (optional)

        Returns:
            Dict with timetable organized by day
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Import Timetable model
                from app.models.tenant.TimeTable import Timetable

                # If no start_date provided, get current week's Monday
                if start_date:
                    base_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                else:
                    today = date.today()
                    # Get Monday of current week
                    base_date = today - timedelta(days=today.weekday())

                # Query all timetable entries for the teacher
                entries = tenant_session.query(
                    TimetableEntry.id,
                    TimetableEntry.day_of_week,
                    TimetableEntry.period_number,
                    TimetableEntry.start_time,
                    TimetableEntry.end_time,
                    TimetableEntry.room_number,
                    Subject.subject_name.label('subject_name'),
                    Class.class_name.label('class_name'),
                    Section.section_name.label('section_name')
                ).join(
                    Subject, TimetableEntry.subject_id == Subject.id
                ).join(
                    Timetable, TimetableEntry.timetable_id == Timetable.id
                ).join(
                    Class, Timetable.class_id == Class.id
                ).join(
                    Section, Timetable.section_id == Section.id
                ).filter(
                    and_(
                        TimetableEntry.teacher_id == teacher_id,
                        TimetableEntry.is_active == True
                    )
                ).order_by(
                    TimetableEntry.day_of_week,
                    TimetableEntry.period_number
                ).all()

                # Organize by day
                days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
                week_timetable = {}

                for day in days_order:
                    day_entries = [e for e in entries if e.day_of_week == day]
                    week_timetable[day] = []

                    for entry in day_entries:
                        week_timetable[day].append({
                            'id': entry.id,
                            'period_number': entry.period_number,
                            'start_time': entry.start_time.strftime('%H:%M'),
                            'end_time': entry.end_time.strftime('%H:%M'),
                            'subject_name': entry.subject_name,
                            'class_name': entry.class_name,
                            'section_name': entry.section_name,
                            'room': entry.room_number,
                            'day': day
                        })

                return {
                    'week_start': base_date.isoformat(),
                    'timetable_by_day': week_timetable
                }

        except Exception as e:
            raise Exception(f"Failed to fetch week timetable: {str(e)}")
