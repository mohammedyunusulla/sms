from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO
import os
import logging
from logging.handlers import RotatingFileHandler
from config import config
from sqlalchemy import text

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
cors = CORS()
jwt = JWTManager()
socketio = SocketIO()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per minute"],
    storage_uri="memory://"
)

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV') or 'default'
    
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    # CORS: restrict origins in production, allow all in development
    allowed_origins = app.config.get('CORS_ORIGINS', '*')
    cors.init_app(app, resources={r"/api/*": {"origins": allowed_origins}})
    jwt.init_app(app)
    limiter.init_app(app)
    _bootstrap_main_schema(app)
    _bootstrap_tenant_schemas(app)
        
    # Setup logging
    # setup_logging(app)
    
    # Register blueprints
    from app.api import (
        auth_bp, user_bp, teacher_bp, student_bp, institution_bp, class_bp, subject_bp, attendance_bp,
        parent_bp, roles_bp, user_roles_bp, timeTable_bp, studentParent_bp, fee_bp, announcement_bp,
        institution_admin_dashboard_bp, exam_bp, marks_bp, progress_card_bp, expense_bp, academic_year_bp,
        teacher_dashboard_bp, syllabus_bp, assignment_bp, student_dashboard_bp, room_bp, seating_bp,
        bus_scan_bp, staff_bp, homework_bp, push_bp, leave_bp, staff_attendance_bp, holidays_bp, calendar_bp, events_bp, substitutions_bp
    )
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(user_bp, url_prefix='/api/users')
    app.register_blueprint(teacher_bp, url_prefix='/api/teachers')
    app.register_blueprint(student_bp, url_prefix='/api/students')
    app.register_blueprint(parent_bp, url_prefix='/api/parents')
    app.register_blueprint(studentParent_bp, url_prefix='/api/studentParent')
    app.register_blueprint(institution_bp, url_prefix='/api/institution')
    app.register_blueprint(class_bp, url_prefix='/api/classes')
    app.register_blueprint(subject_bp, url_prefix='/api/subjects')
    app.register_blueprint(attendance_bp, url_prefix='/api/attendance')
    app.register_blueprint(timeTable_bp, url_prefix='/api/timeTable')
    app.register_blueprint(fee_bp, url_prefix='/api/fee')
    app.register_blueprint(roles_bp, url_prefix='/api/roles')
    app.register_blueprint(user_roles_bp, url_prefix='/api/user-roles')
    app.register_blueprint(announcement_bp, url_prefix='/api/announcements')
    app.register_blueprint(institution_admin_dashboard_bp, url_prefix='/api/institutionAdminDashboard')
    app.register_blueprint(teacher_dashboard_bp, url_prefix='/api/teacherDashboard')
    app.register_blueprint(exam_bp, url_prefix='/api/exams')
    app.register_blueprint(marks_bp, url_prefix='/api/marks')
    app.register_blueprint(expense_bp, url_prefix='/api/expenses')
    app.register_blueprint(progress_card_bp, url_prefix='/api/progress-card')
    app.register_blueprint(academic_year_bp, url_prefix='/api/academic-years')
    app.register_blueprint(syllabus_bp, url_prefix='/api/syllabus')
    app.register_blueprint(assignment_bp, url_prefix='/api/assignments')
    app.register_blueprint(student_dashboard_bp, url_prefix='/api/studentDashboard')
    app.register_blueprint(room_bp, url_prefix='/api/rooms')
    app.register_blueprint(seating_bp, url_prefix='/api/seating')
    app.register_blueprint(bus_scan_bp, url_prefix='/api/bus-scan')
    app.register_blueprint(staff_bp, url_prefix='/api/staff')
    app.register_blueprint(homework_bp, url_prefix='/api/homework')
    app.register_blueprint(push_bp, url_prefix='/api/push')  # push notifications (installed app)
    app.register_blueprint(leave_bp, url_prefix='/api/leave')  # leave requests (students, staff)
    app.register_blueprint(staff_attendance_bp, url_prefix='/api/staff-attendance')
    app.register_blueprint(holidays_bp, url_prefix='/api/holidays')  # holiday calendar, weekly offs
    app.register_blueprint(calendar_bp, url_prefix='/api/calendar')  # Calendar page: holidays, exams, leave, events
    app.register_blueprint(events_bp, url_prefix='/api/events')  # events / parent-teacher meetings
    app.register_blueprint(substitutions_bp, url_prefix='/api/substitutions')  # substitute teacher planner

    from app.api import bus_location_bp
    app.register_blueprint(bus_location_bp, url_prefix='/api/bus-location')

    # Initialize SocketIO
    socketio.init_app(app, cors_allowed_origins=allowed_origins, async_mode='threading')

    # Register SocketIO event handlers
    from app.sockets import bus_location_events  # noqa: F401
    
    # JWT token handlers — check if token's session has been invalidated
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        session_token = jwt_payload.get('session_token')
        if not session_token:
            # Tokens without a session_token are considered revoked
            return True
        from app.models.main.UserSession import UserSession
        session = UserSession.get_active_session(session_token)
        # If no active session found, the token is revoked
        return session is None
    
    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return {'message': 'Token has been revoked. Please login again.'}, 401

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return {'message': 'Token has expired'}, 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return {'message': 'Invalid token'}, 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return {'message': 'Authorization token is required'}, 401

    _register_error_safety_net(app)
    return app


