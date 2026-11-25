/**
 * Dashboard strip for approvers: "3 leave requests waiting" -> Leave requests page.
 * Shows nothing when there is nothing pending (or the user isn't an approver).
 */
import { FC, useEffect, useState } from 'react';
import { Link } from 'react-router';
import { leaveService } from '../../services/modules/leaveService';

const PendingLeaveBanner: FC = () => {
    const [count, setCount] = useState(0);

    useEffect(() => {
        let alive = true;
        leaveService.pendingCount().then((n) => alive && setCount(n)).catch(() => undefined);
        return () => {
            alive = false;
        };
    }, []);

    if (!count) return null;
    return (
        <Link to="/leave/requests"
            className="mb-4 flex items-center justify-between gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 transition-colors hover:bg-amber-100 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-200 dark:hover:bg-amber-900/30">
            <span className="flex items-center gap-2">
                <svg className="h-5 w-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                <span><strong>{count}</strong> leave request{count === 1 ? '' : 's'} waiting for your decision</span>
            </span>
            <span className="font-medium">Review →</span>
        </Link>
    );
};

export default PendingLeaveBanner;
