/**
 * Calendar: a month grid (or an agenda list) with holidays, weekly offs, exams and leave, limited to what this
 * person may see. The Institution Admin and "Manage Holidays" holders add holidays by picking a day, and edit,
 * confirm, move or delete them from the day panel; weekly offs are under "Calendar settings".
 * New kinds of items only need a type from /api/calendar/events and a style here.
 */
import { FC, useCallback, useEffect, useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import { Badge, Button, ConfirmDialog, FormInput, FormSelect, Modal, PageHeader } from '../../components';
import { Permission } from '../../config/permissions';
import { usePermissions } from '../../hooks/usePermissions';
import { useAuthStore } from '../../stores/authStore';
import {
    AltSaturdays, Audience, CalendarEvent, CalendarEventType, CalendarSettings, holidayError, HolidayInput, holidayService,
} from '../../services/modules/holidayService';
import { addDays, formatRange, localDay } from '../LeaveManagement/leaveDates';

type Filterable = Exclude<CalendarEventType, 'WEEKLY_OFF'>;
const STYLE: Record<CalendarEventType, { label: string; chip: string; dot: string }> = {
    HOLIDAY: { label: 'Holidays', chip: 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-200', dot: 'bg-purple-500' },
    EXAM: { label: 'Exams', chip: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200', dot: 'bg-blue-500' },
    LEAVE: { label: 'Leave', chip: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200', dot: 'bg-emerald-500' },
    WEEKLY_OFF: { label: 'Weekly off', chip: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300', dot: 'bg-gray-400' },
};
const FILTERS: Filterable[] = ['HOLIDAY', 'EXAM', 'LEAVE'];
const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const AUDIENCE_LABEL: Record<Audience, string> = { ALL: 'Everyone', STUDENTS: 'Students only', STAFF: 'Staff only' };

const emptyForm = (day: string): HolidayInput => ({
    name: '', start_date: day, end_date: day, applies_to: 'ALL', is_tentative: false, note: '', notify: false,
});
const recountText = (n: number) => (n ? ` ${n} approved staff leave${n === 1 ? ' was' : 's were'} recounted.` : '');
const monthStart = (d: Date) => new Date(d.getFullYear(), d.getMonth(), 1);
const ymd = (d: Date) => localDay(d);
const prettyDay = (day: string) => {
    const [y, m, d] = day.split('-').map(Number);
    return new Date(y, m - 1, d).toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' });
};

const chipClass = (e: CalendarEvent) => {
    if (e.type === 'HOLIDAY' && e.is_tentative) return `${STYLE.HOLIDAY.chip} border border-dashed border-purple-400`;
    if (e.type === 'LEAVE' && e.status === 'PENDING') return 'bg-amber-50 text-amber-800 border border-dashed border-amber-400 dark:bg-amber-900/20 dark:text-amber-200';
    return STYLE[e.type].chip;
};
const chipText = (e: CalendarEvent) => (e.type === 'HOLIDAY' && e.is_tentative ? `${e.title} ?` : e.title);

const CalendarPage: FC = () => {
    const { hasPermission } = usePermissions();
    const canManage = hasPermission(Permission.MANAGE_HOLIDAYS);
    const role = useAuthStore((st) => st.user?.role);
    const isFamily = role === 'STUDENT' || role === 'PARENT';
    const today = localDay();
    const [month, setMonth] = useState(() => monthStart(new Date()));
    const [view, setView] = useState<'month' | 'list'>(() => (typeof window !== 'undefined' && window.innerWidth < 640 ? 'list' : 'month'));
    const [events, setEvents] = useState<CalendarEvent[]>([]);
    const [loading, setLoading] = useState(true);
    const [shown, setShown] = useState<Record<Filterable, boolean>>({ HOLIDAY: true, EXAM: true, LEAVE: true });
    const [selected, setSelected] = useState<string>(today);
    const [reload, setReload] = useState(0);
    // holiday management
    const [editing, setEditing] = useState<{ id: number | null; form: HolidayInput; focusDates?: boolean } | null>(null);
    const [saving, setSaving] = useState(false);
    const [deleting, setDeleting] = useState<CalendarEvent | null>(null);
    const [confirming, setConfirming] = useState<CalendarEvent | null>(null);
    const [notifyConfirm, setNotifyConfirm] = useState(true);
    const [settingsOpen, setSettingsOpen] = useState(false);
    const [settings, setSettings] = useState<CalendarSettings | null>(null);
    const [offDays, setOffDays] = useState<number[]>([6]);
    const [altSat, setAltSat] = useState<AltSaturdays>('NONE');
    const [savingSettings, setSavingSettings] = useState(false);

    // the grid: full weeks, Monday before the 1st to Sunday after the last day
    const gridStart = useMemo(() => addDays(ymd(month), -((month.getDay() + 6) % 7)), [month]);
    const gridDays = useMemo(() => {
        const last = new Date(month.getFullYear(), month.getMonth() + 1, 0);
        const end = addDays(ymd(last), (7 - ((last.getDay() + 6) % 7) - 1) % 7);
        const out: string[] = [];
        for (let d = gridStart; d <= end; d = addDays(d, 1)) out.push(d);
        return out;
    }, [month, gridStart]);

    useEffect(() => {
        let alive = true;
        setLoading(true);
        holidayService.events(gridDays[0], gridDays[gridDays.length - 1])
            .then((ev) => alive && setEvents(ev))
            .catch((err) => { if (alive) { setEvents([]); toast.error(holidayError(err, 'Could not load the calendar')); } })
            .finally(() => alive && setLoading(false));
        return () => { alive = false; };
    }, [gridDays, reload]);

    const refresh = useCallback(() => setReload((n) => n + 1), []);
    const goToMonth = (d: Date) => {
        const m = monthStart(d);
        setMonth(m);
        setSelected(today.startsWith(ymd(m).slice(0, 7)) ? today : ymd(m));
    };

    const byDay = useMemo(() => {
        const map: Record<string, CalendarEvent[]> = {};
        events.forEach((e) => {
            if (e.type !== 'WEEKLY_OFF' && !shown[e.type as Filterable]) return;
            for (let d = e.date_from; d <= e.date_to; d = addDays(d, 1)) (map[d] ||= []).push(e);
        });
        const order: CalendarEventType[] = ['HOLIDAY', 'EXAM', 'LEAVE', 'WEEKLY_OFF'];
        Object.values(map).forEach((list) => list.sort((a, b) => order.indexOf(a.type) - order.indexOf(b.type)));
        return map;
    }, [events, shown]);

    const monthKey = ymd(month).slice(0, 7);
    // list view: each item once, on its first day within the month
    const firstInMonth = useCallback((e: CalendarEvent) => (e.date_from < `${monthKey}-01` ? `${monthKey}-01` : e.date_from), [monthKey]);
    const agendaItems = useCallback((d: string) => (byDay[d] || []).filter((e) => e.type !== 'WEEKLY_OFF' && firstInMonth(e) === d), [byDay, firstInMonth]);
    const agenda = useMemo(() => gridDays.filter((d) => d.startsWith(monthKey) && agendaItems(d).length > 0), [gridDays, monthKey, agendaItems]);

    // ---- holiday actions
    const openAdd = (day: string) => setEditing({ id: null, form: emptyForm(day) });
    const openEdit = (e: CalendarEvent, focusDates = false) => setEditing({
        id: e.id!, focusDates,
        form: { name: e.title, start_date: e.date_from, end_date: e.date_to, applies_to: e.applies_to || 'ALL', is_tentative: !!e.is_tentative, note: e.note || '', notify: false },
    });
    const setField = <K extends keyof HolidayInput>(k: K, v: HolidayInput[K]) =>
        setEditing((cur) => {
            if (!cur) return cur;
            const form = { ...cur.form, [k]: v };
            if (k === 'start_date' && typeof v === 'string' && form.end_date < v) form.end_date = v;
            return { ...cur, form };
        });
    const save = async () => {
        if (!editing) return;
        const f = editing.form;
        if (!f.name.trim()) { toast.error('Give the holiday a name'); return; }
        if (!f.start_date || !f.end_date || f.end_date < f.start_date) { toast.error('Check the dates'); return; }
        setSaving(true);
        try {
            const body = { ...f, name: f.name.trim(), note: f.note?.trim() || null };
            const res = editing.id ? await holidayService.update(editing.id, body) : await holidayService.create(body);
            toast.success(`${editing.id ? 'Holiday updated' : 'Holiday added'}.${recountText(res.recounted_leave)}`);
            setEditing(null);
            setSelected(f.start_date);
            refresh();
        } catch (err) {
            toast.error(holidayError(err, 'Could not save the holiday'));
        } finally {
            setSaving(false);
        }
    };
    const confirmTentative = async () => {
        if (!confirming?.id) return;
        try {
            await holidayService.update(confirming.id, { is_tentative: false, notify: notifyConfirm });
            toast.success(`${confirming.title} confirmed`);
            refresh();
        } catch (err) {
            toast.error(holidayError(err, 'Could not confirm the holiday'));
        } finally {
            setConfirming(null);
        }
    };
    const remove = async () => {
        if (!deleting?.id) return;
        try {
            const res = await holidayService.remove(deleting.id);
            toast.success(`Holiday deleted.${recountText(res.recounted_leave)}`);
            refresh();
        } catch (err) {
            toast.error(holidayError(err, 'Could not delete the holiday'));
        } finally {
            setDeleting(null);
        }
    };
    const openSettings = async () => {
        setSettingsOpen(true);
        try {
            const y = await holidayService.listYear();
            setSettings(y.settings);
            setOffDays(y.settings.weekly_off_days);
            setAltSat(y.settings.alternate_saturdays);
        } catch (err) {
            toast.error(holidayError(err, 'Could not load the settings'));
        }
    };
    const saveSettings = async () => {
        setSavingSettings(true);
        try {
            const res = await holidayService.saveSettings(offDays, offDays.includes(5) ? 'NONE' : altSat);
            toast.success(`Weekly offs saved.${recountText(res.recounted_leave)}`);
            setSettingsOpen(false);
            refresh();
        } catch (err) {
            toast.error(holidayError(err, 'Could not save weekly offs'));
        } finally {
            setSavingSettings(false);
        }
    };

    // ---- pieces
    const EventRow: FC<{ e: CalendarEvent }> = ({ e }) => (
        <div className="flex flex-col gap-2 py-2.5 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
                <p className="flex flex-wrap items-center gap-2 text-sm font-medium text-gray-900 dark:text-white">
                    <span className={`inline-block h-2.5 w-2.5 shrink-0 rounded-full ${STYLE[e.type].dot}`} />
                    {e.title}
                    {e.type === 'HOLIDAY' && e.is_tentative && <Badge variant="warning" size="sm">Tentative</Badge>}
                    {e.type === 'HOLIDAY' && !isFamily && e.applies_to && e.applies_to !== 'ALL' && <Badge variant="secondary" size="sm">{AUDIENCE_LABEL[e.applies_to]}</Badge>}
                </p>
                <p className="pl-4.5 text-xs text-gray-500 dark:text-gray-400">
                    {e.date_from !== e.date_to ? formatRange(e.date_from, e.date_to) : ''}
                    {e.time ? `${e.date_from !== e.date_to ? ' · ' : ''}${e.time}` : ''}
                    {e.detail ? `${e.date_from !== e.date_to || e.time ? ' · ' : ''}${e.detail}` : ''}
                    {e.type === 'HOLIDAY' && e.is_tentative ? `${e.date_from !== e.date_to ? ' · ' : ''}date may change` : ''}
                    {e.note ? ` · ${e.note}` : ''}
                </p>
            </div>
            {canManage && e.type === 'HOLIDAY' && (
                <div className="flex flex-wrap gap-1.5 pl-4.5 sm:pl-0">
                    {e.is_tentative ? (
                        <>
                            <Button size="sm" variant="success" onClick={() => { setNotifyConfirm(true); setConfirming(e); }}>Confirm</Button>
                            <Button size="sm" variant="secondary" onClick={() => openEdit(e, true)}>Change date</Button>
                        </>
                    ) : <Button size="sm" variant="secondary" onClick={() => openEdit(e)}>Edit</Button>}
                    <Button size="sm" variant="ghost" onClick={() => setDeleting(e)}>Delete</Button>
                </div>
            )}
        </div>
    );

    const dayItems = byDay[selected] || [];

    return (
        <div className="space-y-5">
            <PageHeader
                title="Calendar"
                subtitle="Holidays, weekly offs, exams and leave"
                breadcrumbs={[{ label: 'Dashboard', href: '/dashboard' }, { label: 'Calendar', href: '#' }]}
                actions={canManage ? (
                    <div className="flex flex-wrap gap-2">
                        <Button variant="secondary" size="sm" onClick={openSettings}>⚙ Calendar settings</Button>
                        <Button size="sm" onClick={() => openAdd(selected >= today ? selected : today)}>+ Add holiday</Button>
                    </div>
                ) : undefined}
            />

            {/* toolbar */}
            <div className="flex flex-col gap-3 rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800 md:flex-row md:items-center md:justify-between">
                <div className="flex items-center gap-2">
                    <button type="button" aria-label="Previous month" onClick={() => goToMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))}
                        className="flex h-9 w-9 items-center justify-center rounded-full border border-gray-300 text-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700">
                        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}><path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" /></svg>
                    </button>
                    <p className="min-w-[9.5rem] text-center text-base font-semibold text-gray-900 dark:text-white" data-testid="calendar-month">
                        {month.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })}
                    </p>
                    <button type="button" aria-label="Next month" onClick={() => goToMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))}
                        className="flex h-9 w-9 items-center justify-center rounded-full border border-gray-300 text-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700">
                        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" /></svg>
                    </button>
                    <button type="button" onClick={() => goToMonth(new Date())}
                        className="ml-1 h-9 rounded-lg border border-gray-300 px-3 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700">Today</button>
                </div>
                <div className="flex flex-wrap items-center gap-1.5">
                    {FILTERS.map((f) => (
                        <button key={f} type="button" aria-pressed={shown[f]} onClick={() => setShown((s) => ({ ...s, [f]: !s[f] }))}
                            className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${shown[f]
                                ? 'border-gray-300 bg-white text-gray-800 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100'
                                : 'border-gray-200 bg-gray-50 text-gray-400 line-through dark:border-gray-700 dark:bg-gray-900'}`}>
                            <span className={`inline-block h-2 w-2 rounded-full ${STYLE[f].dot}`} />{STYLE[f].label}
                        </button>
                    ))}
                    <span className="ml-1 flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
                        <span className="inline-block h-2.5 w-2.5 rounded-sm bg-gray-200 dark:bg-gray-600" />Weekly off
                    </span>
                    <div className="ml-2 flex overflow-hidden rounded-lg border border-gray-300 dark:border-gray-600" role="tablist">
                        {(['month', 'list'] as const).map((v) => (
                            <button key={v} type="button" role="tab" aria-selected={view === v} onClick={() => setView(v)}
                                className={`px-3 py-1 text-xs font-medium ${view === v ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 dark:bg-gray-800 dark:text-gray-200'}`}>
                                {v === 'month' ? 'Month' : 'List'}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {view === 'month' ? (
                <div className="grid gap-4 xl:grid-cols-[1fr_340px]">
                    <div className={`overflow-hidden rounded-xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800 ${loading ? 'opacity-60' : ''}`} data-testid="calendar-grid">
                        <div className="grid grid-cols-7 border-b border-gray-200 bg-gray-50 text-center text-xs font-semibold text-gray-500 dark:border-gray-700 dark:bg-gray-700/50 dark:text-gray-300">
                            {WEEKDAYS.map((d) => <div key={d} className="py-2">{d}</div>)}
                        </div>
                        <div className="grid grid-cols-7">
                            {gridDays.map((d) => {
                                const items = byDay[d] || [];
                                const off = items.some((e) => e.type === 'WEEKLY_OFF');
                                const visible = items.filter((e) => e.type !== 'WEEKLY_OFF');
                                const inMonth = d.startsWith(monthKey);
                                return (
                                    <button key={d} type="button" data-day={d} onClick={() => setSelected(d)}
                                        className={`flex min-h-[3.25rem] flex-col items-stretch gap-0.5 border-b border-r border-gray-100 p-1 text-left align-top transition-colors dark:border-gray-700 sm:min-h-[6.5rem] sm:p-1.5
                                            ${off ? 'bg-gray-100/80 dark:bg-gray-900/50' : ''} ${selected === d ? 'ring-2 ring-inset ring-blue-500' : 'hover:bg-blue-50/50 dark:hover:bg-gray-700/40'}`}>
                                        <span className={`self-start rounded-full px-1.5 text-xs font-semibold sm:text-sm
                                            ${d === today ? 'bg-blue-600 text-white' : inMonth ? 'text-gray-800 dark:text-gray-100' : 'text-gray-300 dark:text-gray-600'}`}>
                                            {Number(d.slice(8))}
                                        </span>
                                        {/* phones: dots; larger screens: chips */}
                                        <span className="flex flex-wrap gap-0.5 sm:hidden">
                                            {visible.slice(0, 4).map((e, i) => <span key={i} className={`inline-block h-1.5 w-1.5 rounded-full ${STYLE[e.type].dot}`} />)}
                                        </span>
                                        <span className="hidden flex-col gap-0.5 sm:flex">
                                            {visible.slice(0, 3).map((e, i) => (
                                                <span key={i} title={e.title} className={`truncate rounded px-1 py-0.5 text-[11px] font-medium leading-tight ${chipClass(e)}`}>{chipText(e)}</span>
                                            ))}
                                            {visible.length > 3 && <span className="px-1 text-[11px] text-gray-500 dark:text-gray-400">+{visible.length - 3} more</span>}
                                        </span>
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    {/* selected day */}
                    <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800" data-testid="day-panel">
                        <div className="flex items-start justify-between gap-2">
                            <div>
                                <p className="font-semibold text-gray-900 dark:text-white">{prettyDay(selected)}</p>
                                {dayItems.filter((e) => e.type === 'WEEKLY_OFF').map((e, i) => (
                                    <p key={i} className="text-xs text-gray-500 dark:text-gray-400">{e.title}</p>
                                ))}
                            </div>
                            {canManage && (
                                <Button size="sm" variant="outline" onClick={() => openAdd(selected)}>+ Holiday</Button>
                            )}
                        </div>
                        <div className="mt-2 divide-y divide-gray-100 dark:divide-gray-700">
                            {dayItems.filter((e) => e.type !== 'WEEKLY_OFF').map((e, i) => <EventRow key={`${e.type}-${e.id ?? i}-${i}`} e={e} />)}
                        </div>
                        {!dayItems.some((e) => e.type !== 'WEEKLY_OFF') && (
                            <p className="mt-3 text-sm text-gray-500 dark:text-gray-400">Nothing on this day.</p>
                        )}
                    </div>
                </div>
            ) : (
                <div className={`rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800 ${loading ? 'opacity-60' : ''}`} data-testid="calendar-list">
                    {agenda.length === 0 ? (
                        <p className="py-6 text-center text-sm text-gray-500 dark:text-gray-400">Nothing this month.</p>
                    ) : agenda.map((d) => (
                        <div key={d} className={`border-b border-gray-100 py-2 last:border-0 dark:border-gray-700 ${d < today ? 'opacity-60' : ''}`}>
                            <div className="flex items-center justify-between">
                                <p className={`text-sm font-semibold ${d === today ? 'text-blue-600 dark:text-blue-400' : 'text-gray-900 dark:text-white'}`}>
                                    {prettyDay(d)}{d === today ? ' · Today' : ''}
                                </p>
                                {canManage && <button type="button" onClick={() => openAdd(d)} className="text-xs font-medium text-blue-600 hover:underline dark:text-blue-400">+ Holiday</button>}
                            </div>
                            <div className="divide-y divide-gray-100 dark:divide-gray-700">
                                {agendaItems(d).map((e, i) => <EventRow key={`${e.type}-${e.id ?? i}-${i}`} e={e} />)}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* add / edit holiday */}
            <Modal isOpen={!!editing} onClose={() => setEditing(null)} size="lg"
                title={editing?.id ? (editing.focusDates ? 'Change holiday date' : 'Edit holiday') : 'Add holiday'}
                footer={
                    <div className="flex justify-end gap-2">
                        <Button variant="secondary" onClick={() => setEditing(null)}>Cancel</Button>
                        <Button onClick={save} isLoading={saving} loadingText="Saving...">Save</Button>
                    </div>
                }>
                {editing && (
                    <div className="space-y-4">
                        <FormInput label="Name" required value={editing.form.name} maxLength={120} placeholder="e.g. Diwali, Eid ul-Fitr, Winter break"
                            onChange={(e) => setField('name', e.target.value)} />
                        <div className="grid gap-4 sm:grid-cols-2">
                            <FormInput label="From" type="date" required value={editing.form.start_date} autoFocus={editing.focusDates}
                                onChange={(e) => setField('start_date', e.target.value)} />
                            <FormInput label="To" type="date" required value={editing.form.end_date} min={editing.form.start_date}
                                onChange={(e) => setField('end_date', e.target.value)} help="Change this for a break of several days" />
                        </div>
                        <FormSelect label="For" value={editing.form.applies_to === 'ALL' ? '' : editing.form.applies_to} placeholder="Everyone"
                            onChange={(e) => setField('applies_to', (e.target.value || 'ALL') as Audience)}
                            options={[{ value: 'STUDENTS', label: 'Students only (staff work)' }, { value: 'STAFF', label: 'Staff only' }]} />
                        <label className="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-300">
                            <input type="checkbox" className="mt-0.5" checked={editing.form.is_tentative} onChange={(e) => setField('is_tentative', e.target.checked)} />
                            <span><strong>Tentative</strong>: the date may change (e.g. subject to moon sighting). Shown with a "Tentative" badge until confirmed.</span>
                        </label>
                        <FormInput label="Note (optional)" value={editing.form.note || ''} maxLength={255} placeholder="e.g. Subject to moon sighting"
                            onChange={(e) => setField('note', e.target.value)} />
                        <label className="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-300">
                            <input type="checkbox" className="mt-0.5" checked={!!editing.form.notify} onChange={(e) => setField('notify', e.target.checked)} />
                            <span>Notify everyone it applies to (push notification with the name and date)</span>
                        </label>
                    </div>
                )}
            </Modal>

            {/* weekly offs */}
            <Modal isOpen={settingsOpen} onClose={() => setSettingsOpen(false)} size="md" title="Calendar settings"
                footer={
                    <div className="flex justify-end gap-2">
                        <Button variant="secondary" onClick={() => setSettingsOpen(false)}>Cancel</Button>
                        <Button onClick={saveSettings} isLoading={savingSettings} loadingText="Saving..." disabled={!settings}>Save</Button>
                    </div>
                }>
                <div className="space-y-4" data-testid="weekly-offs">
                    <div>
                        <p className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">Weekly off days</p>
                        <div className="flex flex-wrap gap-1.5">
                            {WEEKDAYS.map((d, i) => (
                                <button key={d} type="button" aria-pressed={offDays.includes(i)}
                                    onClick={() => setOffDays((cur) => (cur.includes(i) ? cur.filter((x) => x !== i) : [...cur, i]))}
                                    className={`rounded-lg border px-3 py-1.5 text-sm font-medium ${offDays.includes(i)
                                        ? 'border-blue-600 bg-blue-600 text-white'
                                        : 'border-gray-300 bg-white text-gray-700 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200'}`}>
                                    {d}
                                </button>
                            ))}
                        </div>
                    </div>
                    {!offDays.includes(5) && (
                        <FormSelect label="Saturdays off" value={altSat === 'NONE' ? '' : altSat} placeholder="No"
                            onChange={(e) => setAltSat((e.target.value || 'NONE') as AltSaturdays)}
                            options={[{ value: '2_4', label: '2nd & 4th Saturday' }, { value: '1_3', label: '1st & 3rd Saturday' }]} />
                    )}
                    {settings?.inherited_from && (
                        <p className="text-xs text-amber-700 dark:text-amber-400">These come from {settings.inherited_from}; they apply until you save.</p>
                    )}
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                        Weekly offs and holidays aren't counted in staff leave and don't need attendance. Applies to the current academic year.
                    </p>
                </div>
            </Modal>

            <ConfirmDialog
                isOpen={!!confirming}
                title="Confirm holiday"
                message={confirming ? `Confirm ${confirming.title} on ${formatRange(confirming.date_from, confirming.date_to)}? The "Tentative" badge will be removed.` : ''}
                confirmText="Confirm"
                type="success"
                onConfirm={confirmTentative}
                onCancel={() => setConfirming(null)}
            >
                <label className="mt-3 flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                    <input type="checkbox" checked={notifyConfirm} onChange={(e) => setNotifyConfirm(e.target.checked)} />
                    Notify everyone it applies to
                </label>
            </ConfirmDialog>

            <ConfirmDialog
                isOpen={!!deleting}
                title="Delete holiday?"
                message={deleting ? `Delete ${deleting.title} (${formatRange(deleting.date_from, deleting.date_to)})? Those days become normal working days.` : ''}
                confirmText="Delete"
                type="danger"
                onConfirm={remove}
                onCancel={() => setDeleting(null)}
            />
        </div>
    );
};

export default CalendarPage;