# ---------- error safety net (QA D25) ----------
# Many routes return f"Failed to X: {error}" with status 500, which put database / Python internals in front of
# users (e.g. a psycopg2 message for a bad date). Readable messages ("Section already exists") are left alone;
# replies whose text looks internal are replaced, and the original goes to the server log.
import re as _re
GENERIC_SERVER_ERROR = "Something went wrong on the server. Please try again."
_INTERNAL_ERROR_TEXT = _re.compile(
    r"psycopg2|sqlalchemy|\(Background on this error|Traceback|time data .* does not match|unconverted data remains"
    r"|invalid literal for|object has no attribute|NoneType|\[Errno \d+\]|KeyError|IndexError|list index out of range"
    r"|could not convert|unsupported operand|unexpected keyword argument|required positional argument"
    r"|is not JSON serializable|SyntaxError|NameError|AttributeError|TypeError|ZeroDivisionError",
    _re.IGNORECASE,
)


def _register_error_safety_net(app):
    from flask import request, jsonify, json
    from werkzeug.exceptions import HTTPException

    @app.after_request
    def _hide_internal_error_text(response):
        if response.status_code < 500 or not response.is_json:
            return response
        data = response.get_json(silent=True)
        if not isinstance(data, dict):
            return response
        changed = False
        for key in ('message', 'error', 'detail'):
            value = data.get(key)
            if isinstance(value, str) and _INTERNAL_ERROR_TEXT.search(value):
                app.logger.error(f"{request.method} {request.path} -> {response.status_code}: {value}")
                data[key] = GENERIC_SERVER_ERROR
                changed = True
        if changed:
            response.set_data(json.dumps(data))
        return response

    @app.errorhandler(Exception)
    def _unhandled_error(error):
        # an error no route caught: a plain JSON reply instead of a stack trace / debugger page
        if isinstance(error, HTTPException):
            return error
        app.logger.exception(f"Unhandled error on {request.method} {request.path}")
        return jsonify({'status': 'error', 'code': 500, 'message': GENERIC_SERVER_ERROR}), 500


def _bootstrap_main_schema(app):
    """
    Ensure main-database tables/columns required by the migrated backend exist.
    This keeps fresh environments functional even without running migrations.
    """
    with app.app_context():
        import app.models  # noqa: F401 - registers model metadata

        # Old "school" names -> "institution" (tables, columns, types, role value). Must run BEFORE create_all,
        # which would otherwise create new empty tables next to the renamed ones. Does nothing once done.
        from app.utils.institution_rename import rename_database_objects
        with db.engine.begin() as conn:
            renamed = rename_database_objects(conn)
        if renamed:  # (not app.logger: "import app.models" above rebinds the name `app` to the package)
            logging.getLogger(__name__).warning(f"Main database renamed to institution names: {renamed}")

        db.create_all()

        # Backfill auth hardening columns for legacy users table schemas.
        db.session.execute(
            text(
                """
                ALTER TABLE IF EXISTS users
                ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER DEFAULT 0
                """
            )
        )
        db.session.execute(
            text(
                """
                ALTER TABLE IF EXISTS users
                ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP NULL
                """
            )
        )
        db.session.commit()

        # Login roles added after the users table was created (create_all doesn't alter an existing enum type)
        for role_value in ('CLERK',):
            db.session.execute(text(
                "DO $$ BEGIN "
                "IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userrole') THEN "
                f"ALTER TYPE userrole ADD VALUE IF NOT EXISTS '{role_value}'; "
                "END IF; END $$;"
            ))
            db.session.commit()

