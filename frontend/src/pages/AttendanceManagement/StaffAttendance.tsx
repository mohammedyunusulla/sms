/**
 * Mark staff attendance for a day. Everyone starts as Present (or Leave, with approved leave) until the day is
 * saved; after that the saved statuses load and can be edited.
 */
import { FC, useCallback, useEffect, useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import { Button, FormInput, FormSelect, LoadingSpinner, PageHeader } from '../../components';
import {
    errorMessage, STAFF_STATUS_LABEL, STAFF_STATUSES, staffAttendanceService, StaffDay, StaffStatus,
} from '../../services/modules/staffAttendanceService';
import { localDay } from '../LeaveManagement/leaveDates';

const TONE: Record<StaffStatus, string> = {
    PRESENT: 'bg-emerald-600 text-white border-emerald-600',
    ABSENT: 'bg-red-600 text-white border-red-600',
    LATE: 'bg-amber-500 text-white border-amber-500',
    HALF_DAY: 'bg-orange-500 text-white border-orange-500',
    LEAVE: 'bg-blue-600 text-white border-blue-600',
};

interface Row { status: StaffStatus; remarks: string }

const StaffAttendance: FC = () => {
    const [date, setDate] = useState(localDay());
    const [day, setDay] = useState<StaffDay | null>(null);
    const [rows, setRows] = useState<Record<number, Row>>({});
    const [dirty, setDirty] = useState(false);
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [role, setRole] = useState('');
    const [search, setSearch] = useState('');

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const data = await staffAttendanceService.getDay(date);
            setDay(data);
            const next: Record<number, Row> = {};
            data.staff.forEach((s) => {
                next[s.user_id] = {
                    status: s.status || (s.on_leave ? 'LEAVE' : 'PRESENT'),
                    remarks: s.status ? s.remarks || '' : s.on_leave ? `Approved leave (${s.on_leave})` : '',
                };
            });
            setRows(next);
            setDirty(false);
        } catch (err) {
            toast.error(errorMessage(err, 'Could not load staff'));
            setDay(null);
        } finally {
            setLoading(false);
        }
    }, [date]);

    useEffect(() => {
        load();
    }, [load]);

    const roles = useMemo(() => Array.from(new Set((day?.staff || []).map((s) => s.role_name))).sort(), [day]);
    const visible = useMemo(() => {
        const q = search.trim().toLowerCase();
        return (day?.staff || []).filter((s) => (!role || s.role_name === role)
            && (!q || s.name.toLowerCase().includes(q) || (s.email || '').toLowerCase().includes(q)));
    }, [day, role, search]);
    const counts = useMemo(() => {
        const c: Record<StaffStatus, number> = { PRESENT: 0, ABSENT: 0, LATE: 0, HALF_DAY: 0, LEAVE: 0 };
        Object.values(rows).forEach((r) => { c[r.status] += 1; });
        return c;
    }, [rows]);

    const setRow = (id: number, patch: Partial<Row>) => {
        setRows((r) => ({ ...r, [id]: { ...r[id], ...patch } }));
        setDirty(true);
    };
    const markVisible = (status: StaffStatus) => {
        setRows((r) => {
            const next = { ...r };
            visible.forEach((s) => { next[s.user_id] = { ...next[s.user_id], status }; });
            return next;
        });
        setDirty(true);
    };

    const save = async () => {
        if (!day) return;
        setSaving(true);
        try {
            const res = await staffAttendanceService.saveDay(date, day.staff.map((s) => ({
                user_id: s.user_id, status: rows[s.user_id].status, remarks: rows[s.user_id].remarks.trim() || null,
            })));
            toast.success(`Attendance saved for ${res.saved} staff`);
            load();
        } catch (err) {
            toast.error(errorMessage(err, 'Could not save attendance'));
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="space-y-6">
            <PageHeader
                title="Staff Attendance"
                subtitle="Mark attendance for teachers and other staff"
                breadcrumbs={[{ label: 'Dashboard', href: '/dashboard' }, { label: 'Staff Attendance', href: '#' }]}
            />

            <div className="grid gap-3 rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800 sm:grid-cols-3">
                <FormInput label="Date" type="date" value={date} max={localDay()} onChange={(e) => e.target.value && setDate(e.target.value)} />
                <FormSelect label="Role" value={role} onChange={(e) => setRole(e.target.value)} placeholder="All roles"
                    options={roles.map((r) => ({ value: r, label: r }))} />
                <FormInput label="Search" type="search" value={search} placeholder="Name or email" onChange={(e) => setSearch(e.target.value)} />
            </div>

            {loading && !day ? (
                <div className="flex justify-center py-12"><LoadingSpinner /></div>
            ) : day && day.staff.length === 0 ? (
                <div className="rounded-lg border border-dashed border-gray-300 p-8 text-center text-gray-500 dark:border-gray-600 dark:text-gray-400">
                    No staff found. Staff are users with a role other than Student, Parent or Institution Admin.
                </div>
            ) : day ? (
                <>
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <div className="flex flex-wrap gap-2 text-sm">
                            {STAFF_STATUSES.map((s) => (
                                <span key={s} className="rounded-full bg-gray-100 px-3 py-1 text-gray-700 dark:bg-gray-700 dark:text-gray-200">
                                    {STAFF_STATUS_LABEL[s]}: <strong>{counts[s]}</strong>
                                </span>
                            ))}
                        </div>
                        <div className="flex flex-wrap gap-2">
                            <Button size="sm" variant="secondary" onClick={() => markVisible('PRESENT')}>
                                Mark {visible.length === day.staff.length ? 'all' : 'shown'} present
                            </Button>
                        </div>
                    </div>

                    <p className="text-xs text-gray-500 dark:text-gray-400">
                        {day.is_marked
                            ? `Saved${day.last_saved_by ? ` by ${day.last_saved_by}` : ''}${day.last_saved_at ? ` · ${new Date(day.last_saved_at).toLocaleString(undefined, { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })}` : ''}. Changes are saved when you press Save.`
                            : 'Not saved yet for this day: everyone starts as Present (approved leave as Leave).'}
                    </p>

                    <div className={`divide-y divide-gray-100 overflow-hidden rounded-xl border border-gray-200 bg-white dark:divide-gray-700 dark:border-gray-700 dark:bg-gray-800 ${loading ? 'opacity-60' : ''}`}>
                        {visible.map((s) => {
                            const row = rows[s.user_id];
                            if (!row) return null;
                            return (
                                <div key={s.user_id} className="flex flex-col gap-3 p-4 lg:flex-row lg:items-center">
                                    <div className="min-w-0 lg:w-64">
                                        <p className="truncate font-medium text-gray-900 dark:text-white">{s.name}</p>
                                        <p className="text-xs text-gray-500 dark:text-gray-400">
                                            {s.role_name}
                                            {s.on_leave && (
                                                <span className={`ml-2 rounded px-1.5 py-0.5 font-medium ${s.unpaid_leave
                                                    ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300'
                                                    : 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300'}`}>
                                                    {s.unpaid_leave ? 'Approved leave (unpaid)' : 'Approved leave'}
                                                </span>
                                            )}
                                        </p>
                                    </div>
                                    <div className="flex flex-wrap gap-1.5" role="radiogroup" aria-label={`Status for ${s.name}`}>
                                        {STAFF_STATUSES.map((st) => (
                                            <button key={st} type="button" role="radio" aria-checked={row.status === st}
                                                onClick={() => setRow(s.user_id, { status: st })}
                                                className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors ${row.status === st
                                                    ? TONE[st]
                                                    : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700'}`}>
                                                {STAFF_STATUS_LABEL[st]}
                                            </button>
                                        ))}
                                    </div>
                                    <input type="text" value={row.remarks} maxLength={500} placeholder="Remarks (optional)"
                                        onChange={(e) => setRow(s.user_id, { remarks: e.target.value })}
                                        className="h-9 flex-1 rounded-lg border border-gray-300 bg-white px-3 text-sm text-gray-900 focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-800 dark:text-white" />
                                </div>
                            );
                        })}
                        {visible.length === 0 && <p className="p-6 text-center text-sm text-gray-500 dark:text-gray-400">No staff match the filter.</p>}
                    </div>

                    <div className="sticky bottom-4 flex justify-end">
                        <Button onClick={save} isLoading={saving} loadingText="Saving..." disabled={saving || (!dirty && day.is_marked)}
                            className="shadow-lg">
                            {day.is_marked ? 'Save changes' : 'Save attendance'}
                        </Button>
                    </div>
                </>
            ) : null}
        </div>
    );
};

export default StaffAttendance;
