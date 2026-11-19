/**
 * Client-side validation for bulk-student-import rows.
 * Rules mirror the backend's expectations so users see errors before round-tripping.
 */

export type ValidationStatus = 'valid' | 'error';

export interface IFieldError {
    field: string;
    message: string;
}

export interface IRowValidation {
    rowIndex: number;
    status: ValidationStatus;
    errors: IFieldError[];
}

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_RE = /^[\d+\-()\s]{7,15}$/;
const ALLOWED_GENDER = ['Male', 'Female', 'Other'];

const REQUIRED_FIELDS = ['first_name', 'last_name', 'email', 'phone'] as const;
const DATE_FIELDS = ['date_of_birth', 'admission_date'] as const;

export function validateRow(
    row: Record<string, any>,
    allRows: Record<string, any>[],
    idx: number
): IRowValidation {
    const errors: IFieldError[] = [];
    const get = (k: string) => String(row[k] ?? '').trim();

    // Required fields
    for (const f of REQUIRED_FIELDS) {
        if (!get(f)) errors.push({ field: f, message: 'Required' });
    }

    // Email format
    const email = get('email');
    if (email && !EMAIL_RE.test(email)) {
        errors.push({ field: 'email', message: 'Invalid email format' });
    }

    // Phone format
    const phone = get('phone');
    if (phone && !PHONE_RE.test(phone)) {
        errors.push({ field: 'phone', message: 'Invalid phone (7-15 chars, digits/symbols)' });
    }

    // Date fields — if provided, must be ISO
    for (const f of DATE_FIELDS) {
        const v = get(f);
        if (v && !ISO_DATE.test(v)) {
            errors.push({ field: f, message: 'Must be YYYY-MM-DD' });
        }
    }

    // Gender enum (optional)
    const gender = get('gender');
    if (gender && !ALLOWED_GENDER.includes(gender)) {
        errors.push({ field: 'gender', message: 'Must be Male, Female or Other' });
    }

    // Duplicate email within file
    if (email) {
        const dupIdx = allRows.findIndex(
            (r, i) => i !== idx && String(r.email ?? '').trim().toLowerCase() === email.toLowerCase()
        );
        if (dupIdx >= 0) {
            errors.push({ field: 'email', message: `Duplicate of row ${dupIdx + 1}` });
        }
    }

    // Duplicate username within file
    const username = get('username');
    if (username) {
        const dupIdx = allRows.findIndex(
            (r, i) =>
                i !== idx && String(r.username ?? '').trim().toLowerCase() === username.toLowerCase()
        );
        if (dupIdx >= 0) {
            errors.push({ field: 'username', message: `Duplicate of row ${dupIdx + 1}` });
        }
    }

    return {
        rowIndex: idx,
        status: errors.length === 0 ? 'valid' : 'error',
        errors,
    };
}

export function validateAll(rows: Record<string, any>[]): IRowValidation[] {
    return rows.map((r, i) => validateRow(r, rows, i));
}

/** Returns a map: field → first error message for fast lookup in cell rendering. */
export function fieldErrorMap(v: IRowValidation): Record<string, string> {
    const map: Record<string, string> = {};
    for (const e of v.errors) {
        if (!map[e.field]) map[e.field] = e.message;
    }
    return map;
}
