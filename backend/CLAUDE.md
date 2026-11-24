# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is the **Institution Management System Backend**, a Flask-based REST API implementing a multi-tenant architecture where each institution has its own PostgreSQL database. The system supports role-based access control with seven user roles: Super Admin, Institution Admin, Principal, Teacher, Student, Parent, and Bus Staff.

## Technology Stack

- **Framework:** Flask 2.3.3
- **Database:** PostgreSQL (main database + per-tenant databases)
- **ORM:** SQLAlchemy 2.0.21
- **Migrations:** Flask-Migrate 4.0.5 + Alembic
- **Authentication:** Flask-JWT-Extended 4.5.3 (1-hour access tokens, 30-day refresh tokens)
- **CORS:** Flask-CORS 4.0.0
- **Production Server:** Gunicorn 22.0.0
- **Real-time:** Socket.io (Flask-SocketIO) — bus location broadcasts

## Common Commands

### Initial Setup
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env  # update database credentials

# Initialize main database
# Windows
run-main_dbupgrade.bat
# Linux/Mac
./run-main_dbupgrade.sh

# Create super admin user (interactive prompt)
python create_admin.py
```

### Running the Application
```bash
# Development mode (debug enabled, hot-reload)
python run.py

# Production mode
gunicorn --workers 4 --bind 0.0.0.0:5000 "app:create_app()"
# or use production script
./run-production.sh  # Linux/Mac
```

### Database Migrations

**Main Database (`eduspyre_main`):**
```bash
alembic -c migrations_main/alembic_main.ini revision --autogenerate -m "description"
# Windows
run-main_dbupgrade.bat
# Linux/Mac
./run-main_dbupgrade.sh
```

**Tenant Databases (per-institution):**
```bash
alembic -c migrations_tenant/alembic_tenant.ini revision --autogenerate -m "description"
# Windows
run-tenant_dbupgrade.bat
# Linux/Mac
./run-tenant_dbupgrade.sh
```
> Tenant schemas are auto-created when an institution registers. Only run tenant migrations to update existing tenants.

## Multi-Tenant Architecture

**Database-per-tenant model:**

1. **Main Database** (`eduspyre_main`) — Central repository:
   - Institutions registry (`institution_code`, `institution_name`, etc.)
   - Super admin users
   - User sessions with IP tracking

2. **Tenant Databases** (`eduspyre_{institution_code}`) — One per institution:
   - Auto-created on institution registration
   - Contains all institution data: students, teachers, classes, attendance, timetables, fees, exams, marks, syllabus, assignments, bus scans, rooms, seating, etc.
   - Fully isolated from other institutions

3. **Tenant Switching:** `app/utils/tenant_db.py` switches the database connection per request based on authenticated user's institution.

**Key files:**
- `app/utils/tenant_db.py` — connection switching
- `app/utils/db_manager.py` — tenant DB creation/deletion
- `app/utils/tenant_migration.py` — applies migrations to new tenants
- `app/utils/seeders.py` — seeds default data (roles, academic years)

## Directory Structure

```
app/
├── __init__.py              # Flask app factory (create_app)
├── api/                     # RESTful API route handlers
│   ├── auth.py             # Login, logout, token refresh
│   ├── user.py             # User management
│   ├── institution.py           # Institution management (Super Admin)
│   ├── teacher.py          # Teacher CRUD
│   ├── student.py          # Student CRUD
│   ├── parent.py           # Parent CRUD
│   ├── studentParent.py    # Student-parent link management
│   ├── classes.py          # Class/section management
│   ├── subject.py          # Subject management
│   ├── attendance.py       # Attendance tracking
│   ├── timeTable.py        # Timetable builder and queries
│   ├── exam_routes.py      # Exam types and subject configs
│   ├── marks_routes.py     # Marks entry and retrieval
│   ├── fee.py              # Fee structures and collection
│   ├── expense_routes.py   # Expense tracking
│   ├── announcement.py     # Institution announcements
│   ├── progress_card_routes.py  # Progress card generation
│   ├── academic_year.py    # Academic year management
│   ├── syllabus.py         # Syllabus, topics, subtopics, progress tracking
│   ├── assignment.py       # Assignment creation and submissions
│   ├── bus_location.py     # Bus GPS location (REST fallback + stop)
│   ├── bus_scan.py         # Bus QR scan boarding/exit records
│   ├── room_routes.py      # Exam room management
│   ├── seating_routes.py   # Seating arrangement per room
│   ├── staff_routes.py     # Institution staff (non-teacher) management
│   ├── roles.py            # Role definitions and permissions
│   ├── userRoles.py        # User-role assignments
│   ├── teacher_dashboard_routes.py       # Teacher dashboard data
│   ├── institution_admin_dashboard_routes.py  # Admin dashboard data
│   └── student_dashboard_routes.py       # Student dashboard data
├── models/
│   ├── base.py             # Base model classes
│   ├── main/               # Main database models
│   │   ├── Institution.py
│   │   ├── User.py
│   │   └── UserSession.py
│   └── tenant/             # Per-institution models
│       ├── AcademicYear.py
│       ├── Announcement.py
│       ├── Assignment.py
│       ├── AssignmentSubmission.py
│       ├── Attendance.py
│       ├── BusLocation.py          # Live GPS position per bus (skid)
│       ├── BusScan.py              # Boarding/exit scan records
│       ├── Class.py
│       ├── ExamModels.py
│       ├── ExpenseModels.py
│       ├── FeeModels.py
│       ├── Lesson.py
│       ├── MarksModels.py
│       ├── Parent.py
│       ├── PromotionHistory.py
│       ├── Roles.py
│       ├── Room.py                 # Exam rooms
│       ├── InstitutionAdmin.py
│       ├── InstitutionUsers.py
│       ├── SeatingArrangement.py   # Student seating per room/exam
│       ├── SectionSubject.py
│       ├── Sections.py
│       ├── Staff.py
│       ├── Student.py
│       ├── StudentEnrollment.py
│       ├── StudentParent.py
│       ├── Subject.py
│       ├── Subtopic.py
│       ├── Syllabus.py
│       ├── SyllabusProgressTracking.py
│       ├── Teacher.py
│       ├── TeacherSubject.py
│       ├── TeacherSyllabusAssignment.py
│       ├── TimeTable.py
│       ├── TimeTableEntry.py
│       ├── Topic.py
│       └── UserRoles.py
├── services/               # Business logic layer
│   ├── auth_service.py
│   ├── user_service.py
│   ├── institution_service.py
│   ├── student_service.py
│   ├── teacher_service.py
│   ├── parent_service.py
│   ├── studentParent_service.py
│   ├── class_service.py
│   ├── subject_service.py
│   ├── attendance_service.py
│   ├── timeTable_service.py
│   ├── exam_service.py
│   ├── marks_service.py
│   ├── fee_service.py
│   ├── expense_service.py
│   ├── announcement_service.py
│   ├── progress_card_service.py
│   ├── academic_year_service.py
│   ├── syllabus_service.py
│   ├── assignment_service.py
│   ├── bus_location_service.py
│   ├── bus_scan_service.py
│   ├── room_service.py
│   ├── seating_service.py
│   ├── staff_service.py
│   ├── roles_service.py
│   ├── userRole_service.py
│   ├── teacher_dashboard_service.py
│   ├── institution_admin_dashboard_service.py
│   └── student_dashboard_service.py
├── decorators/
│   ├── auth.py            # @login_required, @super_admin_required, etc.
│   └── logging.py         # @log_login_attempt, @log_logout, @log_actions
└── utils/
    ├── tenant_db.py
    ├── db_manager.py
    ├── db_name_generator.py
    ├── tenant_migration.py
    ├── seeders.py
    └── helpers.py

