"""
Staff attendance: one status per staff member per day, marked by the Institution Admin or anyone with the
"manage_staff_attendance" tick box; every staff member can see their own.

Staff = active institution users whose role (built-in, or the built-in role a custom role is based on) isn't
Student, Parent or an admin. Approved staff leave starts as "Leave" on the marking page, and approving leave
for a day already marked Absent turns it into Leave (leave_service).

Salary: month summaries feed Salary Payments, which suggests a loss of pay of
basic salary / days in the month x (Absent days + half of Half days + unpaid leave days). Approved leave is
paid up to the yearly balance (leave_balance.py); days beyond it are unpaid leave.
"""
import calendar
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func

from app.models.tenant.InstitutionUsers import InstitutionUsers
from app.models.tenant.LeaveRequest import LeaveRequest
from app.models.tenant.Roles import Role
from app.models.tenant.StaffAttendance import StaffAttendance
from app.utils.db_manager import switch_to_institution_db
from app.services.leave_balance import unpaid_leave_dates, ensure_tables as ensure_policy_table

STATUSES = ('PRESENT', 'ABSENT', 'LATE', 'HALF_DAY', 'LEAVE')
NOT_STAFF = ('STUDENT', 'PARENT', 'INSTITUTION_ADMIN', 'SUPER_ADMIN')
LOP_KEY = 'loss_of_pay'
REMARKS_MAX = 500


class StaffAttendanceError(ValueError):
    def __init__(self, message, code=400):
        super().__init__(message)
        self.code = code


def ensure_tables(session):
    bind = session.connection()
    LeaveRequest.__table__.create(bind=bind, checkfirst=True)
    StaffAttendance.__table__.create(bind=bind, checkfirst=True)
    ensure_policy_table(session)


def _parse_day(value, label='Date'):
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        raise StaffAttendanceError(f'{label} is not a valid date')


def _month(year, month):
    try:
        year, month = int(year), int(month)
        if not (2000 <= year <= 2100 and 1 <= month <= 12):
            raise ValueError
    except (TypeError, ValueError):
        raise StaffAttendanceError('Choose a valid month')
    days = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, days), days


def _status(value):
    status = str(value or '').strip().upper().replace(' ', '_')
    if status == 'HALFDAY':
        status = 'HALF_DAY'
    if status not in STATUSES:
        raise StaffAttendanceError(f"Invalid status '{value}'. Use one of: Present, Absent, Late, Half day, Leave")
    return status


def staff_members(session):
    """[(user, role)] of everyone counted as staff, by name."""
    base = func.coalesce(Role.base_role, Role.role_code)
    return (
        session.query(InstitutionUsers, Role)
        .join(Role, InstitutionUsers.role_id == Role.id)
        .filter(InstitutionUsers.is_active.isnot(False), base.notin_(NOT_STAFF))
        .order_by(InstitutionUsers.first_name, InstitutionUsers.last_name)
        .all()
    )


def _name(user):
    return f"{user.first_name or ''} {user.last_name or ''}".strip()


def approved_staff_leave(session, user_ids, start, end):
    """{user_id: {day: label}} for approved staff leave overlapping start..end ("Casual", or "Casual (unpaid)"
    for days beyond the yearly balance)."""
    ids = [int(u) for u in user_ids]
    if not ids:
        return {}
    rows = session.query(LeaveRequest).filter(
        LeaveRequest.applicant_type == 'STAFF', LeaveRequest.status == 'APPROVED',
        LeaveRequest.user_id.in_(ids), LeaveRequest.from_date <= end, LeaveRequest.to_date >= start,
    ).all()
    unpaid = unpaid_leave_dates(session, ids, start, end)
    out = {}
    for leave in rows:
        day = max(leave.from_date, start)
        while day <= min(leave.to_date, end):
            label = leave.leave_type.title()
            if day in unpaid.get(leave.user_id, ()):
                label += ' (unpaid)'
            out.setdefault(leave.user_id, {})[day] = label
            day = date.fromordinal(day.toordinal() + 1)
    return out


def _empty_totals():
    return {s: 0 for s in STATUSES}