# Columns added to existing institution databases after they were created (create_all only builds new tables).
# Each statement must be safe to run on every start.
_OLD_PROGRESS = """
    SELECT p.*, a.section_id AS target_section
    FROM syllabus_progress_tracking p
    JOIN teacher_syllabus_assignments a ON a.teacher_id = p.teacher_id AND a.syllabus_id = (CASE p.item_type
              WHEN 'syllabus' THEN p.item_id
              WHEN 'lesson' THEN (SELECT l.syllabus_id FROM lessons l WHERE l.id = p.item_id)
              WHEN 'topic' THEN (SELECT l.syllabus_id FROM topics t JOIN lessons l ON l.id = t.lesson_id WHERE t.id = p.item_id)
              WHEN 'subtopic' THEN (SELECT l.syllabus_id FROM subtopics s JOIN topics t ON t.id = s.topic_id JOIN lessons l ON l.id = t.lesson_id WHERE s.id = p.item_id)
            END)
    WHERE p.section_id IS NULL AND p.is_active
"""
SYLLABUS_PROGRESS_CARRY_OVER = f"""
INSERT INTO syllabus_progress_tracking (teacher_id, section_id, item_type, item_id, planned_start_date, planned_end_date,
    actual_start_date, actual_end_date, planned_completion_date, actual_completion_date, status, completion_percentage,
    is_completed, teacher_notes, created_at, updated_at, is_active)
SELECT DISTINCT ON (o.target_section, o.item_type, o.item_id)
    o.teacher_id, o.target_section, o.item_type, o.item_id, o.planned_start_date, o.planned_end_date,
    o.actual_start_date, o.actual_end_date, o.planned_completion_date, o.actual_completion_date, o.status,
    o.completion_percentage, o.is_completed, o.teacher_notes, o.created_at, o.updated_at, TRUE
FROM ({_OLD_PROGRESS}) o
WHERE NOT EXISTS (SELECT 1 FROM syllabus_progress_tracking x WHERE x.section_id = o.target_section
                  AND x.item_type = o.item_type AND x.item_id = o.item_id AND x.is_active)
ORDER BY o.target_section, o.item_type, o.item_id,
    (o.is_completed OR o.status = 'completed') DESC, (o.status = 'in_progress') DESC,
    o.completion_percentage DESC, o.updated_at DESC
"""
SYLLABUS_PROGRESS_RETIRE_COPIED = f"""
UPDATE syllabus_progress_tracking SET is_active = FALSE
WHERE id IN (SELECT o.id FROM ({_OLD_PROGRESS}) o)
"""

# Homework AI used to call its homework "assignments" (it is not the Assignments feature): rename once.
HOMEWORK_TABLE_RENAME = """
DO $$
BEGIN
    IF to_regclass('homework_assignments') IS NOT NULL AND to_regclass('homeworks') IS NULL THEN
        ALTER TABLE homework_assignments RENAME TO homeworks;
        ALTER SEQUENCE IF EXISTS homework_assignments_id_seq RENAME TO homeworks_id_seq;
        ALTER INDEX IF EXISTS homework_assignments_pkey RENAME TO homeworks_pkey;
        ALTER INDEX IF EXISTS ix_homework_assignments_class_id RENAME TO ix_homeworks_class_id;
        ALTER INDEX IF EXISTS ix_homework_assignments_section_id RENAME TO ix_homeworks_section_id;
        ALTER INDEX IF EXISTS ix_homework_assignments_created_by RENAME TO ix_homeworks_created_by;
        ALTER INDEX IF EXISTS ix_homework_assignments_homework_date RENAME TO ix_homeworks_homework_date;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'student_homework_sessions' AND column_name = 'assignment_id') THEN
        ALTER TABLE student_homework_sessions RENAME COLUMN assignment_id TO homework_id;
        ALTER INDEX IF EXISTS ix_student_homework_sessions_assignment_id RENAME TO ix_student_homework_sessions_homework_id;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'student_homework_sessions_assignment_id_fkey') THEN
        ALTER TABLE student_homework_sessions RENAME CONSTRAINT student_homework_sessions_assignment_id_fkey
            TO student_homework_sessions_homework_id_fkey;
    END IF;
END $$;
"""

