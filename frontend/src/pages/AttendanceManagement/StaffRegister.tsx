/**
 * Monthly staff attendance register: staff x days, totals per person, PDF / print.
 */
import { FC, useEffect, useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import { LoadingSpinner, PageHeader, PrintActions } from '../../components';
import { errorMessage, staffAttendanceService, StaffRegister as Register } from '../../services/modules/staffAttendanceService';
import { useAuthStore } from '../../stores/authStore';
import { generateStaffRegisterPdf } from '../../prints/staffRegisterGenerator';
import type { PdfAction } from '../../prints';

const CELL: Record<string, { code: string; cls: string }> = {
    PRESENT: { code: 'P', cls: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200' },
    ABSENT: { code: 'A', cls: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200' },
    LATE: { code: 'L', cls: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200' },
    HALF_DAY: { code: 'H', cls: 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-200' },
    LEAVE: { code: 'LV', cls: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200' },
};
const TOTALS: [string, string][] = [['PRESENT', 'P'], ['ABSENT', 'A'], ['LATE', 'L'], ['HALF_DAY', 'H'], ['LEAVE', 'LV'], ['NOT_MARKED', 'NM']];

const StaffRegister: FC = () => {
    const [month, setMonth] = useState(() => {
        const now = new Date();
        return new Date(now.getFullYear(), now.getMonth(), 1);
    });
    const [data, setData] = useState<Register | null>(null);
    const [loading, setLoading] = useState(false);

    const isCurrentMonth = useMemo(() => {
        const now = new Date();
        return now.getFullYear() === month.getFullYear() && now.getMonth() === month.getMonth();
    }, [month]);
    const monthLabel = month.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' });

    useEffect(() => {
        let cancelled = false;
        setLoading(true);
        staffAttendanceService.getRegister(month.getFullYear(), month.getMonth() + 1)
            .then((d) => !cancelled && setData(d))
            .catch((err) => { if (!cancelled) { setData(null); toast.error(errorMessage(err, 'Could not load the register')); } })
            .finally(() => !cancelled && setLoading(false));
        return () => { cancelled = true; };
    }, [month]);

    const dayNums = useMemo(() => Array.from({ length: data?.days || 0 }, (_, i) => i + 1), [data]);
    const weekend = (d: number) => {
        const wd = new Date(month.getFullYear(), month.getMonth(), d).getDay();
        return wd === 0;
    };

    const print = async (action: PdfAction) => {
        if (!data) return;
        const user = useAuthStore.getState().user;
        try {
            await generateStaffRegisterPdf({
                monthLabel,
                days: data.days,
                rows: data.staff.map((s) => ({ name: s.name, role: s.role_name, days: s.days, totals: s.totals as unknown as Record<string, number> })),
            }, {
                institutionName: user?.institution_name || 'Institution',
                institutionAddress: '', institutionPhone: '', institutionEmail: user?.email || '', logo: null,
                generatedBy: user?.full_name || 'System',
            }, action);
        } catch (err) {
            toast.error(errorMessage(err, 'Could not create the PDF'));
        }
    };

    return (
        <div className="space-y-6">
            <PageHeader
                title="Staff Attendance Register"
                subtitle="Month view of staff attendance with totals"
                breadcrumbs={[{ label: 'Dashboard', href: '/dashboard' }, { label: 'Staff Register', href: '#' }]}
                actions={<div className="flex gap-2"><PrintActions onAction={print} disabled={!data || data.staff.length === 0} /></div>}
            />

            <div className="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800">
                <button type="button" onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))}
                    className="rounded-lg px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-700">‹ Prev</button>
                <p className="text-base font-semibold text-gray-900 dark:text-white">{monthLabel}</p>
                <button type="button" disabled={isCurrentMonth} onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))}
                    className="rounded-lg px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100 disabled:opacity-40 dark:text-gray-200 dark:hover:bg-gray-700">Next ›</button>
            </div>

            {loading && !data ? (
                <div className="flex justify-center py-12"><LoadingSpinner /></div>
            ) : data && data.staff.length === 0 ? (
                <div className="rounded-lg border border-dashed border-gray-300 p-8 text-center text-gray-500 dark:border-gray-600 dark:text-gray-400">No staff found.</div>
            ) : data ? (
                <div className={`overflow-x-auto rounded-xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800 ${loading ? 'opacity-60' : ''}`}>
                    <table className="min-w-full text-xs">
                        <thead>
                            <tr className="bg-gray-50 text-gray-600 dark:bg-gray-700/50 dark:text-gray-300">
                                <th className="sticky left-0 z-10 bg-gray-50 px-3 py-2 text-left font-semibold dark:bg-gray-700">Staff</th>
                                {dayNums.map((d) => (
                                    <th key={d} className={`w-7 px-0.5 py-2 text-center font-medium ${weekend(d) ? 'text-red-500' : ''}`}>{d}</th>
                                ))}
                                {TOTALS.map(([k, label]) => <th key={k} className="bg-gray-100 px-1.5 py-2 text-center font-semibold dark:bg-gray-700">{label}</th>)}
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                            {data.staff.map((s) => (
                                <tr key={s.user_id}>
                                    <td className="sticky left-0 z-10 whitespace-nowrap bg-white px-3 py-2 dark:bg-gray-800">
                                        <p className="font-medium text-gray-900 dark:text-white">{s.name}</p>
                                        <p className="text-[11px] text-gray-500 dark:text-gray-400">{s.role_name}</p>
                                    </td>
                                    {dayNums.map((d) => {
                                        const c = CELL[s.days[String(d)]];
                                        return (
                                            <td key={d} className="px-0.5 py-1 text-center">
                                                {c ? <span className={`inline-block min-w-[1.5rem] rounded px-0.5 py-0.5 font-semibold ${c.cls}`}>{c.code}</span>
                                                    : <span className="text-gray-300 dark:text-gray-600">·</span>}
                                            </td>
                                        );
                                    })}
                                    {TOTALS.map(([k]) => (
                                        <td key={k} className="bg-gray-50 px-1.5 py-2 text-center font-semibold text-gray-800 dark:bg-gray-700/40 dark:text-gray-100">
                                            {(s.totals as unknown as Record<string, number>)[k] ?? 0}
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    <p className="border-t border-gray-100 px-3 py-2 text-[11px] text-gray-500 dark:border-gray-700 dark:text-gray-400">
                        P Present · A Absent · L Late · H Half day · LV Leave · NM Not marked (days up to today with no entry) · Sundays in red
                    </p>
                </div>
            ) : null}
        </div>
    );
};

export default StaffRegister;
