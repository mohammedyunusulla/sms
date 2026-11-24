/**
 * Bus Staff Dashboard
 * Today at a glance (students on the bus now / dropped off) and big buttons for the two bus pages.
 * Bus staff used to land on "No dashboard available for your role".
 */

import { FC, useEffect, useState } from 'react';
import { Link } from 'react-router';
import { useAuth } from '../../hooks/useAuth';
import { usePermissions } from '../../hooks/usePermissions';
import { Permission } from '../../config/permissions';
import { busScanService, BusScanRecord } from '../../services/modules/busScanService';

const BusStaffDashboard: FC = () => {
    const { user } = useAuth();
    const { hasPermission } = usePermissions();
    const [status, setStatus] = useState<BusScanRecord[] | null>(null);
    const [failed, setFailed] = useState(false);

    useEffect(() => {
        let cancelled = false;
        busScanService
            .getStatus(user?.current_academic_year?.id)
            .then((rows) => !cancelled && setStatus(rows))
            .catch(() => !cancelled && setFailed(true));
        return () => {
            cancelled = true;
        };
    }, [user?.current_academic_year?.id]);

    // each student's latest scan today: checked in = on the bus now, checked out = dropped off
    const onBus = (status || []).filter((r) => r.scan_type === 'CHECK_IN').length;
    const dropped = (status || []).filter((r) => r.scan_type === 'CHECK_OUT').length;
    const name = user?.first_name || user?.username || '';

    const links = [
        { title: 'Scan QR Code', description: "Scan a student's card when they board or get off", path: '/bus-scan/scan', icon: '📷', permission: Permission.MANAGE_BUS_SCAN },
        { title: 'Tracking Report', description: 'Who boarded and got off, and when', path: '/bus-scan/report', icon: '📋', permission: Permission.VIEW_BUS_SCAN },
    ].filter((l) => hasPermission(l.permission));

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Welcome{name ? `, ${name}` : ''}</h1>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                    {new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' })}
                </p>
            </div>

            <div className="grid grid-cols-2 gap-4" data-testid="bus-today">
                <div className="rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
                    <p className="text-sm text-gray-500 dark:text-gray-400">On the bus now</p>
                    <p className="mt-1 text-3xl font-bold text-gray-900 dark:text-white">{status === null && !failed ? '…' : onBus}</p>
                </div>
                <div className="rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
                    <p className="text-sm text-gray-500 dark:text-gray-400">Dropped off today</p>
                    <p className="mt-1 text-3xl font-bold text-gray-900 dark:text-white">{status === null && !failed ? '…' : dropped}</p>
                </div>
            </div>
            {failed && <p className="text-sm text-red-600 dark:text-red-400">Couldn't load today's scans.</p>}

            {links.length === 0 ? (
                <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-6 text-sm text-yellow-700 dark:border-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-300">
                    Your role has no bus pages yet. Ask the institution admin to give the Bus Staff role its permissions.
                </div>
            ) : (
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2" data-testid="bus-links">
                    {links.map((l) => (
                        <Link
                            key={l.path}
                            to={l.path}
                            className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm transition hover:border-blue-400 hover:shadow-md dark:border-gray-700 dark:bg-gray-800 dark:hover:border-blue-500"
                        >
                            <div className="text-3xl">{l.icon}</div>
                            <p className="mt-3 text-lg font-semibold text-gray-900 dark:text-white">{l.title}</p>
                            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{l.description}</p>
                        </Link>
                    ))}
                </div>
            )}
        </div>
    );
};

export default BusStaffDashboard;
