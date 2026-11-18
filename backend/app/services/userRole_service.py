from app import db
from app.models.main.User import User
from app.models.tenant import SchoolUsers
from app.models.tenant.Roles import Role
from app.models.tenant.UserRoles import UserRoles 
from app.utils.db_manager import switch_to_school_db
from sqlalchemy.exc import SQLAlchemyError  

class UserRolesService:

    @staticmethod
    def assign_role_to_user(data, skid):
        """
        Assign a role to a user in the specific school database.
        """
        try:
            user_id = data.get("user_id")
            role_id = data.get("role_id")
            assigned_by = data.get("assigned_by")
            update_main_db = data.get("update_main_db", True)  # Default True for backward compatibility

            if not user_id or not role_id:
                raise ValueError("Both user_id and role_id are required")

            with switch_to_school_db(skid) as tenant_session:
                # Check if the user-role combination already exists
                existing = tenant_session.query(UserRoles).filter_by(user_id=user_id, role_id=role_id).first()

                if existing:
                    if not existing.is_active:
                        existing.is_active = True
                        existing.assigned_by = assigned_by
                        tenant_session.commit()
                    return {"message": "Role already assigned", "user_id": user_id, "role_id": role_id}

                # Assign new role
                new_user_role = UserRoles(
                    user_id=user_id,
                    role_id=role_id,
                    assigned_by=assigned_by,
                    is_active=True
                )
                tenant_session.add(new_user_role)
                tenant_session.commit()
                
                # Now, update the role_id in the school_users table
                school_user = tenant_session.query(SchoolUsers).get(user_id)
                if not school_user:
                    raise ValueError(f"User with ID {user_id} not found in school database.")
                
                school_user.role_id = role_id
                tenant_session.add(school_user)
                tenant_session.commit()
                
                # Only update main DB if flag is True
                if update_main_db:
                    # Fetch the role code to assign in the main-db user table
                    role_obj = tenant_session.query(Role).get(role_id)
                    if not role_obj:
                        raise ValueError(f"Role with ID {role_id} not found in tenant database.")
    
                    # Find the corresponding user in the main database
                    main_user = db.session.query(User).filter_by(skid=skid, school_user_id=str(user_id)).first()
                    if not main_user:
                        raise ValueError(f"User with skid {skid} and school_user_id {user_id} not found in main database.")
                    
                    # Update the role in the main User table
                    main_user.role = role_obj.role_code
                    db.session.add(main_user)
                    db.session.commit()
                
                return {
                    "user_id": user_id,
                    "role_id": role_id,
                    "assigned_by": assigned_by,
                    "message": "Role successfully assigned"
                }

        except SQLAlchemyError as e:
            raise Exception(f"Database error: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to assign role: {str(e)}")
