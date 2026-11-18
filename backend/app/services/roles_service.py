from app import db
from app.models.tenant.Roles import Role
from app.utils.db_manager import switch_to_school_db


class RolesService:

    @staticmethod
    def create_role(data, skid):
        try:
            with switch_to_school_db(skid) as tenant_session:
                if data.get('role_code'):
                    existing_role = tenant_session.query(Role).filter_by(
                        role_code=data['role_code']
                    ).first()
                    if existing_role:
                        raise ValueError(f"Role code '{data['role_code']}' already exists")

                new_role = Role(
                    role_name=data['role_name'],
                    role_code=data.get('role_code'),
                    description=data.get('description')
                )
                tenant_session.add(new_role)
                tenant_session.commit()
                tenant_session.refresh(new_role)
                return new_role.to_dict()

        except Exception as e:
            raise Exception(f"Failed to create role: {str(e)}")

    @staticmethod
    def update_role(role_id, data, skid):
        try:
            with switch_to_school_db(skid) as tenant_session:
                role = tenant_session.query(Role).get(role_id)
                if not role:
                    raise ValueError("Role not found")

                role.role_name = data.get('role_name', role.role_name)
                role.description = data.get('description', role.description)
                tenant_session.commit()
                return role.to_dict()

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
    
                role.is_active = not role.is_active

                tenant_session.commit()
                return role.to_dict()

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

                tenant_session.delete(role)
                tenant_session.commit()
                return {"message": "Role deleted successfully"}

        except Exception as e:
            raise Exception(f"Failed to delete role: {str(e)}")
