"""
Helpers for create/edit form payloads (students, parents, staff, teachers).

Forms send '' for fields the user left empty. Stored as-is, '' breaks number/date columns
(500 "invalid input syntax") and unique columns (the second blank value collides), so blank
optional fields become NULL, and required ones get a clear 400 message.
"""


def clean_payload(data, optional_fields):
    """Trim strings (except passwords) and turn blank optional fields into None."""
    cleaned = {}
    for key, value in (data or {}).items():
        if isinstance(value, str) and 'password' not in key:
            value = value.strip()
        cleaned[key] = value
    for key in optional_fields:
        if key in cleaned and cleaned[key] in ('', None):
            cleaned[key] = None
    return cleaned


def missing_fields_message(data, required):
    """required: [(key, label), ...]. Returns 'A, B are required' / 'A is required', or None."""
    missing = [label for key, label in required if not data.get(key)]
    if not missing:
        return None
    plural = len(missing) > 1 or missing[0].endswith('s')
    return f"{', '.join(missing)} {'are' if plural else 'is'} required"


def error(message, code):
    from flask import jsonify
    return jsonify({'message': message, 'status': 'error', 'code': code}), code
