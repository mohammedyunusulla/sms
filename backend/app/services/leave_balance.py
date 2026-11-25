"""
Paid-leave balances for staff.

- The Leave Policy sets paid days per staff leave type for an academic year (no row = no limit; a year
  without a policy uses the latest earlier year's).
- Weekly offs and staff holidays inside a leave aren't counted (calendar_service).
- When staff leave is approved, its days are split into paid (up to what's left of the balance) and
  unpaid (the rest - the LAST days of the leave). The split is stored on the request (paid_days / unpaid_days),
  so later changes to the policy don't rewrite decided requests. Cancelling an approved leave gives its paid
  days back (only approved requests count as used).
- Unpaid leave days count towards the salary loss of pay (staff_attendance_service), unless the person was
  marked as working that day.
"""
from datetime import date, timedelta

from sqlalchemy import func

from app.models.tenant.AcademicYear import AcademicYear
from app.models.tenant.LeavePolicy import LeavePolicy
from app.models.tenant.LeaveRequest import LeaveRequest

STAFF_TYPES = ('CASUAL', 'SICK', 'OTHER')
MAX_PAID_DAYS = 366


def ensure_tables(session):
    LeavePolicy.__table__.create(bind=session.connection(), checkfirst=True)


def chargeable_dates(session, start, end):
    """Leave days that count: every day from start to end except weekly offs and staff holidays."""
    from app.services.calendar_service import working_dates
    return working_dates(session, start, end, 'STAFF')


def policy_for_year(session, year_id):
    """({leave_type: paid_days}, inherited_year_name or None). Missing types have no limit."""
    ensure_tables(session)
    if year_id is None:
        return {}, None
    rows = session.query(LeavePolicy).filter_by(academic_year_id=year_id).all()
    if rows:
        return {r.leave_type: r.paid_days for r in rows}, None
    year = session.query(AcademicYear).filter_by(id=year_id).first()
    if not year:
        return {}, None
    earlier = (session.query(AcademicYear).join(LeavePolicy, LeavePolicy.academic_year_id == AcademicYear.id)
               .filter(AcademicYear.start_date < year.start_date)
               .order_by(AcademicYear.start_date.desc()).first())
    if not earlier:
        return {}, None
    rows = session.query(LeavePolicy).filter_by(academic_year_id=earlier.id).all()
    return {r.leave_type: r.paid_days for r in rows}, earlier.year_name


def used_paid_days(session, user_id, year_id, leave_type, exclude_id=None):
    query = session.query(func.coalesce(func.sum(LeaveRequest.paid_days), 0)).filter(
        LeaveRequest.applicant_type == 'STAFF', LeaveRequest.status == 'APPROVED',
        LeaveRequest.user_id == int(user_id), LeaveRequest.leave_type == leave_type,
    )
    query = query.filter(LeaveRequest.academic_year_id == year_id) if year_id is not None \
        else query.filter(LeaveRequest.academic_year_id.is_(None))
    if exclude_id is not None:
        query = query.filter(LeaveRequest.id != exclude_id)
    return int(query.scalar() or 0)


def balances(session, user_id, year_id, labels):
    """[{type, label, paid_days (None = no limit), used, remaining}] for a staff member."""
    policy, _ = policy_for_year(session, year_id)
    out = []
    for leave_type in STAFF_TYPES:
        quota = policy.get(leave_type)
        used = used_paid_days(session, user_id, year_id, leave_type)
        out.append({'type': leave_type, 'label': labels.get(leave_type, leave_type.title()), 'paid_days': quota,
                    'used': used, 'remaining': None if quota is None else max(0, quota - used)})
    return out


def split_for(session, leave):
    """(paid, unpaid) days if this staff leave were approved now."""
    days = len(chargeable_dates(session, leave.from_date, leave.to_date))
    policy, _ = policy_for_year(session, leave.academic_year_id)
    quota = policy.get(leave.leave_type)
    if quota is None:
        return days, 0
    remaining = max(0, quota - used_paid_days(session, leave.user_id, leave.academic_year_id, leave.leave_type, exclude_id=leave.id))
    paid = min(days, remaining)
    return paid, days - paid


def unpaid_dates(session, leave):
    """The unpaid days of an approved staff leave: its last `unpaid_days` counted days."""
    n = int(leave.unpaid_days or 0)
    if n <= 0:
        return []
    return chargeable_dates(session, leave.from_date, leave.to_date)[-n:]


def unpaid_leave_dates(session, user_ids, start, end):
    """{user_id: set(dates)} of unpaid approved staff leave between start and end."""
    ids = [int(u) for u in user_ids]
    if not ids:
        return {}
    rows = session.query(LeaveRequest).filter(
        LeaveRequest.applicant_type == 'STAFF', LeaveRequest.status == 'APPROVED',
        LeaveRequest.unpaid_days > 0, LeaveRequest.user_id.in_(ids),
        LeaveRequest.from_date <= end, LeaveRequest.to_date >= start,
    ).all()
    out = {}
    for leave in rows:
        for d in unpaid_dates(session, leave):
            if start <= d <= end:
                out.setdefault(leave.user_id, set()).add(d)
    return out


def get_policy(session, year_id, labels):
    policy, inherited = policy_for_year(session, year_id)
    year = session.query(AcademicYear).filter_by(id=year_id).first() if year_id else None
    return {
        'academic_year_id': year_id,
        'year_name': year.year_name if year else None,
        'inherited_from': inherited,
        'types': [{'type': t, 'label': labels.get(t, t.title()), 'paid_days': policy.get(t)} for t in STAFF_TYPES],
    }


def save_policy(session, year_id, types, actor_id):
    """types: [{type, paid_days (None/'' = no limit)}] for the year."""
    if year_id is None:
        raise ValueError('There is no current academic year')
    clean = {}
    for item in types or []:
        leave_type = str((item or {}).get('type') or '').upper()
        if leave_type not in STAFF_TYPES:
            raise ValueError(f"Unknown leave type '{leave_type}'")
        value = item.get('paid_days')
        if value in (None, ''):
            clean[leave_type] = None
            continue
        try:
            days = int(value)
        except (TypeError, ValueError):
            raise ValueError('Paid days must be a whole number')
        if days < 0 or days > MAX_PAID_DAYS:
            raise ValueError(f'Paid days must be between 0 and {MAX_PAID_DAYS}')
        clean[leave_type] = days
    ensure_tables(session)
    existing = {r.leave_type: r for r in session.query(LeavePolicy).filter_by(academic_year_id=year_id).all()}
    if not existing:
        # first save for this year: start from the inherited policy so untouched types keep their limits
        inherited, _ = policy_for_year(session, year_id)
        for t, days in inherited.items():
            clean.setdefault(t, days)
    # every type gets a row (NULL = no limit), so the year never falls back to an earlier year's policy
    for t in STAFF_TYPES:
        row = existing.get(t)
        days = clean.get(t, row.paid_days if row else None)
        if row:
            row.paid_days, row.updated_by = days, actor_id
        else:
            session.add(LeavePolicy(academic_year_id=year_id, leave_type=t, paid_days=days, updated_by=actor_id))
