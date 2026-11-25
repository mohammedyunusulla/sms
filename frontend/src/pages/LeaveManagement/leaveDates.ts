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

/** Leave days that count against a staff balance: every day except the given off days (weekly offs / holidays) */
export const countedDays = (from: string, to: string, offDays: Set<string> = new Set()): number => {
    if (!from || !to || to < from) return 0;
    let n = 0;
    for (let d = from; d <= to; d = addDays(d, 1)) {
        if (!offDays.has(d)) n += 1;
    }
    return n;
};

export const formatRange = (from: string, to: string): string =>
    from === to ? formatDay(from) : `${formatDay(from)} – ${formatDay(to)}`;