migrations_main/            # Alembic migrations — main database
migrations_tenant/          # Alembic migrations — tenant databases
config.py                   # Flask configuration
run.py                      # App entry point
create_admin.py            # Script to create super admin
requirements.txt
.env                       # Not in git
```

## Architecture Patterns

### Service Layer Pattern
```
HTTP Request → API Route (app/api/) → Service (app/services/) → Model/DB → Response
```
- Routes parse requests and call services
- Services contain pure business logic
- Models handle DB operations

### Authentication & Authorization

**Decorators in `app/decorators/auth.py`:**
- `@login_required(allowed_roles=[...])` — validates JWT, checks role
- `@super_admin_required` — super admin only
- `@institution_admin_required` — institution admin or higher
- `@teacher_required` — teacher or higher
- `@same_institution_required` — prevents cross-institution data access

```python
@blueprint.route('/api/example', methods=['GET'])
@login_required(allowed_roles=['TEACHER', 'INSTITUTION_ADMIN'])
def example():
    user = request.current_user   # attached by decorator
    return jsonify(result)
```

**JWT details:**
- Header: `Authorization: Bearer <token>`
- Access tokens: 1 hour (24 hours in development)
- Refresh tokens: 30 days

### Real-time: Bus Location (Socket.io)
- Bus staff app emits `bus_location_update` events via WebSocket
- Server broadcasts to parent clients subscribed to that bus's room
- REST fallback: `POST /api/bus-location/update/<skid>` when WebSocket unavailable
- Stop endpoint: `POST /api/bus-location/stop/<skid>`

### skid (Institution User ID)
Many routes are scoped by `skid` — the institution-specific user identifier (not the global user ID). It appears in URL paths: `/api/assignments/create/<skid>`, `/api/bus-location/update/<skid>`, etc.

## User Roles & Access Control

Seven roles:

| Role | Access | Scope |
|---|---|---|
| `SUPER_ADMIN` | Manage institutions, create institution admins | Main DB only |
| `INSTITUTION_ADMIN` | All institution operations, user management | Tenant DB |
| `PRINCIPAL` | All admin features + timetable approval | Tenant DB |
| `TEACHER` | Attendance, marks, assignments, syllabus | Assigned classes only |
| `STUDENT` | View timetable, assignments, marks | Own data only |
| `PARENT` | View child data, bus location, fees | Linked children only |
| `BUS_STAFF` | Push GPS location, QR scan boarding/exit | Assigned bus |

Role check pattern:
```python
user_role = request.current_user.role.value
if user_role not in allowed_roles:
    return jsonify({'message': 'Insufficient permissions'}), 403