def month_summaries(session, user_ids, year, month):
    """
    {user_id: {'PRESENT': n, ..., 'NOT_MARKED': n, 'UNPAID_LEAVE': n, 'days': n}}. Not marked counts only days up
    to today. UNPAID_LEAVE: days of approved leave beyond the balance, unless the person was marked as working
    (Present / Late) or already counted (Absent / Half day).
    """
    start, end, days = _month(year, month)
    ids = [int(u) for u in user_ids]
    out = {u: {**_empty_totals(), 'NOT_MARKED': 0, 'UNPAID_LEAVE': 0, 'days': days} for u in ids}
    if not ids:
        return out
    marked = {}
    for uid, day, status in session.query(StaffAttendance.user_id, StaffAttendance.date, StaffAttendance.status).filter(
            StaffAttendance.user_id.in_(ids), StaffAttendance.date >= start, StaffAttendance.date <= end).all():
        marked[(uid, day)] = status
        if status in out[uid]:
            out[uid][status] += 1
    for uid, dates in unpaid_leave_dates(session, ids, start, end).items():
        out[uid]['UNPAID_LEAVE'] = sum(1 for d in dates if marked.get((uid, d), 'LEAVE') == 'LEAVE')
    elapsed = max(0, (min(end, date.today()) - start).days + 1)
    for uid, totals in out.items():
        totals['NOT_MARKED'] = max(0, elapsed - sum(totals[s] for s in STATUSES))
    return out


def loss_of_pay(basic_salary, totals):
    """(days, amount): basic / days in month x (absent + half of half days + unpaid leave)."""
    days = (Decimal(totals.get('ABSENT', 0)) + Decimal(totals.get('HALF_DAY', 0)) / 2
            + Decimal(totals.get('UNPAID_LEAVE', 0)))
    if not days or not basic_salary:
        return float(days), 0.0
    amount = (Decimal(str(basic_salary)) / Decimal(totals['days']) * days).quantize(Decimal('0.01'), ROUND_HALF_UP)
    return float(days), float(amount)


class StaffAttendanceService:

    @staticmethod
    def get_day(skid, day):
        day = _parse_day(day)
        with switch_to_institution_db(skid) as session:
            ensure_tables(session)
            members = staff_members(session)
            ids = [u.id for u, _ in members]
            records = {r.user_id: r for r in session.query(StaffAttendance).filter(
                StaffAttendance.date == day, StaffAttendance.user_id.in_(ids or [-1])).all()}
            leave = approved_staff_leave(session, ids, day, day)
            audit_ids = {x for r in records.values() for x in (r.marked_by, r.updated_by) if x}
            names = {u.id: _name(u) for u in session.query(InstitutionUsers).filter(
                InstitutionUsers.id.in_(audit_ids or [-1])).all()}
            last = max(records.values(), key=lambda r: r.updated_at or r.created_at, default=None)
            return {
                'date': day.isoformat(),
                'is_marked': bool(records),
                'last_saved_by': names.get(last.updated_by or last.marked_by) if last else None,
                'last_saved_at': (last.updated_at or last.created_at).isoformat() + 'Z' if last else None,
                'staff': [{
                    'user_id': u.id,
                    'name': _name(u),
                    'email': u.email,
                    'role_name': role.role_name,
                    'status': records[u.id].status if u.id in records else None,
                    'remarks': records[u.id].remarks if u.id in records else None,
                    'on_leave': leave.get(u.id, {}).get(day),
                    'unpaid_leave': (leave.get(u.id, {}).get(day) or '').endswith('(unpaid)'),
                } for u, role in members],
            }

    @staticmethod
    def save_day(skid, day, records, actor_id):
        day = _parse_day(day)
        if day > date.today():
            raise StaffAttendanceError("Attendance can't be marked for a future date")
        if not isinstance(records, list) or not records:
            raise StaffAttendanceError('Nothing to save')
        with switch_to_institution_db(skid) as session:
            ensure_tables(session)
            staff_ids = {u.id for u, _ in staff_members(session)}
            clean = {}
            for r in records:
                try:
                    uid = int(r.get('user_id'))
                except (TypeError, ValueError, AttributeError):
                    raise StaffAttendanceError('Each record needs a user_id')
                if uid not in staff_ids:
                    raise StaffAttendanceError('Attendance can only be saved for active staff members')
                remarks = (str(r.get('remarks') or '').strip() or None)
                if remarks and len(remarks) > REMARKS_MAX:
                    raise StaffAttendanceError(f'Remarks can be at most {REMARKS_MAX} characters')
                clean[uid] = (_status(r.get('status')), remarks)
            existing = {a.user_id: a for a in session.query(StaffAttendance).filter(
                StaffAttendance.date == day, StaffAttendance.user_id.in_(list(clean))).all()}
            now = datetime.utcnow()
            for uid, (status, remarks) in clean.items():
                row = existing.get(uid)
                if row:
                    if row.status != status or (row.remarks or None) != remarks:
                        row.status, row.remarks, row.updated_by, row.updated_at = status, remarks, actor_id, now
                else:
                    session.add(StaffAttendance(user_id=uid, date=day, status=status, remarks=remarks,
                                                marked_by=actor_id, updated_by=actor_id))
            session.commit()
            return {'saved': len(clean), 'date': day.isoformat()}

    @staticmethod
    def register(skid, year, month):
        start, end, days = _month(year, month)
        with switch_to_institution_db(skid) as session:
            ensure_tables(session)
            members = staff_members(session)
            ids = [u.id for u, _ in members]
            grid = {}
            unpaid = unpaid_leave_dates(session, ids, start, end)
            for r in session.query(StaffAttendance).filter(
                    StaffAttendance.user_id.in_(ids or [-1]), StaffAttendance.date >= start, StaffAttendance.date <= end).all():
                status = 'UNPAID_LEAVE' if r.status == 'LEAVE' and r.date in unpaid.get(r.user_id, ()) else r.status
                grid.setdefault(r.user_id, {})[r.date.day] = status
            totals = month_summaries(session, ids, start.year, start.month)
            return {
                'year': start.year, 'month': start.month, 'days': days,
                'staff': [{'user_id': u.id, 'name': _name(u), 'role_name': role.role_name,
                           'days': {str(d): s for d, s in grid.get(u.id, {}).items()},
                           'totals': totals[u.id]} for u, role in members],
            }

    @staticmethod
    def my_month(skid, user, year, month):
        if not user.institution_user_id:
            raise StaffAttendanceError('Only institution accounts have staff attendance', 403)
        start, end, days = _month(year, month)
        with switch_to_institution_db(skid) as session:
            ensure_tables(session)
            me = int(user.institution_user_id)
            rows = session.query(StaffAttendance).filter(
                StaffAttendance.user_id == me, StaffAttendance.date >= start, StaffAttendance.date <= end,
            ).order_by(StaffAttendance.date).all()
            leave = approved_staff_leave(session, [me], start, end).get(me, {})
            return {
                'year': start.year, 'month': start.month, 'days': days,
                'records': [{'date': r.date.isoformat(), 'status': r.status, 'remarks': r.remarks} for r in rows],
                'approved_leave_days': sorted(d.isoformat() for d in leave),
                'unpaid_leave_days': sorted(d.isoformat() for d, label in leave.items() if label.endswith('(unpaid)')),
                'totals': month_summaries(session, [me], start.year, start.month)[me],
            }


