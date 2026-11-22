/**
 * Money in Indian format: ₹6,650 for whole amounts, ₹6,650.50 when there are paise
 * (plain toLocaleString printed ₹6,650.5 - QA C29). Returns the number only; callers add the ₹ sign.
 */
export function formatAmount(value: unknown): string {
    const n = typeof value === 'number' ? value : parseFloat(String(value ?? 0));
    if (!Number.isFinite(n)) return '0';
    const whole = Math.abs(n - Math.round(n)) < 0.005;
    return n.toLocaleString('en-IN', whole
        ? { maximumFractionDigits: 0 }
        : { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
