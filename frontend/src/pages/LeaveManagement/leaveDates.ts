/** Date helpers for the leave pages (days are YYYY-MM-DD strings) */

/** YYYY-MM-DD in the device's own time zone (toISOString would give the UTC day) */
export const localDay = (d: Date = new Date()): string => {
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
};

export const addDays = (day: string, n: number): string => {
    const [y, m, d] = day.split('-').map(Number);
    return localDay(new Date(y, m - 1, d + n));
};

export const formatDay = (day: string): string => {
    const [y, m, d] = day.split('-').map(Number);
    return new Date(y, m - 1, d).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
};

export const formatRange = (from: string, to: string): string =>
    from === to ? formatDay(from) : `${formatDay(from)} – ${formatDay(to)}`;
