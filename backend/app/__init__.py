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
    
    # Setup logging
    # setup_logging(app)
    
    # Register blueprints
    from app.api import (
        auth_bp, user_bp, teacher_bp, student_bp, school_bp, class_bp, subject_bp, attendance_bp,
        parent_bp, roles_bp, user_roles_bp, timeTable_bp, studentParent_bp, fee_bp, announcement_bp,
        school_admin_dashboard_bp, exam_bp, marks_bp, progress_card_bp, expense_bp, academic_year_bp,
        teacher_dashboard_bp, syllabus_bp, assignment_bp, student_dashboard_bp, room_bp, seating_bp,
        bus_scan_bp, staff_bp
    )
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(user_bp, url_prefix='/api/users')
    app.register_blueprint(teacher_bp, url_prefix='/api/teachers')
    app.register_blueprint(student_bp, url_prefix='/api/students')
    app.register_blueprint(parent_bp, url_prefix='/api/parents')
    app.register_blueprint(studentParent_bp, url_prefix='/api/studentParent')
    app.register_blueprint(school_bp, url_prefix='/api/school')
    app.register_blueprint(class_bp, url_prefix='/api/classes')
    app.register_blueprint(subject_bp, url_prefix='/api/subjects')
    app.register_blueprint(attendance_bp, url_prefix='/api/attendance')
    app.register_blueprint(timeTable_bp, url_prefix='/api/timeTable')
    app.register_blueprint(fee_bp, url_prefix='/api/fee')
    app.register_blueprint(roles_bp, url_prefix='/api/roles')
    app.register_blueprint(user_roles_bp, url_prefix='/api/user-roles')
    app.register_blueprint(announcement_bp, url_prefix='/api/announcements')
    app.register_blueprint(school_admin_dashboard_bp, url_prefix='/api/schoolAdminDashboard')
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
    
    return app

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
    app.logger.info('School Management System startup')