/**
 * A staff member's own attendance for a month: totals, a calendar coloured by status, and remarks.
 */
import { FC, useEffect, useMemo, useState } from 'react';
import { MyStaffMonth, staffAttendanceService } from '../../services/modules/staffAttendanceService';

const STYLE: Record<string, { label: string; cell: string; dot: string }> = {
    PRESENT: { label: 'Present', cell: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200', dot: 'bg-emerald-500' },
    ABSENT: { label: 'Absent', cell: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200', dot: 'bg-red-500' },
    LATE: { label: 'Late', cell: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200', dot: 'bg-amber-500' },
    HALF_DAY: { label: 'Half day', cell: 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-200', dot: 'bg-orange-500' },
    LEAVE: { label: 'Leave', cell: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200', dot: 'bg-blue-500' },
};
const pad = (n: number) => String(n).padStart(2, '0');
const ymd = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

const StaffMonthView: FC = () => {
    const [month, setMonth] = useState(() => {
        const now = new Date();
        return new Date(now.getFullYear(), now.getMonth(), 1);
    });
    const [data, setData] = useState<MyStaffMonth | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const last = useMemo(() => new Date(month.getFullYear(), month.getMonth() + 1, 0), [month]);
    const isCurrentMonth = useMemo(() => {
        const now = new Date();
        return now.getFullYear() === month.getFullYear() && now.getMonth() === month.getMonth();
    }, [month]);

    useEffect(() => {
        let cancelled = false;
        setLoading(true);
        setError('');
        staffAttendanceService.getMine(month.getFullYear(), month.getMonth() + 1)
            .then((d) => !cancelled && setData(d))
            .catch((e: unknown) => { if (!cancelled) { setData(null); setError((e as Error)?.message || 'Failed to load attendance'); } })
            .finally(() => !cancelled && setLoading(false));
        return () => { cancelled = true; };
    }, [month]);

    const byDate = useMemo(() => new Map((data?.records || []).map((r) => [r.date, r])), [data]);
    const leaveDays = useMemo(() => new Set(data?.approved_leave_days || []), [data]);
    const unpaidDays = useMemo(() => new Set(data?.unpaid_leave_days || []), [data]);
    const cells = useMemo(() => {
        const lead = (month.getDay() + 6) % 7;
        const out: (Date | null)[] = Array.from({ length: lead }, () => null);
        for (let d = 1; d <= last.getDate(); d++) out.push(new Date(month.getFullYear(), month.getMonth(), d));
        while (out.length % 7) out.push(null);
        return out;
    }, [month, last]);
    const today = ymd(new Date());
    const withRemarks = (data?.records || []).filter((r) => r.remarks).sort((a, b) => (a.date < b.date ? 1 : -1));
    const t = data?.totals;

    return (
        <div className="space-y-4" data-testid="staff-attendance">
            <div className="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800">
                <button type="button" onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))}
                    className="rounded-lg px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-700">‹ Prev</button>
                <p className="text-base font-semibold text-gray-900 dark:text-white">{month.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })}</p>
                <button type="button" disabled={isCurrentMonth} onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))}
                    className="rounded-lg px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100 disabled:opacity-40 dark:text-gray-200 dark:hover:bg-gray-700">Next ›</button>
            </div>

            {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

            <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
                {(['PRESENT', 'ABSENT', 'LATE', 'HALF_DAY', 'LEAVE'] as const).map((key) => (
                    <div key={key} className="rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800">
                        <p className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
                            <span className={`inline-block h-2 w-2 rounded-full ${STYLE[key].dot}`} />{STYLE[key].label}
                        </p>
                        <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">{loading ? '…' : t ? t[key] : 0}</p>
                    </div>
                ))}
                {!!t?.UNPAID_LEAVE && (
                    <div className="rounded-lg border border-purple-200 bg-purple-50 p-3 dark:border-purple-800 dark:bg-purple-900/20">
                        <p className="text-xs text-purple-700 dark:text-purple-300">Unpaid leave</p>
                        <p className="mt-1 text-2xl font-bold text-purple-900 dark:text-purple-100">{t.UNPAID_LEAVE}</p>
                    </div>
                )}
                <div className="rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800">
                    <p className="text-xs text-gray-500 dark:text-gray-400">Not marked</p>
                    <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">{loading ? '…' : t ? t.NOT_MARKED : 0}</p>
                </div>
            </div>

            <div className="rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800">
                <div className="grid grid-cols-7 gap-1 text-center text-xs font-medium text-gray-500 dark:text-gray-400">
                    {WEEKDAYS.map((d) => <div key={d} className="py-1">{d}</div>)}
                </div>
                <div className="grid grid-cols-7 gap-1">
                    {cells.map((day, i) => {
                        if (!day) return <div key={`e${i}`} />;
                        const key = ymd(day);
                        const rec = byDate.get(key);
                        const style = rec ? STYLE[rec.status] : undefined;
                        const leaveOnly = !rec && leaveDays.has(key);
                        const unpaid = unpaidDays.has(key);
                        return (
                            <div key={key} data-status={rec?.status || ''}
                                title={`${rec ? `${style?.label || rec.status}${rec.remarks ? ` - ${rec.remarks}` : ''}` : leaveOnly ? 'Approved leave' : ''}${unpaid ? ' (unpaid)' : ''}`}
                                className={`flex aspect-square items-center justify-center rounded-md text-sm ${style ? style.cell : leaveOnly ? 'border border-dashed border-blue-400 text-blue-600 dark:text-blue-300' : 'text-gray-400 dark:text-gray-500'} ${key === today ? 'ring-2 ring-blue-500' : ''} ${unpaid ? 'ring-2 ring-purple-400' : ''}`}>
                                {day.getDate()}
                            </div>
                        );
                    })}
                </div>
                <div className="mt-3 flex flex-wrap gap-3 text-xs text-gray-500 dark:text-gray-400">
                    {Object.values(STYLE).map((s) => (
                        <span key={s.label} className="flex items-center gap-1.5"><span className={`inline-block h-2.5 w-2.5 rounded-full ${s.dot}`} />{s.label}</span>
                    ))}
                    <span>Dashed: approved leave not yet marked · Purple ring: unpaid leave · Unmarked days are grey</span>
                </div>
            </div>

            {withRemarks.length > 0 && (
                <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
                    <p className="mb-2 text-sm font-semibold text-gray-900 dark:text-white">Remarks</p>
                    <ul className="space-y-2">
                        {withRemarks.map((r) => (
                            <li key={r.date} className="text-sm text-gray-700 dark:text-gray-300">
                                <span className="font-medium">{new Date(r.date + 'T00:00:00').toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}</span>
                                {' · '}{STYLE[r.status]?.label || r.status}{' · '}{r.remarks}
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
};

export default StaffMonthView;
