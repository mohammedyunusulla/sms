from app import db
from app.models.tenant.Roles import Role
from app.utils.db_manager import switch_to_school_db

# Built-in roles (stored on login accounts); a custom role must be based on one of the staff ones
BUILT_IN_ROLES = ('SCHOOL_ADMIN', 'PRINCIPAL', 'TEACHER', 'STUDENT', 'PARENT', 'BUS_STAFF', 'CLERK')
CUSTOM_ROLE_BASES = ('PRINCIPAL', 'CLERK', 'BUS_STAFF')


def _base_role(value):
    base = str(value or '').strip().upper()
    if base not in CUSTOM_ROLE_BASES:
        raise ValueError("Choose what the role is based on: Principal, Clerk or Bus Staff")
    return base


def _is_built_in(role):
    """Built-in roles (School Admin, Principal, Teacher, Student, Parent, Bus Staff, Clerk): only their permissions change."""
    return bool(role.is_system_role) or str(role.role_code or '').upper() in BUILT_IN_ROLES


BUILT_IN_ONLY_PERMISSIONS = "is a built-in role: only its permissions can be changed"


def _role_holders(tenant_session, role_id):
    from app.models.tenant.SchoolUsers import SchoolUsers
    from app.models.tenant.UserRoles import UserRoles
    holders = {uid for (uid,) in tenant_session.query(SchoolUsers.id).filter(SchoolUsers.role_id == role_id)}
    holders |= {uid for (uid,) in tenant_session.query(UserRoles.user_id).filter(UserRoles.role_id == role_id)}
    return holders


class RolesService:

    @staticmethod
    def create_role(data, skid):
        try:
            with switch_to_school_db(skid) as tenant_session:
                role_code = str(data.get('role_code') or '').strip().upper()
                if not role_code:
                    raise ValueError("Role code is required")
                if not str(data.get('role_name') or '').strip():
                    raise ValueError("Role name is required")
                if tenant_session.query(Role).filter_by(role_code=role_code).first():
                    raise ValueError(f"Role code '{role_code}' already exists")
                if role_code in BUILT_IN_ROLES or role_code == 'SUPER_ADMIN':
                    raise ValueError(f"'{role_code}' is a built-in role code; choose another")

                new_role = Role(
                    role_name=data['role_name'].strip(),
                    role_code=role_code,
                    description=data.get('description'),
                    base_role=_base_role(data.get('base_role')),
                    is_system_role=False,
                )
                tenant_session.add(new_role)
                tenant_session.commit()
                tenant_session.refresh(new_role)
                return new_role.to_dict()

        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to create role: {str(e)}")

    @staticmethod
    def update_role(role_id, data, skid):
        try:
            with switch_to_school_db(skid) as tenant_session:
                role = tenant_session.query(Role).get(role_id)
                if not role:
                    raise ValueError("Role not found")

                if _is_built_in(role):
                    # owner's rule: a built-in role keeps its name, description and base; only the tick boxes change
                    renamed = 'role_name' in data and (data.get('role_name') or '').strip() != (role.role_name or '')
                    redescribed = 'description' in data and (data.get('description') or '') != (role.description or '')
                    if renamed or redescribed:
                        raise ValueError(f"'{role.role_name}' {BUILT_IN_ONLY_PERMISSIONS}")
                    return role.to_dict()

                role.role_name = data.get('role_name', role.role_name)
                role.description = data.get('description', role.description)
                if data.get('base_role') is not None and not role.is_system_role:
                    base = _base_role(data['base_role'])
                    if base != role.base_role and _role_holders(tenant_session, role.id):
                        # their login accounts carry the old base: changing it here would make them disagree
                        raise ValueError(f"'{role.role_name}' is assigned to people, so what it's based on can't change. "
                                         "Create a new role instead.")
                    role.base_role = base
                tenant_session.commit()
                return role.to_dict()

        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to update role: {str(e)}")

    @staticmethod
    def assign_permissions(skid, role_id, permissions):
        try:
            with switch_to_school_db(skid) as tenant_session:
                role = tenant_session.query(Role).get(role_id)
                if not role:
                    raise ValueError("Role not found")

                role.permissions = permissions
                tenant_session.commit()
                from app.utils.role_permissions import forget_cached_permissions
                forget_cached_permissions(skid)  # the server uses the new tick boxes straight away
                return role.to_dict()

        except Exception as e:
            raise Exception(f"Failed to assign permissions: {str(e)}")

    @staticmethod
    def toggle_role_status(role_id, skid):
        try:
            with switch_to_school_db(skid) as tenant_session:
                role = tenant_session.query(Role).get(role_id)
                if not role:
                    raise ValueError("Role not found")
    
                if _is_built_in(role):
                    raise ValueError(f"'{role.role_name}' {BUILT_IN_ONLY_PERMISSIONS} (it can't be switched off)")
                role.is_active = not role.is_active

                tenant_session.commit()
                from app.utils.role_permissions import forget_cached_permissions
                forget_cached_permissions(skid)
                return role.to_dict()

        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to toggle role status: {str(e)}")

    @staticmethod
    def get_all_roles_paginated(skid, page=1, limit=10, search='', status=''):
        """
        Get paginated list of roles with filtering
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Base query
                query = tenant_session.query(Role)

                # Apply filters
                if search:
                    search_term = f"%{search}%"
                    query = query.filter(Role.role_name.ilike(search_term))

                if status:
                    query = query.filter(Role.is_active == (status.lower() == 'active'))

                # Get total count before pagination
                total = query.count()

                # Apply pagination
                offset = (page - 1) * limit
                roles_data = query.offset(offset).limit(limit).all()

                role_list = [role.to_dict() for role in roles_data]

                # Calculate total pages
                total_pages = (total + limit - 1) // limit

                return {
                    'data': role_list,
                    'meta': {
                        'total': total,
                        'page': page,
                        'limit': limit,
                        'totalPages': total_pages
                    }
                }

        except Exception as e:
            raise Exception(f"Failed to fetch roles: {str(e)}")

    @staticmethod
    def get_all_roles(skid):
        try:
            with switch_to_school_db(skid) as tenant_session:
                Roles = tenant_session.query(Role).all()
                return [role.to_dict() for role in Roles]

        except Exception as e:
            raise Exception(f"Failed to fetch Role: {str(e)}")

    @staticmethod
    def get_role_by_id(role_id, skid):
        try:
            with switch_to_school_db(skid) as tenant_session:
                role = tenant_session.query(Role).get(role_id)
                if not role:
                    raise ValueError("Role not found")
                return role.to_dict()

        except Exception as e:
            raise Exception(f"Failed to fetch role: {str(e)}")

    @staticmethod
    def delete_role(role_id, skid):
        try:
            with switch_to_school_db(skid) as tenant_session:
                role = tenant_session.query(Role).get(role_id)
                if not role:
                    raise ValueError("Role not found")
                # Built-in roles (Principal, Teacher, Student, Parent, Bus Staff, Clerk, ...) are what accounts are
                # created with, and a role people hold can't go either (it used to delete anything, QA A14)
                if _is_built_in(role):
                    raise ValueError(f"'{role.role_name}' is a built-in role and can't be deleted. You can change its permissions instead.")
                holders = _role_holders(tenant_session, role.id)
                if holders:
                    count = len(holders)
                    raise ValueError(f"'{role.role_name}' is assigned to {count} {'person' if count == 1 else 'people'}. "
                                     "Give them another role first.")

                tenant_session.delete(role)
                tenant_session.commit()
                return {"message": "Role deleted successfully"}

        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to delete role: {str(e)}")
