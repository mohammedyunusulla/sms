/**
 * Clerk Dashboard
 * The fee counter's start page: quick links to the pages a clerk's permissions allow.
 */

import { FC } from 'react';
import { Link } from 'react-router';
import { useAuth } from '../../hooks/useAuth';
import { usePermissions } from '../../hooks/usePermissions';
import { Permission } from '../../config/permissions';

interface QuickLink {
    title: string;
    description: string;
    path: string;
    icon: string;
    permission: Permission;
}

const LINKS: QuickLink[] = [
    { title: 'Fee Collection', description: 'Find a student, collect a payment and print the receipt', path: '/finance/fee-collection', icon: '💳', permission: Permission.MANAGE_FEES },
    { title: 'Fee Defaulters', description: 'Students with fees or installments past their due date', path: '/finance/defaulters', icon: '⏰', permission: Permission.MANAGE_FEES },
    { title: 'Fee Structure', description: 'Fees set for each class this year', path: '/finance/fee-structure', icon: '📋', permission: Permission.VIEW_FEES },
    { title: 'Students', description: 'Look up a student', path: '/students', icon: '🎓', permission: Permission.VIEW_STUDENTS },
    { title: 'Classes', description: 'Classes, sections and their students', path: '/classes', icon: '🏫', permission: Permission.VIEW_CLASSES },
];

const ClerkDashboard: FC = () => {
    const { user } = useAuth();
    const { hasPermission } = usePermissions();
    const links = LINKS.filter((l) => hasPermission(l.permission));
    const name = user?.first_name || user?.username || '';

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Welcome{name ? `, ${name}` : ''}</h1>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                    {user?.current_academic_year?.year_name ? `Academic year ${user.current_academic_year.year_name}` : 'Fee counter'}
                </p>
            </div>

            {links.length === 0 ? (
                <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-6 text-sm text-yellow-700 dark:border-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-300">
                    Your role has no pages yet. Ask the institution admin to give the Clerk role its permissions.
                </div>
            ) : (
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3" data-testid="clerk-links">
                    {links.map((l) => (
                        <Link
                            key={l.path}
                            to={l.path}
                            className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm transition hover:border-blue-400 hover:shadow-md dark:border-gray-700 dark:bg-gray-800 dark:hover:border-blue-500"
                        >
                            <div className="text-2xl">{l.icon}</div>
                            <p className="mt-3 font-semibold text-gray-900 dark:text-white">{l.title}</p>
                            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{l.description}</p>
                        </Link>
                    ))}
                </div>
            )}
        </div>
    );
};

export default ClerkDashboard;
