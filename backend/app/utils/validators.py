"""
Small input checks shared by the money / marks / attendance services.
Each raises ValueError with a message meant for the user (routes turn ValueError into a 400).
"""
from datetime import date, datetime


def to_number(value, label):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be a number")
    if number != number or number in (float("inf"), float("-inf")):  # NaN / inf
        raise ValueError(f"{label} must be a number")
    return number


def positive_amount(value, label="Amount"):
    """A money amount greater than zero."""
    number = to_number(value, label)
    if number <= 0:
        raise ValueError(f"{label} must be greater than 0")
    return round(number, 2)


def non_negative_amount(value, label="Amount"):
    """A money amount of zero or more (e.g. an allowance or deduction)."""
    number = to_number(value, label)
    if number < 0:
        raise ValueError(f"{label} can't be negative")
    return round(number, 2)


def number_in_range(value, low, high, label):
    number = to_number(value, label)
    if number < low or number > high:
        raise ValueError(f"{label} must be between {low:g} and {high:g}")
    return number


def to_date(value, label="Date"):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise ValueError(f"{label} is not a valid date (use YYYY-MM-DD)")


def not_in_future(value, label="Date"):
    day = to_date(value, label)
    if day > date.today():
        raise ValueError(f"{label} can't be in the future")
    return day


def within_an_academic_year(tenant_session, value, label="Date"):
    """The date must fall inside one of the school's academic years; returns that year's id."""
    from app.models.tenant.AcademicYear import AcademicYear
    day = to_date(value, label)
    year = tenant_session.query(AcademicYear).filter(
        AcademicYear.start_date <= day, AcademicYear.end_date >= day
    ).first()
    if not year:
        raise ValueError(f"{label} ({day.strftime('%d %b %Y')}) isn't inside any academic year")
    return year.id