# ---------------------------------------------------------------- salary payments

def salary_attendance(session, payments):
    """{payment_id: {'attendance': totals, 'loss_of_pay_days': n, 'loss_of_pay_suggested': amount,
                     'loss_of_pay_applied': amount or None}} for the Salary Payments list."""
    try:
        ensure_tables(session)
    except Exception:
        session.rollback()
        return {}
    by_month = {}
    for p in payments:
        by_month.setdefault((p.payment_year, p.payment_month), []).append(p)
    out = {}
    for (year, month), group in by_month.items():
        try:
            totals = month_summaries(session, {p.staff_id for p in group}, year, month)
        except StaffAttendanceError:
            continue
        for p in group:
            t = totals.get(p.staff_id)
            lop_days, lop_amount = loss_of_pay(p.basic_salary, t)
            applied = (p.deductions_applied or {}).get(LOP_KEY)
            out[p.id] = {'attendance': t, 'loss_of_pay_days': lop_days, 'loss_of_pay_suggested': lop_amount,
                         'loss_of_pay_applied': float(applied) if applied is not None else None}
    return out


def apply_loss_of_pay(skid, payment_id, apply):
    """Add (apply=True, at the current suggestion) or remove the loss-of-pay deduction on a pending payment."""
    from app.models.tenant.ExpenseModels import SalaryPayment
    with switch_to_institution_db(skid) as session:
        ensure_tables(session)
        payment = session.query(SalaryPayment).filter_by(id=int(payment_id)).first()
        if not payment:
            raise StaffAttendanceError('Payment not found', 404)
        if payment.status != 'pending':
            raise StaffAttendanceError('Loss of pay can only be changed before the salary is paid')
        deductions = dict(payment.deductions_applied or {})
        if apply:
            totals = month_summaries(session, [payment.staff_id], payment.payment_year, payment.payment_month)[payment.staff_id]
            _, amount = loss_of_pay(payment.basic_salary, totals)
            if not amount:
                raise StaffAttendanceError('No absences or half days this month, so there is no loss of pay')
            deductions[LOP_KEY] = amount
        else:
            deductions.pop(LOP_KEY, None)
        total_deductions = sum(Decimal(str(v or 0)) for v in deductions.values())
        payment.deductions_applied = deductions
        payment.net_amount_paid = max(Decimal('0'), Decimal(str(payment.gross_amount)) - total_deductions)
        session.commit()
        return {'id': payment.id, 'deductions_applied': deductions, 'net_amount_paid': float(payment.net_amount_paid)}
