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


def exam_setup_marks(has_internal_external, internal_max, external_max, total_max, passing, weightage=None):
    """
    Maximum / passing marks of an exam subject setup. Returns the cleaned
    (internal_max, external_max, total_max, passing, weightage).
    """
    total_max = to_number(total_max, "Total marks")
    if total_max <= 0 or total_max != int(total_max):
        raise ValueError("Total marks must be a whole number greater than 0")
    if has_internal_external:
        internal_max = to_number(internal_max or 0, "Internal marks")
        external_max = to_number(external_max or 0, "External marks")
        if internal_max < 0 or external_max < 0 or internal_max != int(internal_max) or external_max != int(external_max):
            raise ValueError("Internal and external marks must be whole numbers of 0 or more")
        if internal_max + external_max != total_max:
            raise ValueError("Internal + External marks must equal Total marks")
    else:
        internal_max = external_max = 0
    passing = to_number(passing, "Passing marks")
    if passing < 0 or passing > total_max or passing != int(passing):
        raise ValueError(f"Passing marks must be a whole number between 0 and the total ({total_max:g})")
    if weightage is not None:
        weightage = to_number(weightage, "Weightage")
        if weightage <= 0 or weightage > 100:
            raise ValueError("Weightage must be more than 0 and at most 100")
    return int(internal_max), int(external_max), int(total_max), int(passing), weightage


def student_marks(config, entry, who):
    """
    One student's marks against an exam subject setup. Absent students get 0.
    Returns (internal, external, total).
    """
    if entry.get("is_absent"):
        return 0, 0, 0
    total = to_number(entry.get("total_marks"), f"Total marks for {who}")
    if total < 0 or total > config.total_max_marks:
        raise ValueError(f"Marks for {who} must be between 0 and {config.total_max_marks}")
    if not config.has_internal_external:
        return 0, 0, total
    internal = to_number(entry.get("internal_marks") or 0, f"Internal marks for {who}")
    external = to_number(entry.get("external_marks") or 0, f"External marks for {who}")
    if internal < 0 or internal > config.internal_max_marks:
        raise ValueError(f"Internal marks for {who} must be between 0 and {config.internal_max_marks}")
    if external < 0 or external > config.external_max_marks:
        raise ValueError(f"External marks for {who} must be between 0 and {config.external_max_marks}")
    if abs(internal + external - total) > 0.001:
        raise ValueError(f"Internal + external marks for {who} ({internal:g} + {external:g}) must equal the total ({total:g})")
    return internal, external, total
