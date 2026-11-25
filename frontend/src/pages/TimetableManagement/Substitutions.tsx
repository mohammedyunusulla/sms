/**
 * Substitutions: periods that need a substitute on a date (teachers on leave, absent, half day, or marked by
 * hand), with suggested free teachers. The Institution Admin / "Create / Edit Timetable" holders assign them.
 */
import { FC, useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { useSearchParams } from 'react-router';
import { Badge, Button, ConfirmDialog, FormInput, FormSelect, LoadingSpinner, Modal, PageHeader } from '../../components';
import { CoverDay, CoverPeriod, subError, substitutionService, TeacherPeriod } from '../../services/modules/substitutionService';
import { addDays, localDay } from '../LeaveManagement/leaveDates';

const REASON_VARIANT: Record<string, 'danger' | 'warning' | 'info' | 'secondary'> = {
    LEAVE: 'info', ABSENT: 'danger', HALF_DAY: 'warning', MANUAL: 'secondary',
};

const prettyDay = (day: string) => {
    const [y, m, d] = day.split('-').map(Number);
    return new Date(y, m - 1, d).toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
};

const Substitutions: FC = () => {
    const [params, setParams] = useSearchParams();
    const [date, setDate] = useState(params.get('date') || localDay());
    const [data, setData] = useState<CoverDay | null>(null);
    const [loading, setLoading] = useState(true);
    const [busy, setBusy] = useState<number | 'all' | null>(null);
    const [choice, setChoice] = useState<Record<number, string>>({});
    const [removing, setRemoving] = useState<CoverPeriod | null>(null);
    const [aboutOpen, setAboutOpen] = useState(false);
    // cover by hand
    const [manualOpen, setManualOpen] = useState(false);
    const [manualTeacher, setManualTeacher] = useState('');
    const [manualPeriods, setManualPeriods] = useState<TeacherPeriod[]>([]);
    const [manualPicked, setManualPicked] = useState<number[]>([]);
    const [manualNote, setManualNote] = useState('');

    const load = useCallback(async () => {
        setLoading(true);
        try {
            setData(await substitutionService.day(date));
            setChoice({});
        } catch (err) {
            toast.error(subError(err, 'Could not load substitutions'));
            setData(null);
        } finally {
            setLoading(false);
        }
    }, [date]);

    useEffect(() => {
        load();
        setParams(date === localDay() ? {} : { date }, { replace: true });
    }, [load, date, setParams]);

    const assign = async (p: CoverPeriod, teacherId: number) => {
        setBusy(p.entry_id);
        try {
            await substitutionService.assign(date, p.entry_id, teacherId);
            toast.success(`Substitute assigned for period ${p.period_number}, ${p.class_section}`);
            load();
        } catch (err) {
            toast.error(subError(err, 'Could not assign'));
        } finally {
            setBusy(null);
        }
    };
    const assignAll = async () => {
        setBusy('all');
        try {
            const res = await substitutionService.assignAll(date);
            toast.success(res.assigned ? `${res.assigned} period${res.assigned === 1 ? '' : 's'} assigned` : 'No free teacher found for the remaining periods');
            load();
        } catch (err) {
            toast.error(subError(err, 'Could not assign'));
        } finally {
            setBusy(null);
        }
    };
    const confirmRemove = async () => {
        if (!removing) return;
        try {
            if (removing.teacher_back || (removing.reason === 'MANUAL' && !removing.substitute_id)) await substitutionService.unmark(date, removing.entry_id);
            else await substitutionService.remove(date, removing.entry_id);
            toast.success('Removed');
            load();
        } catch (err) {
            toast.error(subError(err, 'Could not remove'));
        } finally {
            setRemoving(null);
        }
    };

    const openManual = () => {
        setManualOpen(true);
        setManualTeacher('');
        setManualPeriods([]);
        setManualPicked([]);
        setManualNote('');
    };
    const pickTeacher = async (id: string) => {
        setManualTeacher(id);
        setManualPicked([]);
        setManualPeriods(id ? await substitutionService.teacherPeriods(date, Number(id)).catch(() => []) : []);
    };
    const saveManual = async () => {
        if (!manualPicked.length) { toast.error('Choose at least one period'); return; }
        try {
            await substitutionService.mark(date, manualPicked, manualNote.trim());
            toast.success('Added to the list');
            setManualOpen(false);
            load();
        } catch (err) {
            toast.error(subError(err, 'Could not add'));
        }
    };

    const open = (data?.periods || []).filter((p) => !p.substitute_id && !p.optional && !p.teacher_back);

    return (
        <div className="space-y-5">
            <PageHeader
                title="Substitutions"
                titleAddon={
                    <button type="button" aria-label="About substitutions" title="About substitutions" onClick={() => setAboutOpen(true)}
                        className="flex h-7 w-7 items-center justify-center rounded-full text-gray-400 transition-colors hover:bg-blue-50 hover:text-blue-600 dark:text-gray-500 dark:hover:bg-gray-700 dark:hover:text-blue-400">
                        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <circle cx="12" cy="12" r="9" />
                            <path strokeLinecap="round" d="M12 11v5" />
                            <circle cx="12" cy="7.75" r="0.6" fill="currentColor" />
                        </svg>
                    </button>
                }
                subtitle="Cover for teachers on leave, absent or busy"
                breadcrumbs={[{ label: 'Dashboard', href: '/dashboard' }, { label: 'Timetable', href: '/timetable' }, { label: 'Substitutions', href: '#' }]}
                actions={<Button variant="secondary" size="sm" onClick={openManual} disabled={!data || !!data.off_day}>+ Add cover by hand</Button>}
            />

            <div className="flex flex-col gap-3 rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-2">
                    <button type="button" aria-label="Previous day" onClick={() => setDate(addDays(date, -1))}
                        className="flex h-9 w-9 items-center justify-center rounded-full border border-gray-300 text-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700">
                        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}><path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" /></svg>
                    </button>
                    <input type="date" value={date} onChange={(e) => e.target.value && setDate(e.target.value)}
                        className="h-9 rounded-lg border border-gray-300 bg-white px-2 text-sm text-gray-900 dark:border-gray-600 dark:bg-gray-800 dark:text-white" />
                    <button type="button" aria-label="Next day" onClick={() => setDate(addDays(date, 1))}
                        className="flex h-9 w-9 items-center justify-center rounded-full border border-gray-300 text-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700">
                        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" /></svg>
                    </button>
                    <button type="button" onClick={() => setDate(localDay())}
                        className="h-9 rounded-lg border border-gray-300 px-3 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700">Today</button>
                    <span className="hidden text-sm font-medium text-gray-700 dark:text-gray-200 md:inline">{prettyDay(date)}</span>
                </div>
                {data && !data.off_day && data.needed > 0 && (
                    <div className="flex items-center gap-3">
                        <span data-testid="cover-count" className={`text-sm font-semibold ${data.covered === data.needed ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'}`}>
                            {data.covered} of {data.needed} periods covered
                        </span>
                        {open.length > 0 && (
                            <Button size="sm" onClick={assignAll} isLoading={busy === 'all'} loadingText="Assigning...">Assign all suggested</Button>
                        )}
                    </div>
                )}
            </div>

            {loading && !data ? (
                <div className="flex justify-center py-12"><LoadingSpinner /></div>
            ) : data?.off_day ? (
                <div className="rounded-lg border border-purple-200 bg-purple-50 p-6 text-center text-purple-900 dark:border-purple-800 dark:bg-purple-900/20 dark:text-purple-200">
                    {data.off_day.label}: no classes, nothing to cover.
                </div>
            ) : data && data.periods.length === 0 ? (
                <div className="rounded-lg border border-dashed border-gray-300 p-8 text-center text-gray-500 dark:border-gray-600 dark:text-gray-400">
                    Every teacher is in today: nothing to cover. 🎉
                </div>
            ) : data ? (
                <div className={`divide-y divide-gray-100 overflow-hidden rounded-xl border border-gray-200 bg-white dark:divide-gray-700 dark:border-gray-700 dark:bg-gray-800 ${loading ? 'opacity-60' : ''}`} data-testid="cover-list">
                    {data.periods.map((p) => (
                        <div key={p.entry_id} className={`flex flex-col gap-3 p-4 lg:flex-row lg:items-center ${p.optional || p.teacher_back ? 'bg-gray-50/70 dark:bg-gray-900/30' : ''}`}>
                            <div className="flex min-w-0 flex-1 gap-4">
                                <div className="w-20 shrink-0 text-sm">
                                    <p className="font-semibold text-gray-900 dark:text-white">Period {p.period_number}</p>
                                    <p className="text-xs text-gray-500 dark:text-gray-400">{p.start_time}–{p.end_time}</p>
                                </div>
                                <div className="min-w-0">
                                    <p className="font-medium text-gray-900 dark:text-white">{p.class_section} · {p.subject_name}</p>
                                    <p className="flex flex-wrap items-center gap-1.5 text-sm text-gray-600 dark:text-gray-300">
                                        {p.teacher_name}
                                        {p.reason && <Badge variant={REASON_VARIANT[p.reason] || 'secondary'} size="sm">{p.reason_label}</Badge>}
                                        {p.optional && <span className="text-xs text-amber-700 dark:text-amber-400">may need cover</span>}
                                        {p.teacher_back && <Badge variant="success" size="sm">Teacher is back</Badge>}
                                    </p>
                                    {p.note && <p className="text-xs text-gray-500 dark:text-gray-400">{p.note}</p>}
                                </div>
                            </div>
                            <div className="flex flex-col gap-2 sm:flex-row sm:items-center lg:w-[28rem] lg:justify-end">
                                {p.substitute_id && !p.teacher_back ? (
                                    <>
                                        <span className="whitespace-nowrap text-sm font-medium text-emerald-700 dark:text-emerald-400">✓ {p.substitute_name}</span>
                                        <select aria-label={`Change substitute for period ${p.period_number}`} value=""
                                            onChange={(e) => e.target.value && assign(p, Number(e.target.value))}
                                            className="h-9 w-full rounded-lg border border-gray-300 bg-white px-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white sm:w-40">
                                            <option value="">Change…</option>
                                            {p.suggestions.map((s) => <option key={s.teacher_id} value={s.teacher_id}>{s.name}{s.tags.length ? ` · ${s.tags.join(' · ')}` : ''}</option>)}
                                        </select>
                                        <Button size="sm" variant="ghost" onClick={() => setRemoving(p)}>Remove</Button>
                                    </>
                                ) : p.teacher_back ? (
                                    <Button size="sm" variant="secondary" onClick={() => setRemoving(p)}>Remove{p.substitute_name ? ` (${p.substitute_name})` : ''}</Button>
                                ) : p.suggestions.length === 0 ? (
                                    <span className="text-sm text-red-600 dark:text-red-400">No free teacher at this time</span>
                                ) : (
                                    <>
                                        <select aria-label={`Substitute for period ${p.period_number}`} value={choice[p.entry_id] ?? String(p.suggestions[0].teacher_id)}
                                            onChange={(e) => setChoice((c) => ({ ...c, [p.entry_id]: e.target.value }))}
                                            className="h-9 min-w-0 flex-1 rounded-lg border border-gray-300 bg-white px-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white">
                                            {p.suggestions.map((s, i) => (
                                                <option key={s.teacher_id} value={s.teacher_id}>{i === 0 ? '★ ' : ''}{s.name}{s.tags.length ? ` · ${s.tags.join(' · ')}` : ''}</option>
                                            ))}
                                        </select>
                                        <Button size="sm" variant={p.optional ? 'secondary' : 'primary'} isLoading={busy === p.entry_id} loadingText="..."
                                            onClick={() => assign(p, Number(choice[p.entry_id] ?? p.suggestions[0].teacher_id))}>Assign</Button>
                                        {p.reason === 'MANUAL' && <Button size="sm" variant="ghost" onClick={() => setRemoving(p)}>Remove</Button>}
                                    </>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            ) : null}

            <Modal isOpen={manualOpen} onClose={() => setManualOpen(false)} title="Add cover by hand" size="md"
                footer={
                    <div className="flex justify-end gap-2">
                        <Button variant="secondary" onClick={() => setManualOpen(false)}>Cancel</Button>
                        <Button onClick={saveManual} disabled={!manualPicked.length}>Add to the list</Button>
                    </div>
                }>
                <div className="space-y-4" data-testid="manual-form">
                    <p className="text-sm text-gray-600 dark:text-gray-300">For a teacher who is in but busy (exam duty, a meeting) on {prettyDay(date)}.</p>
                    <FormSelect label="Teacher" value={manualTeacher} placeholder="Choose a teacher"
                        onChange={(e) => pickTeacher(e.target.value)}
                        options={(data?.teachers || []).map((t) => ({ value: String(t.id), label: t.name }))} />
                    {manualTeacher && (
                        manualPeriods.length === 0 ? <p className="text-sm text-gray-500 dark:text-gray-400">No periods that day.</p> : (
                            <div className="space-y-1.5">
                                {manualPeriods.map((mp) => (
                                    <label key={mp.entry_id} className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                                        <input type="checkbox" checked={manualPicked.includes(mp.entry_id)}
                                            onChange={(e) => setManualPicked((cur) => (e.target.checked ? [...cur, mp.entry_id] : cur.filter((x) => x !== mp.entry_id)))} />
                                        Period {mp.period_number} ({mp.start_time}–{mp.end_time}) · {mp.class_section} · {mp.subject_name}
                                    </label>
                                ))}
                            </div>
                        )
                    )}
                    <FormInput label="Reason (optional)" value={manualNote} maxLength={255} placeholder="e.g. Exam duty" onChange={(e) => setManualNote(e.target.value)} />
                </div>
            </Modal>

            <Modal isOpen={aboutOpen} onClose={() => setAboutOpen(false)} title="About substitutions" size="md">
                <div className="space-y-3 text-sm text-gray-700 dark:text-gray-300" data-testid="about-substitutions">
                    <p className="font-medium text-gray-900 dark:text-white">Cover classes when a teacher can't take them.</p>
                    <ul className="list-disc space-y-1.5 pl-5">
                        <li>Lists the periods of teachers on leave, absent, on half day, or busy.</li>
                        <li>Suggests free teachers, best match first (same subject).</li>
                        <li>The substitute, students and parents see it in their timetable.</li>
                    </ul>
                    <p className="rounded-lg bg-gray-50 px-3 py-2 text-gray-600 dark:bg-gray-700/50 dark:text-gray-300">
                        <span className="font-medium text-gray-900 dark:text-white">Example:</span> Ravi is on leave on Monday. His Maths class
                        for 6-B shows here. Anita, a free Maths teacher, is suggested. Assign her, and she and the class are informed.
                    </p>
                </div>
            </Modal>

            <ConfirmDialog
                isOpen={!!removing}
                title="Remove cover?"
                message={removing ? (removing.substitute_name
                    ? `Remove ${removing.substitute_name} from period ${removing.period_number}, ${removing.class_section}? They get a notification.`
                    : `Remove period ${removing.period_number}, ${removing.class_section} from the list?`) : ''}
                confirmText="Remove"
                type="warning"
                onConfirm={confirmRemove}
                onCancel={() => setRemoving(null)}
            />
        </div>
    );
};

export default Substitutions;
