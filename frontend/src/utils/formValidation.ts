/**
 * Shared checks for the create/edit user forms (students, parents, staff).
 * Password rules match the backend's validate_password (app/utils/helpers.py).
 */

export const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export const isValidEmail = (value: string): boolean => EMAIL_PATTERN.test(value.trim());

/** 10 digits, ignoring spaces and dashes. */
export const isValidPhone = (value: string): boolean => /^\d{10}$/.test(value.replace(/[\s-]/g, ''));

/** Returns the first broken password rule, or null when the password is acceptable. */
export const passwordProblem = (password: string): string | null => {
    if (!password) return 'Password is required';
    if (password.length < 8) return 'Password must be at least 8 characters';
    if (!/[A-Z]/.test(password)) return 'Password must contain an uppercase letter';
    if (!/[a-z]/.test(password)) return 'Password must contain a lowercase letter';
    if (!/[0-9]/.test(password)) return 'Password must contain a digit';
    return null;
};

/** Copy of `data` with blank-string values of `keys` replaced by null ('' breaks number/date/unique columns). */
export const blanksToNull = <T extends Record<string, unknown>>(data: T, keys: readonly string[]): T => {
    const copy: Record<string, unknown> = { ...data };
    for (const key of keys) {
        if (typeof copy[key] === 'string' && (copy[key] as string).trim() === '') copy[key] = null;
    }
    return copy as T;
};

/** Tailwind classes for a text input / select / textarea, red when it has an error. */
export const fieldInputClass = (hasError: boolean): string =>
    `w-full px-4 py-2 border rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white disabled:opacity-50 ${hasError
        ? 'border-red-500 dark:border-red-500 focus:ring-red-500'
        : 'border-gray-300 dark:border-gray-600'}`;
