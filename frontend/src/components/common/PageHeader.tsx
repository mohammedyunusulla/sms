import React, { FC } from 'react';
import { Link, useLocation } from 'react-router';
import PageInfo from './PageInfo';
import { getPageHelp } from '../../config/pageHelp';
import { useAuthStore } from '../../stores/authStore';
import { IPageHeaderProps } from '../../types';

/**
 * PageHeader Component
 * Displays page title, subtitle, breadcrumbs, and actions
 * @component
 */
const PageHeader: FC<IPageHeaderProps> = ({
    title,
    titleAddon,
    subtitle,
    breadcrumbs,
    actions,
    className = '',
}) => {
    // the (i) "about this page" button, when the page has help text (config/pageHelp.ts)
    const { pathname } = useLocation();
    const role = useAuthStore((s) => s.user?.role);
    const help = getPageHelp(pathname, role);
    const addon = titleAddon ?? (help ? <PageInfo title={title} help={help} /> : null);
    return (
        <div className={`mb-6 ${className}`}>
            {/* Breadcrumbs */}
            {breadcrumbs && breadcrumbs.length > 0 && (
                <div className="mb-4 flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                    {breadcrumbs.map((breadcrumb, index) => (
                        <React.Fragment key={index}>
                            {index > 0 && <span className="text-gray-400 dark:text-gray-600">/</span>}
                            {/* in-app link (no full page reload); "#" / no href = the current page, shown as text */}
                            {breadcrumb.href && breadcrumb.href !== '#' ? (
                                <Link
                                    to={breadcrumb.href}
                                    className="hover:text-gray-900 dark:hover:text-white transition-colors"
                                >
                                    {breadcrumb.label}
                                </Link>
                            ) : (
                                <span className="text-gray-900 dark:text-white font-medium">
                                    {breadcrumb.label}
                                </span>
                            )}
                        </React.Fragment>
                    ))}
                </div>
            )}

            {/* Header with Title and Actions */}
            <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
                <div className="flex-1">
                    <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                        {title}
                        {addon && <span className="ml-2 inline-flex align-middle">{addon}</span>}
                    </h1>
                    {subtitle && (
                        <p className="text-gray-600 dark:text-gray-400">
                            {subtitle}
                        </p>
                    )}
                </div>

                {/* Actions */}
                {actions && (
                    <div className="flex items-center gap-2">
                        {actions}
                    </div>
                )}
            </div>
        </div>
    );
};

export default PageHeader;
