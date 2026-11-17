# School Management System Backend

A comprehensive Flask-based backend system for managing multiple schools with role-based access control and multi-tenant architecture.

## Features

- **Multi-tenant Architecture**: Separate database for each school
- **Role-based Access Control**: Super Admin, School Admin, Principal, Teacher, Student, Parent
- **JWT Authentication**: Secure authentication with refresh tokens
- **Session Management**: Track user login/logout sessions
- **Comprehensive Logging**: Action logging with IP tracking
- **RESTful API**: Well-structured API endpoints
- **Database Management**: Automated database creation and migration

## Tech Stack

- **Backend**: Python Flask
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **Authentication**: Flask-JWT-Extended
- **Migrations**: Flask-Migrate
- **CORS**: Flask-CORS

## First time migrations run
alembic init migrations_main
alembic init migrations_tenant


## Project Structure

```
school_management_backend/
│
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── models/                  # Database models
│   │   ├── __init__.py
│   │   ├── base.py
|   │   ├── main/
│   │       ├── School.py           # Base model with common fields
│   │       ├── User.py             # User model 
│   │       ├── UserSession.py      # School model
|   │   ├── tenant/
|   |       ├── __init__.py           
|   |       ├── Student.py           
|   |       ├── Teacher.py           
|   |       ├── Roles.py             
│   │       └── SchoolUsers.py     
│   ├── api/                     # API endpoints
│   │   ├── __init__.py
│   │   ├── auth.py             # Authentication endpoints
│   │   └── user.py             # User management endpoints
|   |   |__ school.py            # school management endpoints
│   ├── decorators/              # Custom decorators
│   │   ├── __init__.py
│   │   ├── auth.py             # Authentication decorators
│   │   └── logging.py          # Logging decorators
│   ├── services/                # Business logic
│   │   ├── __init__.py
│   │   ├── auth_service.py     # Authentication service
│   │   └── user_service.py     # User service
|   |   |__ school_service.py   # school service
│   └── utils/                   # Utility functions
│       ├── __init__.py
│       ├── database.py         # Database utilities
│       └── helpers.py          # Helper functions
│
├── logs/                       # Application logs
├── config.py                   # Configuration settings
├── run.py                      # Application runner
├── create_admin.py             # Script to create super admin
├── requirements.txt            # Python dependencies
├── run-upgrade_db.bat              # Database upgrade script
├── .env                        # Environment variables
└── README.md                   # This file
```

## User Roles

1. **Super Admin**: Manages all schools, creates school admins
2. **School Admin**: Manages specific school, creates users within school
3. **Principal**: School admin features + timetable management
4. **Teacher**: Manages classes, assignments, progress reports
5. **Student**: Views timetable, assignments, submits work
6. **Parent**: Views child's progress, communicates with teachers

## Setup Instructions

### Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd school_management_backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On Unix/MacOS
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Setup environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

5. **Setup PostgreSQL**
   - Create a PostgreSQL database for super admin - skool_main
   - Update database credentials in `.env`

6. **Initialize database for main db**
   - run-main_dbupgrade.bat
   
7. **Create super admin**
   ```bash
   python create_admin.py
   ```

8. **Run the application**
   ```bash
   python run.py
   ```
## For tenant migrations follow the steps
   - Initially the school db will be created in the database
   - Create Versions Folder in the migrations_tenant folder if not present
   - Replace one tenant db name in the db-url present in the env.py of migrations_tenant folder
   - run-tenant_dbupgrade only if needed to upgrade the db, because the schema will be created automatically while creating a school.


## Multi-Tenant Architecture

Each school has its own database, created automatically when a new school is registered:

1. **Super Admin Database**: Contains schools and super admin users
2. **School Databases**: Individual databases for each school (school_ABC123, school_XYZ456, etc.)

### Database Naming Convention
- Super Admin DB: `skool_main`
- School DBs: `school_{school_code}` (e.g., `school_abc123`)

## Security Features

- **Password Hashing**: Using Werkzeug's secure password hashing
- **JWT Tokens**: Access and refresh token system
- **Session Tracking**: Complete session management with logout tracking
- **Role-based Access**: Granular permission system
- **Input Validation**: Comprehensive input sanitization
- **SQL Injection Protection**: Parameterized queries with SQLAlchemy
- **CORS Protection**: Configurable CORS settings

## Logging

The system provides comprehensive logging:

- **Authentication Events**: Login/logout attempts with IP tracking
- **User Actions**: All CRUD operations with user context
- **Error Tracking**: Detailed error logs with stack traces
- **Session Management**: Session creation and termination logs

Log files are stored in the `logs/` directory.

## Environment Variables

Create a `.env` file based on `.env.example`:

```env
FLASK_ENV=development
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
SUPER_ADMIN_DATABASE_URL=postgresql://user:pass@localhost/skool_main
```

## Development

### Running in Development Mode
```bash
export FLASK_ENV=development
export FLASK_DEBUG=True
python run.py
```

## Production Deployment

1. **Environment Setup**
   - Set `FLASK_ENV=production`
   - Use strong secret keys
   - Configure production database

2. **Security**
   - Use HTTPS
   - Set secure CORS origins
   - Configure firewall rules
   - Regular security updates

3. **Database**
   - Use managed PostgreSQL service
   - Setup regular backups
   - Monitor performance

4. **Monitoring**
   - Setup log aggregation
   - Monitor API performance
   - Track user activities

## Future Enhancements

- Email notifications
- File upload management
- Advanced reporting
- API rate limiting
- Audit trails
- Data export features
- Mobile app support

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support and questions:
- Create an issue in the repository
- Check the documentation
- Review the API examples




project progress:

- virtual env created
- installed requirements

pending
- main database creation 