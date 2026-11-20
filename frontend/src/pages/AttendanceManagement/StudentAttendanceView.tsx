/**
 * One student's attendance for a month: totals, a calendar coloured by status, and the days with remarks.
 * Used by students (their own) and parents (the child picked in the header).
 */
import { FC, useEffect, useMemo, useState } from 'react';
import { attendanceService } from '../../services/modules/attendanceService';

type DayRecord = { date: string; status: string; remarks?: string | null };
type Stats = { total_days: number; present_count: number; absent_count: number; late_count: number; leave_count: number; attendance_percentage: number };

const STATUS_STYLE: Record<string, { label: string; cell: string; dot: string }> = {
    PRESENT: { label: 'Present', cell: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200', dot: 'bg-emerald-500' },
    ABSENT: { label: 'Absent', cell: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200', dot: 'bg-red-500' },
    LATE: { label: 'Late', cell: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200', dot: 'bg-amber-500' },
    LEAVE: { label: 'Leave', cell: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200', dot: 'bg-blue-500' },
};
const statusKey = (status: string) => {
    const s = (status || '').toUpperCase().replace(/[\s-]+/g, '_');
    return s === 'HALF_DAY' ? 'LATE' : s === 'EXCUSED' ? 'LEAVE' : s;
};
const pad = (n: number) => String(n).padStart(2, '0');
const ymd = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

const StudentAttendanceView: FC<{ studentId: number }> = ({ studentId }) => {
    const [month, setMonth] = useState(() => {
        const now = new Date();
        return new Date(now.getFullYear(), now.getMonth(), 1);
    });
    const [records, setRecords] = useState<DayRecord[]>([]);
    const [stats, setStats] = useState<Stats | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const first = month;
    const last = useMemo(() => new Date(month.getFullYear(), month.getMonth() + 1, 0), [month]);
    const isCurrentMonth = useMemo(() => {
        const now = new Date();
        return now.getFullYear() === month.getFullYear() && now.getMonth() === month.getMonth();
    }, [month]);

    useEffect(() => {
        let cancelled = false;
        setLoading(true);
        setError('');
        attendanceService
            .getStudentAttendance(studentId, ymd(first), ymd(last))
            .then((data) => {
                if (cancelled) return;
                setRecords((data.records || []) as DayRecord[]);
                setStats((data.statistics as Stats) || null);
            })
            .catch((e: unknown) => {
                if (cancelled) return;
                setRecords([]);
                setStats(null);
                setError((e as Error)?.message || 'Failed to load attendance');
            })
            .finally(() => !cancelled && setLoading(false));
        return () => {
            cancelled = true;
        };
    }, [studentId, first, last]);

    const byDate = useMemo(() => new Map(records.map((r) => [r.date, r])), [records]);
    const cells = useMemo(() => {
        const lead = (first.getDay() + 6) % 7; // Monday first
        const out: (Date | null)[] = Array.from({ length: lead }, () => null);
        for (let d = 1; d <= last.getDate(); d++) out.push(new Date(first.getFullYear(), first.getMonth(), d));
        while (out.length % 7) out.push(null);
        return out;
    }, [first, last]);
    const withRemarks = [...records].filter((r) => r.remarks).sort((a, b) => (a.date < b.date ? 1 : -1));
    const monthLabel = month.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' });
    const today = ymd(new Date());

    return (
        <div className="space-y-4" data-testid="student-attendance">
            <div className="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800">
                <button type="button" aria-label="Previous month" onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))}
                    className="rounded-lg px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-700">‹ Prev</button>
                <p className="text-base font-semibold text-gray-900 dark:text-white" data-testid="attendance-month">{monthLabel}</p>
                <button type="button" aria-label="Next month" disabled={isCurrentMonth} onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))}
                    className="rounded-lg px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100 disabled:opacity-40 dark:text-gray-200 dark:hover:bg-gray-700">Next ›</button>
            </div>

            {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-5" data-testid="attendance-totals">
                <div className="col-span-2 rounded-lg border border-gray-200 bg-white p-4 sm:col-span-1 dark:border-gray-700 dark:bg-gray-800">
                    <p className="text-xs text-gray-500 dark:text-gray-400">Attendance</p>
                    <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">{loading ? '…' : stats && stats.total_days ? `${stats.attendance_percentage}%` : '-'}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">{stats?.total_days ? `${stats.total_days} days marked` : 'No days marked'}</p>
                </div>
                {(['PRESENT', 'ABSENT', 'LATE', 'LEAVE'] as const).map((key) => (
                    <div key={key} className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
                        <p className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
                            <span className={`inline-block h-2 w-2 rounded-full ${STATUS_STYLE[key].dot}`} />{STATUS_STYLE[key].label}
                        </p>
                        <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">
                            {loading ? '…' : stats ? stats[`${key.toLowerCase()}_count` as keyof Stats] : 0}
                        </p>
                    </div>
                ))}
            </div>

            <div className="rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800">
                <div className="grid grid-cols-7 gap-1 text-center text-xs font-medium text-gray-500 dark:text-gray-400">
                    {WEEKDAYS.map((d) => <div key={d} className="py-1">{d}</div>)}
                </div>
                <div className="grid grid-cols-7 gap-1" data-testid="attendance-calendar">
                    {cells.map((day, i) => {
                        if (!day) return <div key={`e${i}`} />;
                        const key = ymd(day);
                        const rec = byDate.get(key);
                        const style = rec ? STATUS_STYLE[statusKey(rec.status)] : undefined;
                        return (
                            <div key={key} title={rec ? `${style?.label || rec.status}${rec.remarks ? ` - ${rec.remarks}` : ''}` : ''}
                                data-status={rec ? statusKey(rec.status) : ''}
                                className={`flex aspect-square items-center justify-center rounded-md text-sm ${style ? style.cell : 'text-gray-400 dark:text-gray-500'} ${key === today ? 'ring-2 ring-blue-500' : ''}`}>
                                {day.getDate()}
                            </div>
                        );
                    })}
                </div>
                <div className="mt-3 flex flex-wrap gap-3 text-xs text-gray-500 dark:text-gray-400">
                    {Object.values(STATUS_STYLE).map((s) => (
                        <span key={s.label} className="flex items-center gap-1.5"><span className={`inline-block h-2.5 w-2.5 rounded-full ${s.dot}`} />{s.label}</span>
                    ))}
                    <span>Unmarked days are grey</span>
                </div>
            </div>

            {withRemarks.length > 0 && (
                <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
                    <p className="mb-2 text-sm font-semibold text-gray-900 dark:text-white">Teacher's remarks</p>
                    <ul className="space-y-2" data-testid="attendance-remarks">
                        {withRemarks.map((r) => (
                            <li key={r.date} className="text-sm text-gray-700 dark:text-gray-300">
                                <span className="font-medium">{new Date(r.date + 'T00:00:00').toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}</span>
                                {' · '}{STATUS_STYLE[statusKey(r.status)]?.label || r.status}{' · '}{r.remarks}
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
};

export default StudentAttendanceView;
