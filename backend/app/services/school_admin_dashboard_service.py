from app.utils.db_manager import switch_to_school_db
from app.models.tenant import Student, Teacher, SchoolUsers, AcademicYear, StudentEnrollment, Attendance, Subject, Class
from app.models.tenant.ExpenseModels import Expense
from app.models.tenant.FeeModels import StudentFee, FeePayment
from app.models.tenant.Roles import Role
from sqlalchemy import func, and_, or_, extract, case, cast, Float
from datetime import date, datetime, timedelta
from app.models.tenant.TimeTable import Timetable
from app.models.tenant.Sections import Section
from app.models.tenant.TimeTableEntry import TimetableEntry

class SchoolAdminDashboardService:
    
    @staticmethod
    def get_dashboard_stats(skid, academic_year_id):
        """Get dashboard statistics for school admin"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Validate academic year
                academic_year = tenant_session.query(AcademicYear).filter_by(
                    id=academic_year_id
                ).first()
                
                if not academic_year:
                    raise ValueError("Invalid academic year")
                
                # Get stats
                stats = SchoolAdminDashboardService._get_counts(
                    tenant_session, academic_year_id
                )
                
                return {
                    'academic_year': {
                        'id': academic_year.id,
                        'year_name': academic_year.year_name
                    },
                    'stats': stats
                }
                
        except Exception as e:
            raise Exception(f"Failed to get dashboard stats: {str(e)}")
    
    @staticmethod
    def _get_counts(tenant_session, academic_year_id):
        """Get count statistics"""
        
        # Total students
        total_students = tenant_session.query(
            func.count(StudentEnrollment.id)
        ).filter(
            StudentEnrollment.academic_year_id == academic_year_id,
            StudentEnrollment.status == 'active'
        ).scalar() or 0
        
        # Gender distribution
        gender_stats = tenant_session.query(
            SchoolUsers.gender,
            func.count(SchoolUsers.id)
        ).join(
            Student, SchoolUsers.id == Student.user_id
        ).join(
            StudentEnrollment, StudentEnrollment.student_id == Student.user_id
        ).filter(
            StudentEnrollment.academic_year_id == academic_year_id,
            StudentEnrollment.status == 'active'
        ).group_by(SchoolUsers.gender).all()
        
        male_count = next((count for gender, count in gender_stats if gender == 'Male'), 0)
        female_count = next((count for gender, count in gender_stats if gender == 'Female'), 0)
        
        # Total teachers
        total_teachers = tenant_session.query(
            func.count(Teacher.user_id)
        ).scalar() or 0
        
        # Total parents (users with PARENT role)
        total_parents = tenant_session.query(
            func.count(SchoolUsers.id)
        ).join(
            Role, SchoolUsers.role_id == Role.id
        ).filter(
            Role.role_code == 'PARENT'  # Assuming role name is stored in Role table
        ).scalar() or 0
        
        # Overall users count
        overall_users = tenant_session.query(
            func.count(SchoolUsers.id)
        ).scalar() or 0
        
        today = date.today()

        # Count all attendance records marked as Present/Late for today
        present_count = tenant_session.query(func.count(Attendance.id)).filter(
            and_(
                Attendance.academic_year_id == academic_year_id,
                Attendance.date == today,
                Attendance.status.in_(['PRESENT', 'LATE'])
            )
        ).scalar() or 0
        
        return {
            'students_count': total_students,
            'male_students': male_count,
            'female_students': female_count,
            'teachers_count': total_teachers,
            'parents_count': total_parents,
            'overall_users_count': overall_users,
            'today_attendance_present': present_count,
            'today_attendance_total_students': total_students
        }


    @staticmethod
    def get_monthly_expenses_by_category(skid, academic_year_id, month=None):
        """Get monthly expenses breakdown by category"""
        try:
            # Default to current month if not provided
            if not month:
                month = datetime.now().month
            
            with switch_to_school_db(skid) as tenant_session:
                # Get academic year to determine the year
                academic_year = tenant_session.query(AcademicYear).filter(
                    AcademicYear.id == academic_year_id
                ).first()
                
                if not academic_year:
                    raise ValueError("Academic year not found")
                
                year = academic_year.start_date.year
                # If month is before academic year start month, use next year
                if month < academic_year.start_date.month:
                    year = academic_year.end_date.year
                
                # Get expenses grouped by category and date
                expenses = (
                    tenant_session.query(
                        func.date(Expense.expense_date).label('date'),
                        Expense.expense_category,
                        func.sum(Expense.amount).label('total')
                    )
                    .filter(
                        Expense.academic_year_id == academic_year_id,
                        extract('month', Expense.expense_date) == month,
                        extract('year', Expense.expense_date) == year
                    )
                    .group_by(func.date(Expense.expense_date), Expense.expense_category)
                    .order_by(func.date(Expense.expense_date))
                    .all()
                )
                
                # Get unique categories and dates
                categories = list(set([e.expense_category for e in expenses]))
                dates = sorted(list(set([e.date for e in expenses])))
                
                # Build category-wise breakdown
                category_data = {}
                category_totals = {}
                
                for category in categories:
                    category_data[category] = []
                    category_totals[category] = 0
                    
                    for date in dates:
                        amount = next(
                            (float(e.total) for e in expenses 
                             if e.date == date and e.expense_category == category), 
                            0
                        )
                        category_data[category].append({
                            'date': date.isoformat(),
                            'day': date.day,
                            'amount': amount
                        })
                        category_totals[category] += amount
                
                total_expenses = sum(category_totals.values())
                
                return {
                    'month': month,
                    'year': year,
                    'month_name': datetime(year, month, 1).strftime('%B'),
                    'total_expenses': total_expenses,
                    'categories': categories,
                    'dates': [{'date': d.isoformat(), 'day': d.day} for d in dates],
                    'category_data': category_data,
                    'category_totals': category_totals
                }
                
        except Exception as e:
            raise Exception(f"Failed to get expense breakdown: {str(e)}")


    @staticmethod
    def get_timetable(skid, academic_year_id, class_id=None, section_id=None):
        """Get timetable for a specific class and section or the last created one"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Build query
                query = tenant_session.query(Timetable).filter(
                    Timetable.academic_year_id == academic_year_id,
                    Timetable.is_active == True
                )
                
                # If class_id and section_id provided, filter by them
                if class_id and section_id:
                    query = query.filter(
                        Timetable.class_id == class_id,
                        Timetable.section_id == section_id
                    )
                
                # Get the most recent timetable
                timetable = query.order_by(Timetable.created_at.desc()).first()
                
                if not timetable:
                    return {
                        'timetable': None,
                        'entries': [],
                        'message': 'No timetable found'
                    }
                
                # Get timetable entries with related data
                entries = tenant_session.query(
                    TimetableEntry,
                    Subject.subject_name,
                    SchoolUsers.first_name,
                    SchoolUsers.last_name
                ).join(
                    Subject, TimetableEntry.subject_id == Subject.id
                ).join(
                    Teacher, TimetableEntry.teacher_id == Teacher.user_id
                ).join(
                    SchoolUsers, Teacher.user_id == SchoolUsers.id
                ).filter(
                    TimetableEntry.timetable_id == timetable.id,
                    TimetableEntry.is_active == True
                ).order_by(
                    TimetableEntry.day_of_week,
                    TimetableEntry.period_number
                ).all()
                
                # Get class and section names
                class_obj = tenant_session.query(Class).filter(
                    Class.id == timetable.class_id
                ).first()
                
                section_obj = tenant_session.query(Section).filter(
                    Section.id == timetable.section_id
                ).first()
                
                # Format entries
                formatted_entries = []
                for entry, subject_name, first_name, last_name in entries:
                    formatted_entries.append({
                        'id': entry.id,
                        'day_of_week': entry.day_of_week,
                        'period_number': entry.period_number,
                        'start_time': entry.start_time.strftime('%H:%M') if entry.start_time else None,
                        'end_time': entry.end_time.strftime('%H:%M') if entry.end_time else None,
                        'subject_name': subject_name,
                        'teacher_name': f"{first_name} {last_name}",
                        'room_number': entry.room_number,
                        'class_type': entry.class_type
                    })
                
                # Organize by day
                days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
                timetable_by_day = {}
                
                for day in days_order:
                    day_entries = [e for e in formatted_entries if e['day_of_week'] == day]
                    if day_entries:
                        timetable_by_day[day] = sorted(day_entries, key=lambda x: x['period_number'])
                
                return {
                    'timetable': {
                        'id': timetable.id,
                        'class_id': timetable.class_id,
                        'class_name': class_obj.class_name if class_obj else None,
                        'section_id': timetable.section_id,
                        'section_name': section_obj.section_name if section_obj else None,
                        'semester': timetable.semester,
                        'period_duration': timetable.period_duration,
                        'school_start_time': timetable.school_start_time.strftime('%H:%M') if timetable.school_start_time else None,
                        'lunch_start_time': timetable.lunch_start_time.strftime('%H:%M') if timetable.lunch_start_time else None,
                        'lunch_duration': timetable.lunch_duration,
                        'total_periods': timetable.total_periods
                    },
                    'entries': formatted_entries,
                    'timetable_by_day': timetable_by_day
                }
                
        except Exception as e:
            raise Exception(f"Failed to get timetable: {str(e)}")

    @staticmethod
    def get_attendance_overview(skid, academic_year_id, class_id=None, section_id=None):
        """Get attendance overview for the current week, optionally filtered by class/section"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                today = date.today()
                # Get Monday of current week
                monday = today - timedelta(days=today.weekday())

                # Build student count query with optional filters
                student_query = tenant_session.query(
                    func.count(StudentEnrollment.id)
                ).filter(
                    StudentEnrollment.academic_year_id == academic_year_id,
                    StudentEnrollment.status == 'active'
                )
                if class_id:
                    student_query = student_query.filter(StudentEnrollment.class_id == class_id)
                if section_id:
                    student_query = student_query.filter(StudentEnrollment.section_id == section_id)

                total_students = student_query.scalar() or 0

                if total_students == 0:
                    return {
                        'total_students': 0,
                        'weekly_trend': [],
                        'today_present': 0,
                        'today_absent': 0,
                        'today_percentage': 0
                    }

                day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
                weekly_trend = []

                for i in range(6):
                    current_date = monday + timedelta(days=i)
                    if current_date > today:
                        break

                    present_query = tenant_session.query(func.count(Attendance.id)).filter(
                        and_(
                            Attendance.academic_year_id == academic_year_id,
                            Attendance.date == current_date,
                            Attendance.status.in_(['PRESENT', 'LATE'])
                        )
                    )
                    if class_id:
                        present_query = present_query.filter(Attendance.class_id == class_id)
                    if section_id:
                        present_query = present_query.filter(Attendance.section_id == section_id)
                    present = present_query.scalar() or 0

                    total_marked_query = tenant_session.query(func.count(Attendance.id)).filter(
                        and_(
                            Attendance.academic_year_id == academic_year_id,
                            Attendance.date == current_date
                        )
                    )
                    if class_id:
                        total_marked_query = total_marked_query.filter(Attendance.class_id == class_id)
                    if section_id:
                        total_marked_query = total_marked_query.filter(Attendance.section_id == section_id)
                    total_marked = total_marked_query.scalar() or 0

                    percentage = round((present / total_marked * 100), 1) if total_marked > 0 else 0

                    weekly_trend.append({
                        'day': day_names[i],
                        'date': current_date.isoformat(),
                        'present': present,
                        'absent': total_marked - present,
                        'total': total_marked,
                        'percentage': percentage
                    })

                # Today's stats
                today_present_query = tenant_session.query(func.count(Attendance.id)).filter(
                    and_(
                        Attendance.academic_year_id == academic_year_id,
                        Attendance.date == today,
                        Attendance.status.in_(['PRESENT', 'LATE'])
                    )
                )
                if class_id:
                    today_present_query = today_present_query.filter(Attendance.class_id == class_id)
                if section_id:
                    today_present_query = today_present_query.filter(Attendance.section_id == section_id)
                today_present = today_present_query.scalar() or 0

                today_total_query = tenant_session.query(func.count(Attendance.id)).filter(
                    and_(
                        Attendance.academic_year_id == academic_year_id,
                        Attendance.date == today
                    )
                )
                if class_id:
                    today_total_query = today_total_query.filter(Attendance.class_id == class_id)
                if section_id:
                    today_total_query = today_total_query.filter(Attendance.section_id == section_id)
                today_total = today_total_query.scalar() or 0

                today_percentage = round((today_present / today_total * 100), 1) if today_total > 0 else 0

                return {
                    'total_students': total_students,
                    'weekly_trend': weekly_trend,
                    'today_present': today_present,
                    'today_absent': today_total - today_present,
                    'today_total_marked': today_total,
                    'today_percentage': today_percentage
                }

        except Exception as e:
            raise Exception(f"Failed to get attendance overview: {str(e)}")

    @staticmethod
    def get_finance_summary(skid, academic_year_id):
        """Get finance summary for school admin dashboard"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Fee collection summary
                fee_stats = tenant_session.query(
                    func.coalesce(func.sum(StudentFee.total_amount), 0).label('total_fees'),
                    func.coalesce(func.sum(StudentFee.paid_amount), 0).label('total_collected'),
                    func.coalesce(func.sum(StudentFee.discount_amount), 0).label('total_discount'),
                    func.count(StudentFee.id).label('total_assignments')
                ).filter(
                    StudentFee.academic_year_id == academic_year_id
                ).first()

                total_fees = float(fee_stats.total_fees) if fee_stats.total_fees else 0
                total_collected = float(fee_stats.total_collected) if fee_stats.total_collected else 0
                total_discount = float(fee_stats.total_discount) if fee_stats.total_discount else 0
                total_pending = total_fees - total_collected - total_discount

                # Count by status
                status_counts = tenant_session.query(
                    StudentFee.status,
                    func.count(StudentFee.id)
                ).filter(
                    StudentFee.academic_year_id == academic_year_id
                ).group_by(StudentFee.status).all()

                status_map = {status: count for status, count in status_counts}

                # Recent payments (last 5)
                recent_payments = tenant_session.query(
                    FeePayment,
                    StudentFee,
                    SchoolUsers.first_name,
                    SchoolUsers.last_name
                ).join(
                    StudentFee, FeePayment.student_fee_id == StudentFee.id
                ).join(
                    Student, StudentFee.student_id == Student.user_id
                ).join(
                    SchoolUsers, Student.user_id == SchoolUsers.id
                ).filter(
                    StudentFee.academic_year_id == academic_year_id,
                    FeePayment.is_cancelled == False
                ).order_by(
                    FeePayment.created_at.desc()
                ).limit(5).all()

                recent_list = []
                for payment, student_fee, first_name, last_name in recent_payments:
                    recent_list.append({
                        'id': payment.id,
                        'student_name': f"{first_name} {last_name}",
                        'amount': float(payment.amount_paid),
                        'payment_mode': payment.payment_mode.value if payment.payment_mode else None,
                        'payment_date': payment.payment_date.isoformat() if payment.payment_date else None,
                        'receipt_number': payment.receipt_number
                    })

                # Total expenses for the academic year
                total_expenses = tenant_session.query(
                    func.coalesce(func.sum(Expense.amount), 0)
                ).filter(
                    Expense.academic_year_id == academic_year_id
                ).scalar() or 0

                collection_rate = round((total_collected / total_fees * 100), 1) if total_fees > 0 else 0

                return {
                    'total_fees': total_fees,
                    'total_collected': total_collected,
                    'total_pending': total_pending,
                    'total_discount': total_discount,
                    'total_expenses': float(total_expenses),
                    'collection_rate': collection_rate,
                    'status_breakdown': {
                        'paid': status_map.get('PAID', 0),
                        'partial': status_map.get('PARTIAL', 0),
                        'pending': status_map.get('PENDING', 0),
                        'overdue': status_map.get('OVERDUE', 0)
                    },
                    'recent_payments': recent_list
                }
        
        except Exception as e:
            raise Exception(f"Failed to get finance overview: {str(e)}")

