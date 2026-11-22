# app/services/announcement_service.py

from app.utils.db_manager import switch_to_school_db
from app.models.tenant import SchoolUsers, Student, Class, AcademicYear
from app.models.tenant.Announcement import Announcement
from sqlalchemy import and_, or_, cast, case, func
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
import logging
_log = logging.getLogger(__name__)


def _day_value(value, label):
    """A date (or datetime / 'YYYY-MM-DD...' text) as a datetime, or None."""
    if value in (None, ''):
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00')).replace(tzinfo=None)
    except ValueError:
        raise ValueError(f"{label} must be a date like 2026-11-25")


def _check_announcement(title, publish_date, expiry_date):
    """QA C16: a title is required and the post can't expire before it is published."""
    if not str(title or '').strip():
        raise ValueError("Enter a title")
    if publish_date and expiry_date and expiry_date.date() < publish_date.date():
        raise ValueError("The expiry date can't be before the publishing date")


class AnnouncementService: 
    
    @staticmethod
    def create_announcement(skid, announcement_data):
        """Create a new announcement"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                academic_year = tenant_session.query(AcademicYear).filter_by(
                    id=announcement_data['academic_year_id']
                ).first()
                
                if not academic_year:
                    raise ValueError("Invalid academic year")

                # The chosen publishing date is kept (it used to be overwritten with "now", so a post scheduled
                # for later showed at once - QA C16); no date means now.
                publish_date = _day_value(announcement_data.get('publish_date'), "Publishing date") or datetime.utcnow()
                expiry_date = _day_value(announcement_data.get('expiry_date'), "Expiry date")
                _check_announcement(announcement_data.get('title'), publish_date, expiry_date)

                announcement = Announcement(
                    academic_year_id=announcement_data['academic_year_id'],
                    title=str(announcement_data['title']).strip(),
                    description=announcement_data['description'],
                    announcement_type=announcement_data['announcement_type'],
                    priority=announcement_data.get('priority', 'NORMAL'),
                    target_audience=announcement_data['target_audience'],
                    target_classes=announcement_data.get('target_classes'),
                    target_sections=announcement_data.get('target_sections'),
                    target_users=announcement_data.get('target_users'),
                    attachments=announcement_data.get('attachments'),
                    is_published=announcement_data.get('is_published', True),
                    publish_date=publish_date,
                    expiry_date=expiry_date,
                    created_by=announcement_data.get('created_by')
                )
                
                tenant_session.add(announcement)
                tenant_session.commit()
                
                # Fixed: Call to_dict() on the instance, not the class
                return announcement.to_dict()
                
        except ValueError:
            raise  # a clear message for the user (it used to be wrapped into a 500)
        except Exception as e:
            if tenant_session:
                tenant_session.rollback()
            raise Exception(f"Failed to create announcement: {str(e)}")
    
    
    @staticmethod
    def get_announcement_by_id(skid, announcement_id):
        """Get a single announcement by ID"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                announcement = tenant_session.query(Announcement).filter_by(
                    id=announcement_id
                ).first()
                
                if not announcement:
                    raise ValueError("Announcement not found")
                
                return announcement.to_dict()
                
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to get announcement: {str(e)}")

    
    @staticmethod
    def get_announcements(skid, academic_year_id, user_info=None, filters=None):
        """Get announcements with filters"""
        try:    
            with switch_to_school_db(skid) as tenant_session:
                query = tenant_session.query(Announcement, SchoolUsers).join(
                    SchoolUsers, Announcement.created_by == SchoolUsers.id
                ).filter(
                    Announcement.academic_year_id == academic_year_id,
                    Announcement.is_active == True,
                    Announcement.is_published == True
                )
                
                # Filter by current date. Expiry is a day: the post stays up until the END of that day (it used to
                # vanish at midnight at the START of it).
                now = datetime.utcnow()
                today_start = datetime.combine(now.date(), datetime.min.time())
                query = query.filter(
                    or_(
                        Announcement.expiry_date == None,  # Fixed: Changed from announcement.expiry_date
                        Announcement.expiry_date >= today_start
                    )
                )
                # Readers only see a post from its publishing date; the school's admins see scheduled ones too
                if not user_info or user_info.get('role') not in ('SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL'):
                    query = query.filter(or_(Announcement.publish_date == None, Announcement.publish_date <= now))
                
                # Apply additional filters
                if filters:
                    if filters.get('announcement_type'):
                        query = query.filter(Announcement.announcement_type == filters['announcement_type'])
                    if filters.get('priority'):
                        query = query.filter(Announcement.priority == filters['priority'])
                    if filters.get('search'):
                        term = f"%{filters['search']}%"
                        query = query.filter(or_(Announcement.title.ilike(term), Announcement.description.ilike(term)))
                
                # Filter by user's access
                if user_info:
                    query = AnnouncementService._filter_by_user_access(  # Fixed: Changed class name
                        query, 
                        user_info, 
                        tenant_session
                    )
                
                # Fixed: Changed from announcement.created_at to Announcement.created_at
                # Most urgent first (priority used to sort alphabetically: Normal, Medium, Low, High, Urgent - QA C17)
                rank = case(
                    (func.upper(Announcement.priority) == 'URGENT', 4),
                    (func.upper(Announcement.priority) == 'HIGH', 3),
                    (func.upper(Announcement.priority).in_(['MEDIUM', 'NORMAL']), 2),
                    (func.upper(Announcement.priority) == 'LOW', 1),
                    else_=0,
                )
                query = query.order_by(rank.desc(), Announcement.created_at.desc())
                
                results = query.all()
                
                announcements = []
                for announcement, creator in results:
                    announcement_dict = announcement.to_dict()
                    announcement_dict['creator_name'] = f"{creator.first_name} {creator.last_name}"
                    announcements.append(announcement_dict)
                
                return announcements
                
        except Exception as e:
            import traceback
            _log.error(traceback.format_exc())
            raise Exception(f"Failed to get announcements: {str(e)}")
    
    
    @staticmethod
    def _filter_by_user_access(query, user_info, tenant_session):
        """Filter announcements based on user's role and access"""
        from sqlalchemy import func
        
        user_role = user_info.get('role')
        school_user_id = user_info.get('school_user_id')
        
        
        # Admin/Principal can see all
        if user_role in ['SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL']:
            return query
        
        # Build access filters - FIXED: Match exact database values
        access_conditions = [
            Announcement.target_audience == 'ALL',           # Keep this for backward compatibility
            Announcement.target_audience == 'All Users'      # Add this - matches database value
        ]
        
        if user_role == 'STUDENT':
            student = tenant_session.query(Student).filter_by(user_id=school_user_id).first()
            if student:
                access_conditions.extend([
                    Announcement.target_audience == 'ALL_STUDENTS',
                    Announcement.target_audience == 'All Students'  # Add this too
                ])
                
                # Check if student's class is in target_classes JSON array
                if student.class_id:
                    access_conditions.append(
                        and_(
                            or_(
                                Announcement.target_audience == 'SPECIFIC_CLASS',
                                Announcement.target_audience == 'Specific Classes'
                            ),
                            cast(Announcement.target_classes, JSONB).op('@>')(cast([student.class_id], JSONB))
                        )
                    )
                
                # Check if student's section is in target_sections JSON array
                if student.section_id:
                    access_conditions.append(
                        and_(
                            or_(
                                Announcement.target_audience == 'SPECIFIC_SECTION',
                                Announcement.target_audience == 'Specific Sections'
                            ),
                            cast(Announcement.target_sections, JSONB).op('@>')(cast([student.section_id], JSONB))
                        )
                    )
        
        elif user_role == 'TEACHER':
            access_conditions.extend([
                Announcement.target_audience == 'ALL_TEACHERS',
                Announcement.target_audience == 'All Teachers'  # Add this
            ])
        
        elif user_role == 'PARENT':
            access_conditions.extend([
                Announcement.target_audience == 'ALL_PARENTS',
                Announcement.target_audience == 'All Parents'  # Add this
            ])
            # ...and anything aimed at their children's classes / sections (parents never got these - QA C17)
            from app.models.tenant.StudentParent import StudentParent
            children = tenant_session.query(Student.class_id, Student.section_id).join(
                StudentParent, StudentParent.student_user_id == Student.user_id
            ).filter(StudentParent.parent_user_id == school_user_id).all() if school_user_id else []
            for class_id, section_id in children:
                if class_id:
                    access_conditions.append(and_(
                        or_(Announcement.target_audience == 'SPECIFIC_CLASS', Announcement.target_audience == 'Specific Classes'),
                        cast(Announcement.target_classes, JSONB).op('@>')(cast([class_id], JSONB)),
                    ))
                if section_id:
                    access_conditions.append(and_(
                        or_(Announcement.target_audience == 'SPECIFIC_SECTION', Announcement.target_audience == 'Specific Sections'),
                        cast(Announcement.target_sections, JSONB).op('@>')(cast([section_id], JSONB)),
                    ))
        
        # Check if user is specifically targeted
        if school_user_id:
            access_conditions.append(
                cast(Announcement.target_users, JSONB).op('@>')(cast([school_user_id], JSONB))
            )
        
        return query.filter(or_(*access_conditions))

    
    @staticmethod
    def update_announcement(skid, announcement_id, announcement_data):
        """Update an existing announcement"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                announcement = tenant_session.query(Announcement).filter_by(id=announcement_id).first()
                
                if not announcement:
                    raise ValueError("Announcement not found")  # Fixed: Capitalized
                
                data = dict(announcement_data)
                for key, label in (('publish_date', "Publishing date"), ('expiry_date', "Expiry date")):
                    if key in data:
                        data[key] = _day_value(data[key], label)
                if 'title' in data:
                    data['title'] = str(data['title'] or '').strip()
                _check_announcement(data.get('title', announcement.title),
                                    data.get('publish_date', announcement.publish_date),
                                    data.get('expiry_date', announcement.expiry_date))
                for key, value in data.items():
                    if hasattr(announcement, key) and key not in ['id', 'created_at', 'created_by']:
                        setattr(announcement, key, value)
                
                announcement.updated_at = datetime.utcnow()
                tenant_session.commit()
                
                return announcement.to_dict()
                
        except ValueError:
            raise  # a clear message for the user (it used to be wrapped into a 500)
        except Exception as e:
            if tenant_session:
                tenant_session.rollback()
            raise Exception(f"Failed to update announcement: {str(e)}")
    
    
    @staticmethod
    def delete_announcement(skid, announcement_id):
        """Soft delete an announcement"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                announcement = tenant_session.query(Announcement).filter_by(id=announcement_id).first()
                
                if not announcement:
                    raise ValueError("Announcement not found")  # Fixed: Capitalized
                
                announcement.is_active = False
                announcement.updated_at = datetime.utcnow()
                tenant_session.commit()
                
                return {'success': True, 'message': 'Announcement deleted successfully'}  # Fixed: Capitalized
                
        except Exception as e:
            if tenant_session:
                tenant_session.rollback()
            raise Exception(f"Failed to delete announcement: {str(e)}")
