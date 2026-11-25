/**
 * Leave policy: paid staff leave days per type for the current academic year.
 * Empty = no limit (every approved day is paid). Days beyond the balance are approved as unpaid leave.
 */
import { FC, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { Button, LoadingSpinner, PageHeader } from '../../components';
import { leaveErrorMessage, leaveService, LeavePolicy } from '../../services/modules/leaveService';

const LeavePolicyPage: FC = () => {
    const [policy, setPolicy] = useState<LeavePolicy | null>(null);
    const [values, setValues] = useState<Record<string, string>>({});
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');

    const apply = (p: LeavePolicy) => {
        setPolicy(p);
        setValues(Object.fromEntries(p.types.map((t) => [t.type, t.paid_days == null ? '' : String(t.paid_days)])));
    };

    useEffect(() => {
        leaveService.getPolicy().then(apply).catch((err) => setError(leaveErrorMessage(err, 'Could not load the leave policy')));
    }, []);

    const save = async () => {
        const types = Object.entries(values).map(([type, v]) => ({ type, paid_days: v.trim() === '' ? null : Number(v) }));
        if (types.some((t) => t.paid_days !== null && (!Number.isInteger(t.paid_days) || t.paid_days < 0 || t.paid_days > 366))) {
            toast.error('Paid days must be a whole number from 0 to 366, or empty for no limit');
            return;
        }
        setSaving(true);
        try {
            apply(await leaveService.savePolicy(types));
            toast.success('Leave policy saved');
        } catch (err) {
            toast.error(leaveErrorMessage(err, 'Could not save the leave policy'));
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="space-y-6">
            <PageHeader
                title="Leave Policy"
                subtitle={policy?.year_name ? `Paid staff leave for ${policy.year_name}` : 'Paid staff leave per year'}
                breadcrumbs={[{ label: 'Dashboard', href: '/dashboard' }, { label: 'Leave Requests', href: '/leave/requests' }, { label: 'Leave Policy', href: '#' }]}
            />

            {error ? (
                <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
            ) : !policy ? (
                <div className="flex justify-center py-12"><LoadingSpinner /></div>
            ) : (
                <div className="max-w-2xl space-y-4">
                    {policy.inherited_from && (
                        <p className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-200">
                            Nothing saved for {policy.year_name} yet: these are the days from {policy.inherited_from}, and they apply until you save.
                        </p>
                    )}
                    <div className="divide-y divide-gray-100 rounded-xl border border-gray-200 bg-white dark:divide-gray-700 dark:border-gray-700 dark:bg-gray-800">
                        {policy.types.map((t) => (
                            <label key={t.type} className="flex items-center justify-between gap-4 p-4">
                                <span>
                                    <span className="block font-medium text-gray-900 dark:text-white">{t.label} leave</span>
                                    <span className="text-xs text-gray-500 dark:text-gray-400">
                                        {values[t.type]?.trim() === '' ? 'No limit: every approved day is paid' : 'Paid days per staff member this year'}
                                    </span>
                                </span>
                                <span className="flex items-center gap-2">
                                    <input type="number" min={0} max={366} inputMode="numeric" placeholder="No limit"
                                        value={values[t.type] ?? ''} onChange={(e) => setValues((v) => ({ ...v, [t.type]: e.target.value }))}
                                        className="h-10 w-28 rounded-lg border border-gray-300 bg-white px-3 text-right text-gray-900 focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-900 dark:text-white" />
                                    <span className="w-8 text-sm text-gray-500 dark:text-gray-400">days</span>
                                </span>
                            </label>
                        ))}
                    </div>
                    <ul className="list-disc space-y-1 pl-5 text-xs text-gray-500 dark:text-gray-400">
                        <li>Sundays inside a leave are not counted.</li>
                        <li>Leave beyond the balance can still be approved; the extra days are unpaid and count towards the salary loss of pay.</li>
                        <li>Balances start again each academic year. Changing the policy doesn't change leave that was already approved.</li>
                        <li>Leave the box empty for no limit, or enter 0 to make that type always unpaid.</li>
                    </ul>
                    <div className="flex justify-end">
                        <Button onClick={save} isLoading={saving} loadingText="Saving...">Save policy</Button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default LeavePolicyPage;
