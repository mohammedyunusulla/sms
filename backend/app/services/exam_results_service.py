"""
Exam results publishing: students and parents only see an exam's marks once the institution publishes them
for that academic year. Staff always see everything.
"""
from datetime import datetime

from app.models.tenant.AcademicYear import AcademicYear
from app.models.tenant.ExamModels import ExamType
from app.models.tenant.ExamResultPublication import ExamResultPublication
from app.utils.db_manager import switch_to_institution_db

# Roles that only see published results
RESULT_LIMITED_ROLES = ('STUDENT', 'PARENT')


def ensure_table(tenant_session):
    """Existing institutions: create the table on first use (new institutions get it from create_all)."""
    ExamResultPublication.__table__.create(bind=tenant_session.bind, checkfirst=True)


def published_exam_ids(tenant_session, academic_year_id):
    """Exam type ids whose results are published for the year."""
    ensure_table(tenant_session)
    rows = tenant_session.query(ExamResultPublication.exam_type_id).filter(
        ExamResultPublication.academic_year_id == int(academic_year_id)
    ).all()
    return {r[0] for r in rows}


def current_year_id(tenant_session):
    year = tenant_session.query(AcademicYear).filter_by(is_current=True).first()
    return year.id if year else None


class ExamResultsService:

    @staticmethod
    def list_publications(skid, academic_year_id):
        with switch_to_institution_db(skid) as tenant_session:
            ensure_table(tenant_session)
            rows = tenant_session.query(ExamResultPublication).filter(
                ExamResultPublication.academic_year_id == int(academic_year_id)
            ).all()
            return [r.to_dict() for r in rows]

    @staticmethod
    def set_published(skid, exam_type_id, academic_year_id, published, user_id):
        with switch_to_institution_db(skid) as tenant_session:
            ensure_table(tenant_session)
            if not tenant_session.query(ExamType).filter_by(id=exam_type_id).first():
                raise ValueError("Exam not found")
            if not tenant_session.query(AcademicYear).filter_by(id=academic_year_id).first():
                raise ValueError("Academic year not found")
            row = tenant_session.query(ExamResultPublication).filter_by(
                exam_type_id=exam_type_id, academic_year_id=academic_year_id
            ).first()
            newly_published = False
            if published and not row:
                row = ExamResultPublication(
                    exam_type_id=exam_type_id, academic_year_id=academic_year_id,
                    published_at=datetime.now(), published_by=user_id,
                )
                tenant_session.add(row)
                newly_published = True
            elif not published and row:
                tenant_session.delete(row)
            tenant_session.commit()
            # notify only for a first publish in the current year (not re-saves, not past years)
            if newly_published and int(academic_year_id) == current_year_id(tenant_session):
                from app.services import push_events
                push_events.results_published(skid, tenant_session, exam_type_id)
            return {'exam_type_id': exam_type_id, 'academic_year_id': academic_year_id, 'published': bool(published),
                    'published_at': row.published_at.isoformat() if published and row else None}
