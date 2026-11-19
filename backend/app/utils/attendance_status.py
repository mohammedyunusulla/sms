"""
Attendance status rules.

Stored/standard values are UPPERCASE, matching the frontend: PRESENT, ABSENT, LATE, LEAVE.
Older rows may be title case ('Present') or lowercase, so every read compares case-insensitively.
"""
from sqlalchemy import func

VALID_ATTENDANCE_STATUSES = ('PRESENT', 'ABSENT', 'LATE', 'LEAVE')
# Legacy values that count as leave when reading
_LEAVE_ALIASES = {'LEAVE', 'MEDICAL_LEAVE', 'EXCUSED'}


def normalize_status(value):
    """For writes: return the standard UPPERCASE status, or raise ValueError for anything else."""
    status = str(value or '').strip().upper()
    if status not in VALID_ATTENDANCE_STATUSES:
        raise ValueError(
            f"Invalid attendance status '{value}'. Must be one of: {', '.join(VALID_ATTENDANCE_STATUSES)}"
        )
    return status


def status_key(value):
    """For reads: map any stored spelling to PRESENT / ABSENT / LATE / LEAVE (others returned uppercased)."""
    status = str(value or '').strip().upper()
    return 'LEAVE' if status in _LEAVE_ALIASES else status


def status_column(column):
    """For SQL filters: case-insensitive version of a status column, e.g. status_column(Attendance.status) == 'ABSENT'."""
    return func.upper(column)