TENANT_SCHEMA_UPDATES = (
    "ALTER TABLE IF EXISTS attendance ADD COLUMN IF NOT EXISTS marked_by INTEGER",
    "ALTER TABLE IF EXISTS attendance ADD COLUMN IF NOT EXISTS updated_by INTEGER",
    # custom roles are "based on" a built-in staff role (QA A13); built-in roles are based on themselves
    "ALTER TABLE IF EXISTS roles ADD COLUMN IF NOT EXISTS base_role VARCHAR(50)",
    "UPDATE roles SET base_role = role_code WHERE base_role IS NULL AND role_code IN "
    "('INSTITUTION_ADMIN','PRINCIPAL','TEACHER','STUDENT','PARENT','BUS_STAFF','CLERK')",
    # built-in roles are marked as such (some institutions had Clerk / Bus Staff unmarked, so they could be deleted)
    "UPDATE roles SET is_system_role = TRUE WHERE is_system_role IS DISTINCT FROM TRUE AND role_code IN "
    "('INSTITUTION_ADMIN','PRINCIPAL','TEACHER','STUDENT','PARENT','BUS_STAFF','CLERK')",
    # syllabus progress is kept per section (QA B33)
    "ALTER TABLE IF EXISTS syllabus_progress_tracking ADD COLUMN IF NOT EXISTS section_id INTEGER "
    "REFERENCES sections(id) ON DELETE CASCADE",
    "CREATE INDEX IF NOT EXISTS ix_syllabus_progress_tracking_section_id ON syllabus_progress_tracking (section_id)",
    # carry-over: old progress (no section) is copied to every section its teacher was assigned to for that
    # syllabus, so each section starts out showing what it showed before; then the old row is retired.
    # Runs once in effect: it only touches active rows without a section whose teacher has an assignment.
    SYLLABUS_PROGRESS_CARRY_OVER,
    SYLLABUS_PROGRESS_RETIRE_COPIED,
    HOMEWORK_TABLE_RENAME,
    # paid / unpaid split of approved staff leave (leave balances)
    "ALTER TABLE IF EXISTS leave_requests ADD COLUMN IF NOT EXISTS paid_days INTEGER",
    "ALTER TABLE IF EXISTS leave_requests ADD COLUMN IF NOT EXISTS unpaid_days INTEGER",
    # approved leave recounted after a holiday / weekly-off change (holiday calendar)
    "ALTER TABLE IF EXISTS leave_requests ADD COLUMN IF NOT EXISTS recount_note VARCHAR(255)",
)


def _bootstrap_tenant_schemas(app):
    """Apply TENANT_SCHEMA_UPDATES to every institution's database. An institution that can't be reached is logged and skipped."""
    from app.models.main.Institution import Institution
    from app.utils.db_manager import switch_to_institution_db
    with app.app_context():
        try:
            skids = [s.skid for s in Institution.query.all() if s.skid]
        except Exception as e:  # main DB not ready: nothing to update yet
            app.logger.warning(f"Tenant schema update skipped: {e}")
            return
        # institution databases skool_<skid> -> eduspyre_<skid> (before anything connects to them; no-op once done)
        try:
            from app.utils.institution_rename import rename_tenant_databases
            with db.engine.connect().execution_options(isolation_level="AUTOCOMMIT") as admin_conn:
                renamed = rename_tenant_databases(admin_conn, skids)
            if renamed:
                app.logger.warning(f"Institution databases renamed: {renamed}")
        except Exception as e:
            app.logger.error(f"Renaming institution databases failed: {e}")
    for skid in skids:
        try:
            with switch_to_institution_db(skid) as session:  # one transaction per institution database
                # old "school" names -> "institution" first (tables, columns, admin role code); no-op once done
                from app.utils.institution_rename import rename_database_objects, rename_tenant_data
                conn = session.connection()
                renamed = rename_database_objects(conn) + rename_tenant_data(conn)
                if renamed:
                    app.logger.warning(f"Institution database {skid} renamed: {renamed}")
                for statement in TENANT_SCHEMA_UPDATES:
                    session.execute(text(statement))
                # tables added after the institution was created (create_all only runs for new institutions)
                from app.models.tenant.LeaveRequest import LeaveRequest
                from app.models.tenant.StaffAttendance import StaffAttendance
                from app.models.tenant.LeavePolicy import LeavePolicy
                from app.models.tenant.Holiday import Holiday, CalendarSetting
                from app.models.tenant.Event import Event
                from app.models.tenant.Substitution import Substitution
                LeaveRequest.__table__.create(bind=conn, checkfirst=True)
                StaffAttendance.__table__.create(bind=conn, checkfirst=True)
                LeavePolicy.__table__.create(bind=conn, checkfirst=True)
                Holiday.__table__.create(bind=conn, checkfirst=True)
                CalendarSetting.__table__.create(bind=conn, checkfirst=True)
                Event.__table__.create(bind=conn, checkfirst=True)
                Substitution.__table__.create(bind=conn, checkfirst=True)
        except Exception as e:
            app.logger.warning(f"Tenant schema update failed for institution {skid}: {str(e).splitlines()[0]}")


def setup_logging(app):
    if not os.path.exists('logs'):
        os.mkdir('logs')

    file_handler = RotatingFileHandler(
        app.config['LOG_FILE'],
        maxBytes=10240000,
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))

    log_level = logging.DEBUG if app.debug else logging.INFO
    file_handler.setLevel(log_level)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(log_level)
    app.logger.info('Institution Management System startup')