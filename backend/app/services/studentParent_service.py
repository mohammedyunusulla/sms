from app import db
from app.models.tenant import StudentParent, Student, Parent
from app.utils.db_manager import switch_to_school_db
from sqlalchemy import and_
from typing import List, Dict, Optional

class StudentParentService:

    @staticmethod
    def assign_students_to_parent(data, skid):
        """
        Assign multiple students to a parent
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                parent_user_id = data.get('parent_user_id')
                student_user_ids = data.get('student_user_ids', [])
                relation_type = data.get('relation_type', 'guardian')
                
                # Validate parent exists
                parent = tenant_session.query(Parent).filter_by(user_id=parent_user_id).first()
                if not parent:
                    raise ValueError(f"Parent with user_id {parent_user_id} not found")
                
                # Validate all students exist
                students = tenant_session.query(Student).filter(
                    Student.user_id.in_(student_user_ids)
                ).all()
                
                if len(students) != len(student_user_ids):
                    found_ids = [s.user_id for s in students]
                    missing_ids = set(student_user_ids) - set(found_ids)
                    raise ValueError(f"Students with user_ids {list(missing_ids)} not found")
                
                created_links = []
                existing_links = []
                
                # Create links for each student
                for student_user_id in student_user_ids:
                    # Check if link already exists
                    existing_link = tenant_session.query(StudentParent).filter_by(
                        student_user_id=student_user_id,
                        parent_user_id=parent_user_id
                    ).first()
                    
                    if existing_link:
                        existing_links.append({
                            'student_user_id': student_user_id,
                            'parent_user_id': parent_user_id,
                            'relation_type': existing_link.relation_type,
                            'message': 'Already linked'
                        })
                    else:
                        link = StudentParent(
                            student_user_id=student_user_id,
                            parent_user_id=parent_user_id,
                            relation_type=relation_type
                        )
                        tenant_session.add(link)
                        created_links.append({
                            'student_user_id': student_user_id,
                            'parent_user_id': parent_user_id,
                            'relation_type': relation_type,
                            'message': 'Newly created'
                        })
                
                tenant_session.commit()
                
                return {
                    'created_links': created_links,
                    'existing_links': existing_links,
                    'total_processed': len(student_user_ids)
                }

        except Exception as e:
            raise Exception(f"Failed to assign students to parent: {str(e)}")

    
    @staticmethod
    def update_student_parent_link(student_user_id, new_parent_user_id, relation_type, skid):
        """
        Update or create parent link for a student.
        Handles 4 scenarios:
        1. Remove parent (new_parent_user_id is None)
        2. Add new parent (no existing link)
        3. Update existing parent (change to different parent)
        4. Update relation type only (same parent, different relation)
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Validate student exists
                student = tenant_session.query(Student).filter_by(
                    user_id=student_user_id
                ).first()
                if not student:
                    raise ValueError(f"Student with user_id {student_user_id} not found")
                
                # Get existing parent link
                existing_link = tenant_session.query(StudentParent).filter_by(
                    student_user_id=student_user_id
                ).first()
                
                # CASE 1: Remove parent link
                if not new_parent_user_id:
                    if existing_link:
                        tenant_session.delete(existing_link)
                        tenant_session.commit()
                        return {
                            'action': 'removed',
                            'message': 'Parent link removed successfully'
                        }
                    return {
                        'action': 'none',
                        'message': 'No parent was linked to this student'
                    }
                
                # Validate new parent exists
                new_parent = tenant_session.query(Parent).filter_by(
                    user_id=new_parent_user_id
                ).first()
                if not new_parent:
                    raise ValueError(f"Parent with user_id {new_parent_user_id} not found")
                
                # CASE 2: Create new link
                if not existing_link:
                    new_link = StudentParent(
                        student_user_id=student_user_id,
                        parent_user_id=new_parent_user_id,
                        relation_type=relation_type
                    )
                    tenant_session.add(new_link)
                    tenant_session.commit()
                    return {
                        'action': 'created',
                        'message': 'Parent link created successfully'
                    }
                
                # CASE 3: Update to different parent
                if existing_link.parent_user_id != new_parent_user_id:
                    existing_link.parent_user_id = new_parent_user_id
                    existing_link.relation_type = relation_type
                    tenant_session.commit()
                    return {
                        'action': 'updated',
                        'message': 'Parent link updated successfully'
                    }
                
                # CASE 4: Same parent, update relation type
                if existing_link.relation_type != relation_type:
                    existing_link.relation_type = relation_type
                    tenant_session.commit()
                    return {
                        'action': 'updated',
                        'message': 'Parent relationship type updated successfully'
                    }
                
                # No changes
                return {
                    'action': 'unchanged',
                    'message': 'Parent link is already up to date'
                }
                
        except ValueError as ve:
            raise ve
        except Exception as e:
            tenant_session.rollback()
            raise Exception(f"Failed to update parent link: {str(e)}")

    @staticmethod
    def get_parent_students(parent_user_id: int, skid: str):
        """
        Get all students linked to a parent
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Check if parent exists
                parent = tenant_session.query(Parent).filter_by(user_id=parent_user_id).first()
                if not parent:
                    return None
                
                # Get all student links with student details
                links = tenant_session.query(StudentParent, Student).join(
                    Student, StudentParent.student_user_id == Student.user_id
                ).filter(StudentParent.parent_user_id == parent_user_id).all()
                
                students = []
                for link, student in links:
                    student_data = {
                        'user_id': student.user_id,
                        'name': getattr(student, 'name', f"Student {student.user_id}"),
                        'email': getattr(student, 'email', ''),
                        'relation_type': link.relation_type,
                        'section': getattr(student, 'section', ''),
                        'class_name': getattr(student, 'class_name', '')
                    }
                    students.append(student_data)
                
                return {
                    'parent_user_id': parent.user_id,
                    'parent_name': getattr(parent, 'name', f"Parent {parent.user_id}"),
                    'parent_email': getattr(parent, 'email', ''),
                    'students': students,
                    'total_students': len(students)
                }

        except Exception as e:
            raise Exception(f"Failed to get parent students: {str(e)}")

    @staticmethod
    def get_student_parents(student_user_id: int, skid: str):
        """
        Get all parents linked to a student
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Check if student exists
                student = tenant_session.query(Student).filter_by(user_id=student_user_id).first()
                if not student:
                    return None
                
                # Get all parent links with parent details
                links = tenant_session.query(StudentParent, Parent).join(
                    Parent, StudentParent.parent_user_id == Parent.user_id
                ).filter(StudentParent.student_user_id == student_user_id).all()
                
                parents = []
                for link, parent in links:
                    parent_data = {
                        'user_id': parent.user_id,
                        'name': getattr(parent, 'name', f"Parent {parent.user_id}"),
                        'email': getattr(parent, 'email', ''),
                        'relation_type': link.relation_type,
                        'phone': getattr(parent, 'phone', '')
                    }
                    parents.append(parent_data)
                
                return {
                    'student_user_id': student.user_id,
                    'student_name': getattr(student, 'name', f"Student {student.user_id}"),
                    'student_email': getattr(student, 'email', ''),
                    'parents': parents,
                    'total_parents': len(parents)
                }

        except Exception as e:
            raise Exception(f"Failed to get student parents: {str(e)}")

    @staticmethod
    def remove_student_from_parent(student_user_id: int, parent_user_id: int, skid: str):
        """
        Remove a student-parent relationship
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                link = tenant_session.query(StudentParent).filter_by(
                    student_user_id=student_user_id,
                    parent_user_id=parent_user_id
                ).first()
                
                if link:
                    tenant_session.delete(link)
                    tenant_session.commit()
                    return True
                return False

        except Exception as e:
            raise Exception(f"Failed to remove student from parent: {str(e)}")

    @staticmethod
    def update_relation_type(student_user_id: int, parent_user_id: int, relation_type: str, skid: str):
        """
        Update the relation type between a parent and student
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                link = tenant_session.query(StudentParent).filter_by(
                    student_user_id=student_user_id,
                    parent_user_id=parent_user_id
                ).first()
                
                if link:
                    link.relation_type = relation_type
                    tenant_session.commit()
                    return {
                        'student_user_id': student_user_id,
                        'parent_user_id': parent_user_id,
                        'relation_type': relation_type
                    }
                return None

        except Exception as e:
            raise Exception(f"Failed to update relation type: {str(e)}")

    @staticmethod
    def get_all_relationships(skid: str):
        """
        Get all parent-student relationships for a school
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                relationships = tenant_session.query(
                    StudentParent, Student, Parent
                ).join(
                    Student, StudentParent.student_user_id == Student.user_id
                ).join(
                    Parent, StudentParent.parent_user_id == Parent.user_id
                ).all()
                
                result = []
                for link, student, parent in relationships:
                    relationship_data = {
                        'student_user_id': student.user_id,
                        'student_name': getattr(student, 'name', f"Student {student.user_id}"),
                        'parent_user_id': parent.user_id,
                        'parent_name': getattr(parent, 'name', f"Parent {parent.user_id}"),
                        'relation_type': link.relation_type,
                        'student_section': getattr(student, 'section', ''),
                        'student_class': getattr(student, 'class_name', '')
                    }
                    result.append(relationship_data)
                
                return {
                    'relationships': result,
                    'total_relationships': len(result)
                }

        except Exception as e:
            raise Exception(f"Failed to get all relationships: {str(e)}")

    @staticmethod
    def get_parent_children(parent_user_id: int, skid: str):
        """
        Get all children linked to a parent with full details (name, class, section, roll_no).
        Used by the parent mobile app to populate child selector tabs.
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                from app.models.tenant.SchoolUsers import SchoolUsers
                from app.models.tenant.Class import Class
                from app.models.tenant.Sections import Section

                results = tenant_session.query(
                    StudentParent.relation_type,
                    Student.user_id,
                    Student.roll_no,
                    Student.class_id,
                    Student.section_id,
                    SchoolUsers.first_name,
                    SchoolUsers.last_name,
                    Class.class_name,
                    Section.section_name,
                ).join(
                    Student, StudentParent.student_user_id == Student.user_id
                ).join(
                    SchoolUsers, Student.user_id == SchoolUsers.id
                ).outerjoin(
                    Class, Student.class_id == Class.id
                ).outerjoin(
                    Section, Student.section_id == Section.id
                ).filter(
                    StudentParent.parent_user_id == parent_user_id
                ).all()

                children = []
                for row in results:
                    children.append({
                        'student_id': row.user_id,
                        'first_name': row.first_name,
                        'last_name': row.last_name,
                        'full_name': f"{row.first_name} {row.last_name}",
                        'roll_no': row.roll_no,
                        'class_id': row.class_id,
                        'class_name': row.class_name,
                        'section_id': row.section_id,
                        'section_name': row.section_name,
                        'relation_type': row.relation_type,
                    })

                return children

        except Exception as e:
            raise Exception(f"Failed to get parent children: {str(e)}")