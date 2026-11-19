from app.models.tenant.ExamModels import ExamSubjectConfig
from app.models.tenant.MarksModels import MarksEntry
from app.models.tenant.Student import Student
from app.utils.db_manager import switch_to_school_db

class MarksService:
    
    @staticmethod
    def get_students_with_marks(data, skid, academic_year_id):
        """Get students list with existing marks"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Validate required fields
                if 'exam_config_id' not in data:
                    raise ValueError("exam_config_id is required")
                if 'section_id' not in data:
                    raise ValueError("section_id is required")
                
                # Fetch students with their school user info
                students = tenant_session.query(Student).filter_by(
                    section_id=data['section_id']
                ).order_by(Student.roll_no).all()
                
                if not students:
                    return []
                
                result = []
                for student in students:
                    school_user = student.user
                    
                    existing_marks = tenant_session.query(MarksEntry).filter_by(
                        exam_config_id=data['exam_config_id'],
                        student_id=student.user_id,
                        academic_year_id=academic_year_id
                    ).first()
                    
                    result.append({
                        'student_id': student.user_id,
                        'student_name': f"{school_user.first_name} {school_user.last_name}" if school_user else "Unknown",
                        'roll_number': student.roll_no,
                        'existing_marks': {
                            'internal_marks': existing_marks.internal_marks if existing_marks else 0,
                            'external_marks': existing_marks.external_marks if existing_marks else 0,
                            'total_marks': existing_marks.total_marks if existing_marks else 0,
                            'is_absent': existing_marks.is_absent if existing_marks else False,
                            'remarks': existing_marks.remarks if existing_marks else ''
                        } if existing_marks else None
                    })
                
                return result
        except Exception as e:
            raise Exception(f"Failed to fetch students: {str(e)}")

    
    @staticmethod
    def bulk_enter_marks(exam_config_id, marks_data, teacher_id, is_draft, skid, academic_year_id):
        """Bulk insert/update marks entries"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                exam_config = tenant_session.query(ExamSubjectConfig).filter_by(
                    id=exam_config_id
                ).first()
                
                if not exam_config:
                    raise ValueError("Invalid exam configuration")
                
                updated_count = 0
                created_count = 0

                from app.utils.validators import student_marks
                from app.models.tenant.SchoolUsers import SchoolUsers
                for data in marks_data:
                    # Validate marks: 0..maximum, and internal + external = total (negative marks and
                    # mismatched splits like 5 + 5 = 99 used to be saved). Nothing is saved if any row is wrong.
                    person = tenant_session.query(SchoolUsers).filter_by(id=data.get('student_id')).first()
                    who = f"{person.first_name} {person.last_name or ''}".strip() if person else f"student {data.get('student_id')}"
                    data['internal_marks'], data['external_marks'], data['total_marks'] = student_marks(exam_config, data, who)
                    
                    existing_entry = tenant_session.query(MarksEntry).filter_by(
                        exam_config_id=exam_config_id,
                        student_id=data['student_id'],
                        academic_year_id=academic_year_id
                    ).first()
                    
                    if existing_entry:
                        existing_entry.internal_marks = data.get('internal_marks', 0)
                        existing_entry.external_marks = data.get('external_marks', 0)
                        existing_entry.total_marks = data['total_marks']
                        existing_entry.is_absent = data.get('is_absent', False)
                        existing_entry.remarks = data.get('remarks')
                        existing_entry.entered_by = teacher_id
                        updated_count += 1
                    else:
                        new_entry = MarksEntry(
                            exam_config_id=exam_config_id,
                            student_id=data['student_id'],
                            academic_year_id=academic_year_id,
                            internal_marks=data.get('internal_marks', 0),
                            external_marks=data.get('external_marks', 0),
                            total_marks=data['total_marks'],
                            is_absent=data.get('is_absent', False),
                            remarks=data.get('remarks'),
                            entered_by=teacher_id
                        )
                        tenant_session.add(new_entry)
                        created_count += 1
                
                tenant_session.commit()
                
                return {
                    "created": created_count,
                    "updated": updated_count,
                    "total": len(marks_data)
                }
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to save marks: {str(e)}")