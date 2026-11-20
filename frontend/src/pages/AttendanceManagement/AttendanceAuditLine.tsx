/**
 * "Marked by … — last changed by …" for one day's attendance (times come from the server in UTC).
 */
import { FC } from 'react';

export interface IAttendanceAudit {
    recorded: boolean;
    marked_by_name?: string | null;
    marked_at?: string | null;
    updated_by_name?: string | null;
    updated_at?: string | null;
}

const when = (iso?: string | null) =>
    iso ? new Date(iso).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '';

const AttendanceAuditLine: FC<{ audit?: IAttendanceAudit | null }> = ({ audit }) => {
    if (!audit) return null;
    return (
        <p className="text-sm text-gray-600 dark:text-gray-400" data-testid="attendance-audit">
            {!audit.recorded ? (
                <>Marked by: <span className="italic">not recorded</span> (saved before this was tracked)</>
            ) : (
                <>
                    {audit.marked_by_name ? (
                        <>Marked by <span className="font-medium text-gray-900 dark:text-white">{audit.marked_by_name}</span> · {when(audit.marked_at)}</>
                    ) : (
                        <>Marked by: <span className="italic">not recorded</span></>
                    )}
                    {audit.updated_by_name && (
                        <> — last changed by <span className="font-medium text-gray-900 dark:text-white">{audit.updated_by_name}</span> · {when(audit.updated_at)}</>
                    )}
                </>
            )}
        </p>
    );
};

export default AttendanceAuditLine;
