# ============================================================
# app/services/subject_service.py (Fixed Service)
from app import db
from app.models.tenant import SectionSubject, Subject, TeacherSubject, SchoolUsers
from app.models.tenant.Sections import Section
from app.utils.db_manager import switch_to_school_db


class SubjectService:

    @staticmethod
    def create_subject(data, skid):
        """
        Create a new subject in tenant database
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Check if subject code already exists (only if subject_code is provided)
                if data.get('subject_code'):
                    existing_subject = tenant_session.query(Subject).filter_by(
                        subject_code=data['subject_code']
                    ).first()
                    
                    if existing_subject:
                        raise ValueError(f"Subject code '{data['subject_code']}' already exists")
                
                # Create new subject with all fields
                new_subject = Subject(
                    subject_name=data['subject_name'],
                    subject_code=data.get('subject_code'),  # Optional
                    credits=data.get('credits', 1),         # Default to 1
                    description=data.get('description'),    # Optional
                    class_id=data['class_id']               # Required for association
                )
                
                tenant_session.add(new_subject)
                tenant_session.flush()
                
                # Assign teachers
                teacher_ids = data.get("teacher_ids", [])
                for teacher_id in teacher_ids:
                    assignment = TeacherSubject(
                        teacher_id=teacher_id,
                        subject_id=new_subject.id
                    )
                    tenant_session.add(assignment)
    
                tenant_session.commit()
                tenant_session.refresh(new_subject)
                return new_subject.to_dict()

        except Exception as e:
            raise Exception(f"Failed to create subject: {str(e)}")

    @staticmethod
    def update_subject(subject_id, data, skid):
        """
        Update an existing subject in tenant database
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                subject = tenant_session.query(Subject).filter_by(id=subject_id).first()
                
                if not subject:
                    raise ValueError("Subject not found")
                
                # Check if subject code already exists (only if being changed and provided)
                if data.get('subject_code') and data['subject_code'] != subject.subject_code:
                    existing_subject = tenant_session.query(Subject).filter(
                        Subject.subject_code == data['subject_code'],
                        Subject.id != subject_id
                    ).first()
                    
                    if existing_subject:
                        raise ValueError(f"Subject code '{data['subject_code']}' already exists")
                
                # Update subject fields
                subject.subject_name = data['subject_name']
                subject.subject_code = data.get('subject_code')
                subject.credits = data.get('credits', 1)
                subject.description = data.get('description')
                
                # Remove existing teacher assignments
                tenant_session.query(TeacherSubject).filter_by(subject_id=subject.id).delete()
    
                # Reassign teachers
                teacher_ids = data.get("teacher_ids", [])
                for teacher_id in teacher_ids:
                    assignment = TeacherSubject(
                        teacher_id=teacher_id,
                        subject_id=subject.id
                    )
                    tenant_session.add(assignment)
    
                tenant_session.commit()
                tenant_session.refresh(subject)
                
                return subject.to_dict()

        except Exception as e:
            raise Exception(f"Failed to update subject: {str(e)}")


    @staticmethod
    def delete_subject(subject_id, skid):
        """
        Delete a subject from tenant database
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                subject = tenant_session.query(Subject).filter_by(id=subject_id).first()
                
                if not subject:
                    raise ValueError("Subject not found")
                
                tenant_session.delete(subject)
                tenant_session.commit()
                
                return True

        except Exception as e:
            raise Exception(f"Failed to delete subject: {str(e)}")

    @staticmethod
    def get_subject_by_id(subject_id, skid):
        """
        Get a specific subject by ID
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                subject = tenant_session.query(Subject).filter_by(id=subject_id).first()
                
                if not subject:
                    raise ValueError("Subject not found")
                
                return subject.to_dict()

        except Exception as e:
            raise Exception(f"Failed to retrieve subject: {str(e)}")

    @staticmethod
    def get_subjects_by_class(class_id, skid):
        """
        Get all subjects for a specific class along with assigned teachers
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                subjects = tenant_session.query(Subject).filter_by(class_id=class_id).all()
                result = []
    
                for subject in subjects:
                    # Get assigned teacher_subject mappings
                    teacher_subjects = tenant_session.query(TeacherSubject).filter_by(subject_id=subject.id).all()
                    
                    teachers = []
                    for ts in teacher_subjects:
                        user = tenant_session.query(SchoolUsers).filter_by(id=ts.teacher_id).first()
                        if user:
                            teachers.append({
                                "id": user.id,
                                "first_name": user.first_name,
                                "last_name": user.last_name,
                                "email": user.email,
                                "phone": user.phone
                            })
                    
                    subject_data = subject.to_dict()
                    subject_data["teachers"] = teachers
                    result.append(subject_data)
                return result
    
        except Exception as e:
            raise Exception(f"Failed to retrieve subjects: {str(e)}")
        
    @staticmethod
    def get_subjects_list( skid):
        """
        Get all subjects in a school
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                subjects = tenant_session.query(Subject).all()
                return [subject.to_dict() for subject in subjects]
    
        except Exception as e:
            raise Exception(f"Failed to retrieve subjects: {str(e)}")
            

    @staticmethod
    def get_subjects_by_section(section_id, skid):
        """
        Get all subjects assigned to a specific section with their teachers
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Query subjects through the section_subjects association
                subjects = tenant_session.query(Subject).join(
                    SectionSubject, Subject.id == SectionSubject.subject_id
                ).filter(
                    SectionSubject.section_id == section_id,
                    SectionSubject.is_active == True
                ).all()
                
                result = []
                for subject in subjects:
                    # Get assigned teachers
                    teacher_subjects = tenant_session.query(TeacherSubject).filter_by(
                        subject_id=subject.id
                    ).all()
                    
                    teachers = []
                    for ts in teacher_subjects:
                        user = tenant_session.query(SchoolUsers).filter_by(id=ts.teacher_id).first()
                        if user:
                            teachers.append({
                                "id": user.id,
                                "first_name": user.first_name,
                                "last_name": user.last_name,
                                "email": user.email,
                                "phone": user.phone
                            })
                    
                    subject_data = subject.to_dict()
                    subject_data["teachers"] = teachers
                    result.append(subject_data)
                
                return result
        
        except Exception as e:
            raise Exception(f"Failed to retrieve section subjects: {str(e)}")
    
    
    @staticmethod
    def add_subjects_to_section(skid, section_id, subject_ids):
        """
        Assign multiple subjects to a section
        Validates that subjects belong to the same class as the section
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Verify section exists and get its class_id
                section = tenant_session.query(Section).filter_by(id=section_id).first()
                if not section:
                    raise ValueError("Section not found")
                
                added_count = 0
                failed_count = 0
                failed_subjects = []
                
                for subject_id in subject_ids:
                    try:
                        # Check if subject exists
                        subject = tenant_session.query(Subject).filter_by(id=subject_id).first()
                        if not subject:
                            failed_subjects.append({
                                'subject_id': subject_id,
                                'reason': 'Subject not found'
                            })
                            failed_count += 1
                            continue
                        
                        # Verify subject belongs to the same class
                        if subject.class_id != section.class_id:
                            failed_subjects.append({
                                'subject_id': subject_id,
                                'subject_name': subject.subject_name,
                                'reason': f'Subject belongs to different class. Expected class_id={section.class_id}, got {subject.class_id}'
                            })
                            failed_count += 1
                            continue
                        
                        # Check if already assigned
                        existing = tenant_session.query(SectionSubject).filter_by(
                            section_id=section_id,
                            subject_id=subject_id
                        ).first()
                        
                        if existing:
                            failed_subjects.append({
                                'subject_id': subject_id,
                                'subject_name': subject.subject_name,
                                'reason': 'Subject already assigned to this section'
                            })
                            failed_count += 1
                            continue
                        
                        # Create association
                        section_subject = SectionSubject(
                            section_id=section_id,
                            subject_id=subject_id,
                            is_active=True,
                        )
                        tenant_session.add(section_subject)
                        added_count += 1
                        
                    except Exception as e:
                        failed_subjects.append({
                            'subject_id': subject_id,
                            'reason': str(e)
                        })
                        failed_count += 1
                
                if added_count > 0:
                    tenant_session.commit()
                
                return {
                    'added_count': added_count,
                    'failed_count': failed_count,
                    'failed_subjects': failed_subjects
                }
                
        except Exception as e:
            tenant_session.rollback()
            raise Exception(f"Failed to add subjects to section: {str(e)}")
    
    
    @staticmethod
    def remove_subject_from_section(skid, section_id, subject_id):
        """
        Remove a subject from a section
        Only removes the assignment, doesn't delete the subject
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Find the association
                section_subject = tenant_session.query(SectionSubject).filter_by(
                    section_id=section_id,
                    subject_id=subject_id
                ).first()
                
                if not section_subject:
                    raise ValueError("Subject is not assigned to this section")
                
                # Delete the association
                tenant_session.delete(section_subject)
                tenant_session.commit()
                
                return True
                
        except Exception as e:
            tenant_session.rollback()
            raise Exception(f"Failed to remove subject from section: {str(e)}")
    
    
    @staticmethod
    def get_available_subjects_for_section(section_id, skid):
        """
        Get subjects that CAN be assigned to a section
        (same class, not yet assigned)
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Get section's class_id
                section = tenant_session.query(Section).filter_by(id=section_id).first()
                if not section:
                    raise ValueError("Section not found")
                
                # Get all subjects for this class
                all_subjects = tenant_session.query(Subject).filter_by(
                    class_id=section.class_id
                ).all()
                
                # Get already assigned subject IDs
                assigned_subject_ids = [
                    ss.subject_id for ss in 
                    tenant_session.query(SectionSubject).filter_by(
                        section_id=section_id
                    ).all()
                ]
                
                # Filter out assigned subjects
                available_subjects = [
                    subject.to_dict() for subject in all_subjects 
                    if subject.id not in assigned_subject_ids
                ]
                
                return available_subjects
                
        except Exception as e:
            raise Exception(f"Failed to get available subjects: {str(e)}")
