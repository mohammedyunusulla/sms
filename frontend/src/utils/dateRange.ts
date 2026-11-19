/**
 * "1 Jun – 19 Nov 2026" (or "1 Dec 2025 – 19 Nov 2026" across years) from two ISO dates.
 * Returns '' when either date is missing or invalid.
 */
export const formatDateRange = (from?: string | null, to?: string | null): string => {
    if (!from || !to) return '';
    const start = new Date(`${from.slice(0, 10)}T00:00:00`);
    const end = new Date(`${to.slice(0, 10)}T00:00:00`);
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return '';
    const dayMonth: Intl.DateTimeFormatOptions = { day: 'numeric', month: 'short' };
    const full: Intl.DateTimeFormatOptions = { day: 'numeric', month: 'short', year: 'numeric' };
    const startText = start.toLocaleDateString('en-GB', start.getFullYear() === end.getFullYear() ? dayMonth : full);
    return `${startText} – ${end.toLocaleDateString('en-GB', full)}`;
};
