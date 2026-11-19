from app import db
from app.models.tenant import Class, Teacher, SchoolUsers, Student, StudentEnrollment
from app.models.tenant.Sections import Section
from app.utils.db_manager import switch_to_school_db
from app.utils.usage_check import usage_summary, CLASS_REFERENCES, SECTION_REFERENCES, blocked_message
from sqlalchemy import text
from datetime import date


def _section_teacher_id(value):
    """A section's class teacher is optional: '', None, 'null', 'NaN' -> None (no teacher)."""
    if value is None or (isinstance(value, str) and value.strip().lower() in ('', 'null', 'none', 'nan', 'undefined')):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError("Invalid class teacher")


class ClassService:
    @staticmethod
    def create_class(data, skid):
        """
        Create a new class in tenant database
        """
        try:
            if not skid:
                raise ValueError("School ID (skid) is required")
            
            # Create class in tenant DB
            with switch_to_school_db(skid) as tenant_session:
                # Check if class name already exists
                existing_class = tenant_session.query(Class).filter_by(
                    class_name=data['class_name']
                ).first()
                
                if existing_class:
                    raise ValueError(f"Class '{data['class_name']}' already exists")
                
                new_class = Class(
                    class_name=data['class_name']
                )
                
                tenant_session.add(new_class)
                tenant_session.commit()
                
                # Return the created class with its ID
                tenant_session.refresh(new_class)
                return new_class.to_dict()

        except Exception as e:
            raise Exception(f"Failed to create class: {str(e)}")

    @staticmethod
    def update_class(class_id, data, skid):
        """
        Update an existing class
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                class_obj = tenant_session.query(Class).filter_by(id=class_id).first()
                if not class_obj:
                    raise ValueError("Class not found")
                
                # Check if new class name already exists (excluding current class)
                existing_class = tenant_session.query(Class).filter(
                    Class.class_name == data['class_name'],
                    Class.id != class_id
                ).first()
                
                if existing_class:
                    raise ValueError(f"Class '{data['class_name']}' already exists")
                
                class_obj.class_name = data['class_name']
                tenant_session.commit()
                
                tenant_session.refresh(class_obj)
                return class_obj.to_dict()

        except Exception as e:
            raise Exception(f"Failed to update class: {str(e)}")

    @staticmethod
    def delete_class(class_id, skid):
        """
        Delete a class and all its Section
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                class_obj = tenant_session.query(Class).filter_by(id=class_id).first()
                if not class_obj:
                    raise ValueError("Class not found")
                
                # Only allow deleting a class nothing depends on (its empty sections are removed with it)
                usage = usage_summary(tenant_session, CLASS_REFERENCES, class_id)
                if usage:
                    raise ValueError(blocked_message(class_obj.class_name or f'#{class_id}', 'class', usage))
                Sections = tenant_session.query(Section).filter_by(class_id=class_id).all()
                
                # Delete all Section first
                for section in Sections:
                    tenant_session.delete(section)
                
                # Delete the class
                tenant_session.delete(class_obj)
                tenant_session.commit()

        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to delete class: {str(e)}")

    @staticmethod
    def get_classes_by_school(skid):
        """
        Get all classes for a specific school
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                classes = tenant_session.query(Class).all()
                
                for cls in classes:
                    student_count = (
                        tenant_session.query(StudentEnrollment)
                        .filter_by(class_id=cls.id)
                        .count()
                    )
                    cls.student_count = student_count
                return [cls.to_dict() for cls in classes]
                
        except Exception as e:
            raise Exception(f"Failed to retrieve classes: {str(e)}")

    @staticmethod
    def get_class_by_id(class_id, skid):
        """
        Get a specific class by ID with student count
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                class_obj = tenant_session.query(Class).filter_by(id=class_id).first()
                if not class_obj:
                    raise ValueError("Class not found")

                # Get student count for this class
                student_count = (
                    tenant_session.query(StudentEnrollment)
                    .filter_by(class_id=class_id)
                    .count()
                )
                class_obj.student_count = student_count

                return class_obj.to_dict()

        except Exception as e:
            raise Exception(f"Failed to retrieve class: {str(e)}")


