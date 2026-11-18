from app.models.main.User import User, UserRole
from app.models.main.School import School
from app.models.tenant import SchoolUsers
from app.models.tenant.Roles import Role
from app.models.tenant.Staff import Staff
from app.models.tenant.UserRoles import UserRoles
from app import db
from app.utils.db_manager import switch_to_school_db

# Roles NOT handled by this service — they have dedicated creation flows
EXCLUDED_ROLES = {'TEACHER', 'STUDENT', 'PARENT', 'SUPER_ADMIN', 'SCHOOL_ADMIN'}


class StaffService:

    @staticmethod
    def create_staff(data, skid):
        """
        Create a school user for any role except TEACHER, STUDENT, PARENT.
        Supports: SCHOOL_ADMIN, PRINCIPAL, BUS_STAFF, and any custom roles.

        Required fields in `data`:
            username, email, password, first_name, last_name, role

        Optional:
            phone, designation, employee_id
        """
        required = ['username', 'email', 'password', 'first_name', 'last_name', 'role']
        for field in required:
            if not data.get(field):
                raise ValueError(f"Missing required field: {field}")

        role_code = data['role'].upper()
        if role_code in EXCLUDED_ROLES:
            raise ValueError(
                f"Role '{role_code}' cannot be created through this endpoint. "
                "Use the dedicated Teacher / Student / Parent creation forms."
            )

        school = School.query.filter_by(skid=skid).first()
        if not school:
            raise ValueError("School not found")

        # Uniqueness checks in main DB
        if User.get_by_username(data['username']):
            raise ValueError("Username already exists")
        if User.get_by_email(data['email']):
            raise ValueError("Email already exists")

        # Validate role exists in the UserRole enum
        try:
            user_role_enum = UserRole(role_code)
        except ValueError:
            raise ValueError(f"Unknown role '{role_code}'")

        # ── Step 1: create main DB user ──────────────────────────────────────
        user = User(
            username=data['username'],
            email=data['email'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            phone=data.get('phone'),
            role=user_role_enum,
            skid=skid,
            school_id=school.id,
        )
        user.set_password(data['password'])
        db.session.add(user)
        db.session.flush()

        # ── Step 2: create tenant-DB records ─────────────────────────────────
        with switch_to_school_db(skid) as session:
            # Look up the role record in the tenant DB
            role_obj = session.query(Role).filter_by(role_code=role_code).first()
            if not role_obj:
                raise ValueError(
                    f"Role '{role_code}' not found in school database. "
                    "Run the seeder / migrations to populate roles."
                )

            # Create SchoolUsers entry
            school_user = SchoolUsers(
                username=data['username'],
                email=data['email'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                phone=data.get('phone'),
                skid=skid,
                role_id=role_obj.id,
                is_active=True,
            )
            session.add(school_user)
            session.flush()

            # Create UserRoles entry
            user_role = UserRoles(
                user_id=school_user.id,
                role_id=role_obj.id,
                is_active=True,
            )
            session.add(user_role)

            # All staff roles (PRINCIPAL, BUS_STAFF, custom) get a Staff profile
            employee_id = (
                data.get('employee_id')
                or f"{role_code[:3]}-{skid}-{school_user.id}"
            )
            profile = Staff(
                user_id=school_user.id,
                employee_id=employee_id,
                designation=data.get('designation', role_code.replace('_', ' ').title()),
                salary=data.get('salary'),
                qualifications=data.get('qualifications'),
                date_of_joining=data.get('date_of_joining'),
            )
            session.add(profile)

            session.commit()
            user.school_user_id = school_user.id

        db.session.commit()
        return user

    @staticmethod
    def get_staff_list(skid):
        """Return all active non-student/teacher/parent users for a school."""
        with switch_to_school_db(skid) as session:
            excluded = list(EXCLUDED_ROLES)
            staff = (
                session.query(SchoolUsers)
                .join(Role, SchoolUsers.role_id == Role.id)
                .filter(
                    SchoolUsers.is_active == True,
                    Role.role_code.notin_(excluded),
                )
                .order_by(SchoolUsers.first_name, SchoolUsers.last_name)
                .all()
            )
            return [s.to_dict() for s in staff]
