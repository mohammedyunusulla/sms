# utils/seeders.py

from app.models.tenant.Roles import Role
from app.models.main.User import UserRole  # your Enum

def seed_default_roles(session, school_id=None):
    """
    Insert default roles into the tenant DB's `roles` table.
    """
    existing_roles = session.query(Role.role_code).all()
    existing_codes = {r[0] for r in existing_roles}

    new_roles = []

    for role_enum in UserRole:
        if role_enum.value not in existing_codes and role_enum.value !="SUPER_ADMIN":
            new_roles.append(
                Role(
                    role_name=role_enum.value.replace("_", " ").title(),  # e.g. SCHOOL_ADMIN → School Admin
                    role_code=role_enum.value, 
                    is_system_role=True,
                    is_active=True,
                    school_id=school_id
                )
            )
    
    if new_roles:
        session.add_all(new_roles)
        session.commit()
