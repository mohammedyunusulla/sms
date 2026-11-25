/**
 * Leave for the signed-in person: a student's or staff member's own, or (parents) the child picked in the
 * header dropdown. Apply, see the history, cancel a request that hasn't started.
 */
import { FC, FormEvent, useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { Button, ConfirmDialog, FormInput, FormSelect, FormTextarea, LoadingSpinner, PageHeader } from '../../components';
import { useAuthStore } from '../../stores/authStore';
import { useParentStore } from '../../stores/parentStore';
import { leaveErrorMessage, leaveService, LeaveRequest, MyLeaveData } from '../../services/modules/leaveService';
import LeaveCard from './LeaveCard';
import { addDays, localDay } from './leaveDates';

const REASON_MAX = 1000;

const MyLeave: FC = () => {
    const role = useAuthStore((s) => s.user?.role);
    const isParent = role === 'PARENT';
    const selectedChild = useParentStore((s) => s.selectedChild);
    const childrenLoaded = useParentStore((s) => s.loaded);
    const childrenLoading = useParentStore((s) => s.loading);
    const childId = isParent && selectedChild ? Number(selectedChild.student_id) : undefined;
    const childName = selectedChild?.first_name || selectedChild?.full_name || 'your child';

    const [data, setData] = useState<MyLeaveData | null>(null);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [saving, setSaving] = useState(false);
    const [cancelling, setCancelling] = useState<LeaveRequest | null>(null);
    const [form, setForm] = useState({ from_date: localDay(), to_date: localDay(), leave_type: '', reason: '' });
    const [errors, setErrors] = useState<Record<string, string>>({});

    const load = useCallback(async () => {
        if (isParent && !childId) {
            setLoading(false);
            return;
        }
        setLoading(true);
        try {
            setData(await leaveService.getMine(childId));
        } catch (err) {
            toast.error(leaveErrorMessage(err, 'Could not load leave requests'));
        } finally {
            setLoading(false);
        }
    }, [isParent, childId]);

    useEffect(() => {
        setShowForm(false);
        load();
    }, [load]);

    const minDay = addDays(localDay(), -(data?.days_back ?? 7));

    const validate = () => {
        const e: Record<string, string> = {};
        if (!form.from_date) e.from_date = 'Choose the first day';
        else if (form.from_date < minDay) e.from_date = `At most ${data?.days_back ?? 7} days back`;
        if (!form.to_date) e.to_date = 'Choose the last day';
        else if (form.from_date && form.to_date < form.from_date) e.to_date = 'Must be on or after the first day';
        if (!form.leave_type) e.leave_type = 'Choose a type';
        if (!form.reason.trim()) e.reason = 'Please give a reason';
        setErrors(e);
        return Object.keys(e).length === 0;
    };

    const submit = async (ev: FormEvent) => {
        ev.preventDefault();
        if (!validate()) return;
        setSaving(true);
        try {
            await leaveService.apply({ ...form, reason: form.reason.trim(), student_id: childId });
            toast.success('Leave request sent');
            setShowForm(false);
            setForm({ from_date: localDay(), to_date: localDay(), leave_type: '', reason: '' });
            load();
        } catch (err) {
            toast.error(leaveErrorMessage(err, 'Could not send the request'));
        } finally {
            setSaving(false);
        }
    };

    const confirmCancel = async () => {
        if (!cancelling) return;
        try {
            await leaveService.cancel(cancelling.id);
            toast.success('Request cancelled');
            load();
        } catch (err) {
            toast.error(leaveErrorMessage(err, 'Could not cancel the request'));
        } finally {
            setCancelling(null);
        }
    };

    const change = (name: string, value: string) => {
        setForm((f) => {
            const next = { ...f, [name]: value };
            // moving the first day past the last day moves the last day with it
            if (name === 'from_date' && value && next.to_date < value) next.to_date = value;
            return next;
        });
        if (errors[name]) setErrors((e) => ({ ...e, [name]: '' }));
    };

    const title = isParent ? "My Child's Leave" : 'My Leave';
    const subtitle = isParent
        ? (selectedChild ? `Apply for leave for ${childName} and see past requests` : 'Pick a child from the header dropdown')
        : 'Apply for leave and see your past requests';

    const pending = data?.requests.filter((r) => r.status === 'PENDING').length ?? 0;

    return (
        <div className="space-y-6">
            <PageHeader
                title={title}
                subtitle={subtitle}
                breadcrumbs={[{ label: 'Dashboard', href: '/dashboard' }, { label: title, href: '#' }]}
                actions={data && !showForm ? <Button onClick={() => setShowForm(true)}>Apply for leave</Button> : undefined}
            />

            {isParent && !selectedChild ? (
                <div className="rounded-lg border border-gray-200 bg-white p-8 text-center dark:border-gray-700 dark:bg-gray-800">
                    <p className="text-gray-500 dark:text-gray-400">
                        {childrenLoading ? 'Loading your children…' : childrenLoaded ? 'No children linked to your account yet.' : 'Select a child from the dropdown in the header to begin.'}
                    </p>
                </div>
            ) : loading && !data ? (
                <div className="flex justify-center py-12"><LoadingSpinner /></div>
            ) : data ? (
                <>
                    {showForm && (
                        <form onSubmit={submit} className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
                            <h3 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">
                                {isParent ? `Apply for leave for ${childName}` : 'Apply for leave'}
                            </h3>
                            <div className="grid gap-4 sm:grid-cols-2">
                                <FormInput label="From" type="date" required value={form.from_date} min={minDay}
                                    onChange={(e) => change('from_date', e.target.value)} error={errors.from_date} />
                                <FormInput label="To" type="date" required value={form.to_date} min={form.from_date || minDay}
                                    onChange={(e) => change('to_date', e.target.value)} error={errors.to_date} />
                                <FormSelect label="Type" required placeholder="Choose a type" value={form.leave_type}
                                    options={data.leave_types} onChange={(e) => change('leave_type', e.target.value)} error={errors.leave_type} />
                            </div>
                            <div className="mt-4">
                                <FormTextarea label="Reason" required rows={3} maxLength={REASON_MAX} value={form.reason}
                                    placeholder={isParent ? `Why ${childName} needs leave` : 'Why you need leave'}
                                    onChange={(e) => change('reason', e.target.value)} error={errors.reason}
                                    help={`${form.reason.length}/${REASON_MAX}`} />
                            </div>
                            <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">
                                {data.applicant_type === 'STUDENT'
                                    ? 'The class teacher reviews the request. You get a notification when it is decided.'
                                    : 'The institution admin reviews the request. You get a notification when it is decided.'}
                            </p>
                            <div className="mt-4 flex justify-end gap-2">
                                <Button type="button" variant="secondary" onClick={() => { setShowForm(false); setErrors({}); }}>Cancel</Button>
                                <Button type="submit" isLoading={saving} loadingText="Sending...">Send request</Button>
                            </div>
                        </form>
                    )}

                    <div>
                        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                            Requests{pending ? ` · ${pending} pending` : ''}
                        </h3>
                        {data.requests.length === 0 ? (
                            <div className="rounded-lg border border-dashed border-gray-300 p-8 text-center text-gray-500 dark:border-gray-600 dark:text-gray-400">
                                No leave requests yet.
                            </div>
                        ) : (
                            <div className="grid gap-3 lg:grid-cols-2">
                                {data.requests.map((r) => (
                                    <LeaveCard key={r.id} leave={r}
                                        actions={r.can_cancel ? (
                                            <Button size="sm" variant="ghost" onClick={() => setCancelling(r)}>Cancel request</Button>
                                        ) : undefined} />
                                ))}
                            </div>
                        )}
                    </div>
                </>
            ) : null}

            <ConfirmDialog
                isOpen={!!cancelling}
                title="Cancel this leave request?"
                message="The request will be withdrawn. You can apply again later."
                confirmText="Cancel request"
                cancelText="Keep it"
                type="warning"
                onConfirm={confirmCancel}
                onCancel={() => setCancelling(null)}
            />
        </div>
    );
};

export default MyLeave;
