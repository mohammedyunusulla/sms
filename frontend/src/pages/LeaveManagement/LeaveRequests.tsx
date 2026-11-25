/**
 * Leave requests for approvers: class teachers (their sections' students), the Institution Admin and anyone
 * with the "Approve leave" tick box (everyone's). Pending first; approve in one tap, reject with an optional note.
 */
import { FC, useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { Button, FormSelect, FormTextarea, LoadingSpinner, Modal, PageHeader } from '../../components';
import { leaveErrorMessage, leaveService, LeaveRequest, ReviewData } from '../../services/modules/leaveService';
import LeaveCard from './LeaveCard';
import { formatRange } from './leaveDates';

const TABS = [
    { value: 'PENDING', label: 'Pending' },
    { value: 'APPROVED', label: 'Approved' },
    { value: 'REJECTED', label: 'Not approved' },
    { value: '', label: 'All' },
];

const LeaveRequests: FC = () => {
    const [tab, setTab] = useState('PENDING');
    const [applicantType, setApplicantType] = useState('');
    const [search, setSearch] = useState('');
    const [query, setQuery] = useState('');
    const [data, setData] = useState<ReviewData | null>(null);
    const [loading, setLoading] = useState(true);
    const [busyId, setBusyId] = useState<number | null>(null);
    const [deciding, setDeciding] = useState<{ leave: LeaveRequest; decision: 'APPROVE' | 'REJECT' } | null>(null);
    const [note, setNote] = useState('');

    // search after typing pauses
    useEffect(() => {
        const t = setTimeout(() => setQuery(search.trim()), 350);
        return () => clearTimeout(t);
    }, [search]);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            setData(await leaveService.getRequests({ status: tab, applicant_type: applicantType, search: query }));
        } catch (err) {
            toast.error(leaveErrorMessage(err, 'Could not load leave requests'));
        } finally {
            setLoading(false);
        }
    }, [tab, applicantType, query]);

    useEffect(() => {
        load();
    }, [load]);

    const decide = async (leave: LeaveRequest, decision: 'APPROVE' | 'REJECT', withNote?: string) => {
        setBusyId(leave.id);
        try {
            await leaveService.decide(leave.id, decision, withNote);
            toast.success(decision === 'APPROVE' ? `Leave approved for ${leave.name}` : 'Leave not approved');
            setDeciding(null);
            setNote('');
            load();
        } catch (err) {
            toast.error(leaveErrorMessage(err, 'Could not save the decision'));
        } finally {
            setBusyId(null);
        }
    };

    return (
        <div className="space-y-6">
            <PageHeader
                title="Leave Requests"
                subtitle={data?.full_access ? 'Student and staff leave requests' : 'Leave requests from the students of your class'}
                breadcrumbs={[{ label: 'Dashboard', href: '/dashboard' }, { label: 'Leave Requests', href: '#' }]}
            />

            {data && !data.can_review ? (
                <div className="rounded-lg border border-gray-200 bg-white p-8 text-center text-gray-500 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400">
                    Leave requests appear here for class teachers (for their own sections) and for people allowed to approve leave.
                    You are not a class teacher of any section yet.
                </div>
            ) : (
                <>
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
                        <div className="flex flex-wrap gap-1 rounded-lg bg-gray-100 p-1 dark:bg-gray-800">
                            {TABS.map((t) => (
                                <button key={t.value || 'all'} type="button" onClick={() => setTab(t.value)}
                                    className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${tab === t.value
                                        ? 'bg-white text-gray-900 shadow-sm dark:bg-gray-700 dark:text-white'
                                        : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white'}`}>
                                    {t.label}
                                    {t.value === 'PENDING' && data?.pending ? (
                                        <span className="ml-1.5 rounded-full bg-amber-500 px-1.5 py-0.5 text-xs text-white">{data.pending}</span>
                                    ) : null}
                                </button>
                            ))}
                        </div>
                        <div className="flex flex-col gap-2 sm:flex-row">
                            <input type="search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by name"
                                className="h-10 rounded-lg border border-gray-300 bg-white px-3 text-sm text-gray-900 focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-800 dark:text-white sm:w-56" />
                            {data?.full_access && (
                                <div className="sm:w-44">
                                    <FormSelect value={applicantType} onChange={(e) => setApplicantType(e.target.value)} placeholder="Students and staff"
                                        options={[{ value: 'STUDENT', label: 'Students' }, { value: 'STAFF', label: 'Staff' }]} />
                                </div>
                            )}
                        </div>
                    </div>

                    {loading && !data ? (
                        <div className="flex justify-center py-12"><LoadingSpinner /></div>
                    ) : data && data.requests.length === 0 ? (
                        <div className="rounded-lg border border-dashed border-gray-300 p-8 text-center text-gray-500 dark:border-gray-600 dark:text-gray-400">
                            {tab === 'PENDING' ? 'No pending leave requests. 🎉' : 'No leave requests here.'}
                        </div>
                    ) : (
                        <div className={`grid gap-3 lg:grid-cols-2 ${loading ? 'opacity-60' : ''}`}>
                            {data?.requests.map((r) => (
                                <LeaveCard key={r.id} leave={r} showPerson
                                    actions={r.can_decide ? (
                                        <>
                                            <Button size="sm" variant="success" isLoading={busyId === r.id && !deciding} loadingText="Saving..."
                                                disabled={busyId !== null} onClick={() => decide(r, 'APPROVE')}>Approve</Button>
                                            <Button size="sm" variant="secondary" disabled={busyId !== null}
                                                onClick={() => { setNote(''); setDeciding({ leave: r, decision: 'REJECT' }); }}>Reject</Button>
                                            <Button size="sm" variant="ghost" disabled={busyId !== null}
                                                onClick={() => { setNote(''); setDeciding({ leave: r, decision: 'APPROVE' }); }}>Approve with note</Button>
                                        </>
                                    ) : undefined} />
                            ))}
                        </div>
                    )}
                </>
            )}

            <Modal
                isOpen={!!deciding}
                onClose={() => setDeciding(null)}
                title={deciding?.decision === 'REJECT' ? 'Reject leave request' : 'Approve leave request'}
                size="md"
                footer={
                    <div className="flex justify-end gap-2">
                        <Button variant="secondary" onClick={() => setDeciding(null)}>Cancel</Button>
                        <Button variant={deciding?.decision === 'REJECT' ? 'danger' : 'success'}
                            isLoading={busyId !== null} loadingText="Saving..."
                            onClick={() => deciding && decide(deciding.leave, deciding.decision, note.trim() || undefined)}>
                            {deciding?.decision === 'REJECT' ? 'Reject' : 'Approve'}
                        </Button>
                    </div>
                }
            >
                {deciding && (
                    <div className="space-y-3">
                        <p className="text-sm text-gray-700 dark:text-gray-300">
                            <span className="font-medium">{deciding.leave.name}</span> · {formatRange(deciding.leave.from_date, deciding.leave.to_date)}
                        </p>
                        <FormTextarea label="Note (optional)" rows={3} maxLength={1000} value={note} onChange={(e) => setNote(e.target.value)}
                            placeholder={deciding.decision === 'REJECT' ? 'e.g. Exams that week, please talk to the class teacher' : 'e.g. Get well soon'}
                            help="The applicant sees this note in the app." />
                    </div>
                )}
            </Modal>
        </div>
    );
};

export default LeaveRequests;
