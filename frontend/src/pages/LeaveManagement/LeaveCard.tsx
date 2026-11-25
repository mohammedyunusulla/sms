import { FC, ReactNode } from 'react';
import { Badge } from '../../components';
import { LeaveRequest, LeaveStatus } from '../../services/modules/leaveService';
import { formatRange } from './leaveDates';

const STATUS: Record<LeaveStatus, { label: string; variant: 'warning' | 'success' | 'danger' | 'secondary' }> = {
    PENDING: { label: 'Pending', variant: 'warning' },
    APPROVED: { label: 'Approved', variant: 'success' },
    REJECTED: { label: 'Not approved', variant: 'danger' },
    CANCELLED: { label: 'Cancelled', variant: 'secondary' },
};

const StatusBadge: FC<{ status: LeaveStatus }> = ({ status }) => (
    <Badge variant={STATUS[status].variant} size="sm">{STATUS[status].label}</Badge>
);

interface Props {
    leave: LeaveRequest;
    /** Show who is on leave (approver's list) */
    showPerson?: boolean;
    actions?: ReactNode;
}

const LeaveCard: FC<Props> = ({ leave, showPerson = false, actions }) => (
    <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800 sm:p-5">
        <div className="flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0">
                {showPerson && (
                    <p className="font-semibold text-gray-900 dark:text-white">
                        {leave.name}
                        <span className="ml-2 text-sm font-normal text-gray-500 dark:text-gray-400">
                            {leave.applicant_type === 'STAFF' ? 'Staff' : leave.class_section || 'Student'}
                        </span>
                    </p>
                )}
                <p className={showPerson ? 'text-sm text-gray-700 dark:text-gray-300' : 'font-semibold text-gray-900 dark:text-white'}>
                    {formatRange(leave.from_date, leave.to_date)}
                    <span className="ml-2 text-sm font-normal text-gray-500 dark:text-gray-400">
                        {leave.counted_days != null && leave.counted_days !== leave.days
                            ? `${leave.counted_days} day${leave.counted_days === 1 ? '' : 's'} counted (holidays / weekly offs not counted)`
                            : `${leave.days} day${leave.days === 1 ? '' : 's'}`} · {leave.leave_type_label}
                    </span>
                </p>
            </div>
            <StatusBadge status={leave.status} />
        </div>

        <p className="mt-3 whitespace-pre-line break-words text-sm text-gray-700 dark:text-gray-300">{leave.reason}</p>

        <div className="mt-3 space-y-1 text-xs text-gray-500 dark:text-gray-400">
            {leave.applicant_type === 'STUDENT' && !leave.applied_by_self && leave.applied_by_name && (
                <p>Applied by {leave.applied_by_name}{showPerson ? ' (parent)' : ''}</p>
            )}
            {leave.decided_by_name && (leave.status === 'APPROVED' || leave.status === 'REJECTED') && (
                <p>
                    {leave.status === 'APPROVED' ? 'Approved' : 'Not approved'} by {leave.decided_by_name}
                    {leave.decided_at ? ` on ${new Date(leave.decided_at).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })}` : ''}
                </p>
            )}
            {leave.status === 'APPROVED' && !!leave.unpaid_days && (
                <p className="font-medium text-amber-700 dark:text-amber-400">
                    {leave.paid_days} paid · {leave.unpaid_days} unpaid (beyond the yearly balance)
                </p>
            )}
            {leave.recount_note && <p className="italic">{leave.recount_note}</p>}
            {leave.cover && (
                <p className={leave.cover.covered === leave.cover.periods ? 'text-emerald-700 dark:text-emerald-400' : 'text-amber-700 dark:text-amber-400'}>
                    {leave.cover.covered === leave.cover.periods ? 'Your periods are covered' : 'Periods covered'}: {leave.cover.covered} of {leave.cover.periods}
                </p>
            )}
            {leave.balance && (
                <p className={leave.balance.would_be_unpaid ? 'font-medium text-amber-700 dark:text-amber-400' : ''}>
                    {leave.balance.remaining === null
                        ? `${leave.leave_type_label} leave: no limit`
                        : leave.balance.paid_days === 0
                            ? `${leave.leave_type_label} leave is always unpaid`
                            : `${leave.leave_type_label} balance: ${leave.balance.remaining} of ${leave.balance.paid_days} days left`}
                    {leave.balance.would_be_unpaid ? ` · ${leave.balance.would_be_unpaid} day${leave.balance.would_be_unpaid === 1 ? '' : 's'} would be unpaid` : ''}
                </p>
            )}
            {leave.decision_note && (
                <p className="rounded-md bg-gray-50 px-2 py-1.5 text-gray-700 dark:bg-gray-700/50 dark:text-gray-300">
                    Note: {leave.decision_note}
                </p>
            )}
        </div>

        {actions && <div className="mt-4 flex flex-wrap gap-2">{actions}</div>}
    </div>
);

export default LeaveCard;
