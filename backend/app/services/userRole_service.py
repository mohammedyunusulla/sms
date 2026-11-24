from app import db
from app.models.main.User import User, UserRole
from app.models.tenant import InstitutionUsers
from app.models.tenant.Roles import Role
from app.models.tenant.UserRoles import UserRoles
from app.utils.db_manager import switch_to_institution_db
from sqlalchemy.exc import SQLAlchemyError


class UserRolesService:

    @staticmethod
    def assign_role_to_user(data, skid):
        """
        Give a user their role in the institution. Everyone has exactly one role, so this REPLACES the user's role
        (it used to add a second one). The institution record and the login account are kept in step: the login
        account gets the role's built-in base (a custom role's "based on" role).
        """
        try:
            user_id = data.get("user_id")
            role_id = data.get("role_id")
            assigned_by = data.get("assigned_by")
            if not user_id or not role_id:
                raise ValueError("Both user_id and role_id are required")

            with switch_to_institution_db(skid) as tenant_session:
                institution_user = tenant_session.query(InstitutionUsers).get(user_id)
                if not institution_user:
                    raise ValueError(f"User with ID {user_id} not found in institution database.")
                role_obj = tenant_session.query(Role).get(role_id)
                if not role_obj:
                    raise ValueError(f"Role with ID {role_id} not found.")
                if role_obj.is_active is False:
                    raise ValueError(f"The role '{role_obj.role_name}' is switched off")
                try:
                    login_role = UserRole(str(role_obj.base_role or role_obj.role_code).upper())
                except ValueError:
                    raise ValueError(f"The role '{role_obj.role_name}' isn't based on a built-in role")

                # one role per person: drop any other role rows, keep / add this one
                tenant_session.query(UserRoles).filter(
                    UserRoles.user_id == user_id, UserRoles.role_id != role_id
                ).delete(synchronize_session=False)
                link = tenant_session.query(UserRoles).filter_by(user_id=user_id, role_id=role_id).first()
                if link:
                    link.is_active = True
                    link.assigned_by = assigned_by
                else:
                    tenant_session.add(UserRoles(user_id=user_id, role_id=role_id, assigned_by=assigned_by, is_active=True))
                institution_user.role_id = role_id

                main_user = db.session.query(User).filter_by(skid=skid, institution_user_id=int(user_id)).first()
                if main_user:
                    main_user.role = login_role
                tenant_session.commit()
                db.session.commit()

            from app.utils.role_permissions import forget_cached_permissions
            forget_cached_permissions(skid)
            return {
                "user_id": user_id,
                "role_id": role_id,
                "login_role": login_role.value,
                "message": "Role assigned (replaces any previous role)",
            }

        except ValueError:
            db.session.rollback()
            raise
        except SQLAlchemyError as e:
            db.session.rollback()
            raise Exception(f"Database error: {str(e)}")
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Failed to assign role: {str(e)}")