```

## Key Configuration

**`.env` Environment Variables:**
```env
FLASK_ENV=development
FLASK_DEBUG=True
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
SECRET_KEY=...
JWT_SECRET_KEY=...
SUPER_ADMIN_DATABASE_URL=postgresql://user:pass@localhost:5432/eduspyre_main
POSTGRES_HOST=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_PORT=5432
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

## Common Development Tasks

### Adding a New API Endpoint

1. **Service** in `app/services/something_service.py`:
```python
class SomethingService:
    @staticmethod
    def create_something(skid, data):
        # business logic
        return result
```

2. **Route** in `app/api/something.py`:
```python
from flask import Blueprint, request, jsonify
from app.decorators.auth import login_required
from app.services.something_service import SomethingService

something_bp = Blueprint('something', __name__)

@something_bp.route('/create/<skid>', methods=['POST'])
@login_required(['TEACHER', 'INSTITUTION_ADMIN'])
def create(skid):
    data = request.get_json()
    result = SomethingService.create_something(skid, data)
    return jsonify(result), 201
```

3. **Register blueprint** in `app/__init__.py`:
```python
from app.api.something import something_bp
app.register_blueprint(something_bp, url_prefix='/api/something')
```

### Adding a Tenant Model

1. Define in `app/models/tenant/Something.py`
2. Create migration: `alembic -c migrations_tenant/alembic_tenant.ini revision --autogenerate -m "add something"`
3. Apply: `./run-tenant_dbupgrade.sh`

## Important Notes

- **Never hardcode database names** — use `db_name_generator.py` with `institution_code`
- **Always use `@same_institution_required`** to prevent cross-tenant data leakage
- **Password hashing** — always use Werkzeug's `generate_password_hash()` / `check_password_hash()`
- **Main vs Tenant models** — `app/models/main/` (global) vs `app/models/tenant/` (per-institution)
- **Access tokens** — short-lived (1 hour); refresh tokens — long-lived (30 days)
- **Never log sensitive data** — use `app.logger` for events only
- **CORS** — currently `origins: "*"`; restrict to specific domains in production
- **`skid` in routes** — institution-scoped user ID; used throughout tenant API URLs
- **Migrations are auto-applied** when new institutions register via `tenant_migration.py`