#----------------------------------------------- SECTIONS APIS --------------------------------------------------------


    @staticmethod
    def create_section(data, skid):
        """
        Create a new section in tenant database
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Validate class exists
                class_obj = tenant_session.query(Class).filter_by(id=data['class_id']).first()
                if not class_obj:
                    raise ValueError("Class not found")
                
                # Check if section name already exists for this class
                existing_section = tenant_session.query(Section).filter_by(
                    section_name=data['section_name'],
                    class_id=data['class_id']
                ).first()
                
                if existing_section:
                    raise ValueError(f"Section '{data['section_name']}' already exists for this class")
                
                # Class teacher is optional (can be assigned later); validate it if given
                teacher_id = _section_teacher_id(data.get('teacher_id'))
                if teacher_id is not None and not tenant_session.query(Teacher).filter_by(user_id=teacher_id).first():
                    raise ValueError("Teacher not found")

                new_section = Section(
                    section_name=data['section_name'],
                    class_id=data['class_id'],
                    teacher_id=teacher_id
                )
                
                tenant_session.add(new_section)
                tenant_session.commit()
                
                # Return the created section with its ID
                tenant_session.refresh(new_section)
                return new_section.to_dict()

        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to create section: {str(e)}")

    @staticmethod
    def get_sections_by_class(class_id, skid):
        """
        Get all Section for a specific class
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                sections = tenant_session.query(Section).filter_by(class_id=class_id).all()
    
                for section in sections:
                    if section.teacher_id:
                        teacher = tenant_session.query(Teacher).filter_by(user_id=section.teacher_id).first()
                        if teacher:
                            school_user = tenant_session.query(SchoolUsers).filter_by(id=teacher.user_id).first()
                            if school_user:
                                section.teacher_name = f"{school_user.first_name} {school_user.last_name}"
                                
                    # Get student count for this section
                    student_count = tenant_session.query(StudentEnrollment).filter_by(section_id=section.id).count()
                    section.student_count = student_count
    
                return [section.to_dict() for section in sections]  # ✅ serialize list
    
        except Exception as e:
            raise Exception(f"Failed to retrieve Section: {str(e)}")

    @staticmethod
    def update_section(section_id, data, skid):
        """
        Update an existing section
        """
        try:
            if 'section_name' not in data:
                raise ValueError("Section name is required")
            
            with switch_to_school_db(skid) as tenant_session:
                section = tenant_session.query(Section).filter_by(id=section_id).first()
                if not section:
                    raise ValueError("Section not found")
                
                # Check if new section name already exists for this class (excluding current section)
                existing_section = tenant_session.query(Section).filter(
                    Section.section_name == data['section_name'],
                    Section.class_id == section.class_id,
                    Section.id != section_id
                ).first()
                
                if existing_section:
                    raise ValueError(f"Section '{data['section_name']}' already exists for this class")
                
                # Validate teacher exists if provided; an empty value removes the class teacher
                teacher_id = _section_teacher_id(data.get('teacher_id'))
                if teacher_id is not None and not tenant_session.query(Teacher).filter_by(user_id=teacher_id).first():
                    raise ValueError("Teacher not found")
                
                section.section_name = data['section_name']
                if 'teacher_id' in data:
                    section.teacher_id = teacher_id
                
                tenant_session.commit()
                
                tenant_session.refresh(section)
                return section.to_dict()

        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to update section: {str(e)}")

    @staticmethod
    def delete_section(section_id, skid):
        """
        Delete a section
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                section = tenant_session.query(Section).filter_by(id=section_id).first()
                if not section:
                    raise ValueError("Section not found")
                
                # Only allow deleting a section nothing depends on
                usage = usage_summary(tenant_session, SECTION_REFERENCES, section_id)
                if usage:
                    raise ValueError(blocked_message(section.section_name or f'#{section_id}', 'section', usage))

                # Subject links are configuration only: remove them with the section
                tenant_session.execute(text('DELETE FROM section_subjects WHERE section_id = :id'), {'id': int(section_id)})
                tenant_session.delete(section)
                tenant_session.commit()

        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to delete section: {str(e)}")

    @staticmethod
    def get_section_by_id(section_id, skid):
        """
        Get a specific section by ID
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                section = tenant_session.query(Section).filter_by(id=section_id).first()
                if not section:
                    raise ValueError("Section not found")
                return section
                
        except Exception as e:
            raise Exception(f"Failed to retrieve section: {str(e)}")


    @staticmethod
    def add_students_to_section(skid, section_id, student_ids):
        """
        Add multiple students to a section
        Ensures a student can only be in ONE section at a time
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Verify section exists
                section = tenant_session.query(Section).filter_by(id=section_id).first()
                if not section:
                    raise ValueError("Section not found")
                
                added_count = 0
                failed_count = 0
                failed_students = []
                
                for student_id in student_ids:
                    try:
                        # Check if student exists
                        student = tenant_session.query(Student).filter_by(user_id=student_id).first()
                        if not student:
                            failed_students.append({
                                'student_id': student_id,
                                'reason': 'Student not found'
                            })
                            failed_count += 1
                            continue
                        
                        # **CRITICAL CHECK**: Verify student is not already in another section
                        # Check if student has any current enrollment
                        existing_enrollment = tenant_session.query(StudentEnrollment).filter_by(
                            student_id=student_id
                        ).first()
                        
                        if existing_enrollment:
                            # Student is already enrolled in a section
                            if existing_enrollment.section_id == section_id:
                                # Already in THIS section
                                failed_students.append({
                                    'student_id': student_id,
                                    'reason': 'Already enrolled in this section'
                                })
                            else:
                                # Already in ANOTHER section
                                current_section = tenant_session.query(Section).filter_by(
                                    id=existing_enrollment.section_id
                                ).first()
                                failed_students.append({
                                    'student_id': student_id,
                                    'reason': f'Already enrolled in {current_section.section_name if current_section else "another section"}. Remove from current section first.'
                                })
                            failed_count += 1
                            continue
                        
                        # Also check student table's current assignment
                        if student.section_id is not None:
                            current_section = tenant_session.query(Section).filter_by(
                                id=student.section_id
                            ).first()
                            failed_students.append({
                                'student_id': student_id,
                                'reason': f'Already assigned to {current_section.section_name if current_section else "another section"}. Remove from current section first.'
                            })
                            failed_count += 1
                            continue
                        
                        # Create new enrollment
                        new_enrollment = StudentEnrollment(
                            student_id=student_id,
                            class_id=section.class_id,
                            section_id=section_id,
                            enrollment_date=date.today(),
                        )
                        tenant_session.add(new_enrollment)
                        
                        # Update student's current class and section
                        student.class_id = section.class_id
                        student.section_id = section_id
                        
                        added_count += 1
                        
                    except Exception as e:
                        failed_students.append({
                            'student_id': student_id,
                            'reason': str(e)
                        })
                        failed_count += 1
                        continue
                
                # Commit all successful enrollments
                if added_count > 0:
                    tenant_session.commit()
                
                return {
                    'added_count': added_count,
                    'failed_count': failed_count,
                    'failed_students': failed_students
                }
                
        except Exception as e:
            tenant_session.rollback()
            raise Exception(f"Failed to add students to section: {str(e)}")
    
    
    @staticmethod
    def remove_student_from_section(skid, section_id, student_id):
        """
        Remove a student from a section
        Also cleans up the student's current assignment
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Find enrollment record
                enrollment = tenant_session.query(StudentEnrollment).filter_by(
                    student_id=student_id,
                    section_id=section_id
                ).first()
                
                if not enrollment:
                    raise ValueError("Enrollment record not found for the given student and section")
                
                # Delete enrollment
                tenant_session.delete(enrollment)
                
                # Update student's class and section to NULL (unassigned)
                student = tenant_session.query(Student).filter_by(user_id=student_id).first()
                if student:
                    student.class_id = None
                    student.section_id = None
                
                tenant_session.commit()
                return True
                
        except Exception as e:
            tenant_session.rollback()
            raise Exception(f"Failed to remove student from section: {str(e)}")
    
    
    @staticmethod
    def move_student_to_section(skid, new_section_id, student_id):
        """
        Move a student from current section to a new section
        This is safer than remove + add
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Verify new section exists
                new_section = tenant_session.query(Section).filter_by(id=new_section_id).first()
                if not new_section:
                    raise ValueError("Target section not found")
                
                # Get student
                student = tenant_session.query(Student).filter_by(user_id=student_id).first()
                if not student:
                    raise ValueError("Student not found")
                
                # Find current enrollment
                current_enrollment = tenant_session.query(StudentEnrollment).filter_by(
                    student_id=student_id
                ).first()
                
                if current_enrollment:
                    # Update existing enrollment
                    current_enrollment.section_id = new_section_id
                    current_enrollment.class_id = new_section.class_id
                    current_enrollment.enrollment_date = date.today()
                else:
                    # Create new enrollment
                    new_enrollment = StudentEnrollment(
                        student_id=student_id,
                        class_id=new_section.class_id,
                        section_id=new_section_id,
                        enrollment_date=date.today(),
                        skid=skid
                    )
                    tenant_session.add(new_enrollment)
                
                # Update student's current assignment
                student.class_id = new_section.class_id
                student.section_id = new_section_id
                
                tenant_session.commit()
                return True
                
        except Exception as e:
            tenant_session.rollback()
            raise Exception(f"Failed to move student: {str(e)}")

    @staticmethod
    def remove_subject_from_section(skid, section_id, subject_id):
        """
        Remove a subject from a section by unsetting the section_id
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Find the subject
                subject = tenant_session.query(Subject).filter_by(
                    id=subject_id,
                    section_id=section_id
                ).first()
                
                if not subject:
                    raise ValueError("Subject not found in this section")
                
                # Remove section association (set to NULL)
                subject.section_id = None
                
                tenant_session.commit()
                return True
                    
        except Exception as e:
            tenant_session.rollback()
            raise Exception(f"Failed to remove subject from section: {str(e)}")
