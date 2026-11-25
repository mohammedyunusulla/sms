from .auth import auth_bp
from .user import user_bp
from .teacher import teacher_bp
from .student import student_bp
from .institution import institution_bp
from .classes import class_bp
from .subject import subject_bp
from .roles import roles_bp
from .userRoles import user_roles_bp
from .attendance import attendance_bp
from .parent import parent_bp
from .timeTable import timeTable_bp
from .studentParent import studentParent_bp
from .fee import fee_bp
from .announcement import announcement_bp
from .institution_admin_dashboard_routes import institution_admin_dashboard_bp
from .exam_routes import exam_bp
from .marks_routes import marks_bp
from .progress_card_routes import progress_card_bp
from .expense_routes import expense_bp
from .academic_year import academic_year_bp
from .teacher_dashboard_routes import teacher_dashboard_bp
from .syllabus import syllabus_bp
from .assignment import assignment_bp
from .student_dashboard_routes import student_dashboard_bp
from .room_routes import room_bp
from .seating_routes import seating_bp
from .bus_scan import bus_scan_bp
from .staff_routes import staff_bp
from .bus_location import bus_location_bp
from .homework import homework_bp
from .push import push_bp
from .leave import leave_bp
from .staff_attendance import staff_attendance_bp

__all__ = ['auth_bp', 'user_bp', 'teacher_bp', 'student_bp',
            'institution_bp', 'class_bp', 'subject_bp', 'roles_bp',
            'user_roles_bp', 'attendance_bp', 'parent_bp', 'timeTable_bp', 'studentParent_bp',
            'fee_bp', 'announcement_bp', 'exam_bp', 'marks_bp', 'progress_card_bp',
            'institution_admin_dashboard_bp', 'expense_bp', 'academic_year_bp', 'teacher_dashboard_bp',
            'syllabus_bp', 'assignment_bp', 'student_dashboard_bp', 'room_bp', 'seating_bp',
            'bus_scan_bp', 'staff_bp', 'bus_location_bp', 'homework_bp', 'push_bp', 'leave_bp', 'staff_attendance_bp'
        ]