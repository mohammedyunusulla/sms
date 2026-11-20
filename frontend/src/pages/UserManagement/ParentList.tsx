/**
 * Parent List Page
 * Display and manage list of parents with pagination and actions
 */

import { FC, useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import toast from 'react-hot-toast';
import { PageHeader, LoadingSpinner, DataTable, Button, ConfirmDialog } from '../../components';
import { parentService } from '../../services/modules/parentService';
import ParentDetailDialog from './components/ParentDetailDialog';
import { usePermissions } from '../../hooks/usePermissions';
import { Permission } from '../../config/permissions';
import { useLoginAccess } from '../../hooks/useLoginAccess';
import { useDebounce } from '../../hooks/useDebounce';

// "Father / Mother" phones without the "null / null" the list used to show
type Phones = { father_phone?: string | null; mother_phone?: string | null };
const phonesOf = (profile: Phones | undefined, row: { phone?: string | null }) =>
    [profile?.father_phone, profile?.mother_phone].filter(Boolean).join(' / ') || row?.phone || '-';

interface IColumn {
    key: string;
    label: string;
    width?: number;
    render?: (value: any, row: any) => React.ReactNode;
}

interface IPaginationMeta {
    total: number;
    page: number;
    limit: number;
    totalPages: number;
}

const ParentList: FC = () => {
    const navigate = useNavigate();
    const { hasPermission } = usePermissions();
    const [loading, setLoading] = useState(false);
    const [rows, setRows] = useState<any[]>([]);
    const [pagination, setPagination] = useState<IPaginationMeta>({
        total: 0,
        page: 1,
        limit: 10,
        totalPages: 0,
    });
    const [showActionsMenu, setShowActionsMenu] = useState<string | null>(null);
    const [menuPosition, setMenuPosition] = useState<{ top: number; right: number }>({ top: 0, right: 0 });
    const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
    const [selectedParent, setSelectedParent] = useState<any>(null);
    const [currentPage, setCurrentPage] = useState(1);
    const [pageSize] = useState(10);
    const [isParentDetailOpen, setIsParentDetailOpen] = useState(false);
    const [selectedParentIdForDialog, setSelectedParentIdForDialog] = useState<string | null>(null);

    const handleMenuClick = (event: React.MouseEvent, parentId: string) => {
        const button = event.currentTarget as HTMLButtonElement;
        const rect = button.getBoundingClientRect();
        setMenuPosition({
            top: rect.bottom + 8,
            right: window.innerWidth - rect.right,
        });
        setShowActionsMenu(showActionsMenu === parentId ? null : parentId);
    };

    // search box (the server already supported it; the page never sent it - QA A25)
    const [searchTerm, setSearchTerm] = useState('');
    const debouncedSearch = useDebounce(searchTerm, 400);
    useEffect(() => {
        setCurrentPage(1);
    }, [debouncedSearch]);

    useEffect(() => {
        fetchParents(currentPage, pageSize);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [currentPage, pageSize, debouncedSearch]);

    const fetchParents = async (page: number, limit: number) => {
        try {
            setLoading(true);
            const response = await parentService.list({ page, limit, ...(debouncedSearch.trim() ? { search: debouncedSearch.trim() } : {}) });
            const parents = response.data.map((parent: any, index: number) => ({
                ...parent,
                key: parent.id,
                slNo: (page - 1) * limit + index + 1,
            }));
            setRows(parents);
            setPagination(response.meta);
        } catch (error) {
            console.error('Error fetching parents:', error);
            toast.error('Failed to fetch parents');
            setRows([]);
        } finally {
            setLoading(false);
        }
    };

    const handleEdit = (parent: any) => {
        setShowActionsMenu(null);
        navigate(`/parents/${parent.id}/edit`, { state: { parent, mode: 'update' } });
    };

    const handleView = (parent: any) => {
        setSelectedParentIdForDialog(parent.id);
        setIsParentDetailOpen(true);
        setShowActionsMenu(null);
    };

    const handleDelete = (parent: any) => {
        setSelectedParent(parent);
        setDeleteConfirmOpen(true);
        setShowActionsMenu(null);
    };

    const handleConfirmDelete = async () => {
        try {
            setLoading(true);
            await parentService.delete(selectedParent!.id);
            toast.success('Parent deleted. Their records are kept and they can be reactivated.');
            fetchParents(currentPage, pageSize);
            setDeleteConfirmOpen(false);
        } catch (err: any) {
            toast.error(err.message || 'Failed to delete parent.');
        } finally {
            setLoading(false);
        }
    };

    const handleReactivate = async (parent: { id: string | number; full_name?: string }) => {
        setShowActionsMenu(null);
        try {
            setLoading(true);
            await parentService.reactivate(String(parent.id));
            toast.success(`${parent.full_name || 'Parent'} reactivated`);
            fetchParents(currentPage, pageSize);
        } catch (err) {
            toast.error((err as { message?: string })?.message || 'Failed to reactivate parent.');
        } finally {
            setLoading(false);
        }
    };

    const { loginAccessColumn, renderLoginAccessModals } = useLoginAccess({
        onRefresh: () => fetchParents(currentPage, pageSize),
        onEdit: (user) => handleEdit(user),
    });

    const columns: IColumn[] = [
        {
            key: 'slNo',
            label: 'Sl. No',
        },
        {
            key: 'father_name',
            label: 'Father Name',
            // fall back to the account name when the profile has no father name
            render: (_v, row) => <span className="font-medium text-gray-900 dark:text-white truncate">{row.profile?.father_full_name || row.full_name || '-'}</span>,
        },
        {
            key: 'mother_name',
            label: 'Mother Name',
            render: (_v, row) => <span className="font-medium text-gray-900 dark:text-white truncate">{row.profile?.mother_full_name || '-'}</span>,
        },
        {
            key: 'phones',
            label: 'Phone',
            render: (_v, row) => <span className="text-gray-600 dark:text-gray-400">{phonesOf(row.profile, row)}</span>,
        },
        {
            key: 'is_active',
            label: 'Status',
            render: (value) => (
                <span className={`px-3 py-1 rounded-full text-sm font-medium whitespace-nowrap ${value
                    ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                    : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
                    }`}>
                    {value ? 'Active' : 'Inactive'}
                </span>
            ),
        },
        loginAccessColumn,
    ];

    if (loading && rows.length === 0) {
        return <LoadingSpinner fullHeight message="Loading parents..." />;
    }

    return (
        <div className="space-y-6">
            <PageHeader
                title="Parent Management"
                subtitle="Manage parents and view their details"
                breadcrumbs={[
                    { label: 'Dashboard', href: '/dashboard' },
                    { label: 'Parents', href: '#' },
                ]}
                actions={
                    hasPermission(Permission.MANAGE_STUDENTS) ? (
                        <Button
                            variant="primary"
                            onClick={() => navigate('/parents/new')}
                        >
                            + Create Parent
                        </Button>
                    ) : undefined
                }
            />

            <div className="max-w-sm">
                <input
                    type="search"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Search by name, email or phone"
                    aria-label="Search parents"
                    className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                />
            </div>

            <DataTable
                columns={columns}
                data={rows}
                loading={loading}
                pagination={{
                    page: currentPage,
                    pageSize: pageSize,
                    total: pagination?.total,
                    onPageChange: setCurrentPage,
                }}
                actions={(row) => (
                    <button
                        onClick={(e) => handleMenuClick(e, row.id)}
                        className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                        title="More actions"
                    >
                        <svg className="w-5 h-5 text-gray-600 dark:text-gray-400" fill="currentColor" viewBox="0 0 24 24">
                            <circle cx="12" cy="5" r="2" />
                            <circle cx="12" cy="12" r="2" />
                            <circle cx="12" cy="19" r="2" />
                        </svg>
                    </button>
                )}
            />

            {/* Fixed Actions Menu */}
            {showActionsMenu && (
                <>
                    <div className="fixed inset-0 z-40" onClick={() => setShowActionsMenu(null)} />
                    <div
                        className="fixed w-48 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-50"
                        style={{
                            top: `${menuPosition.top}px`,
                            right: `${menuPosition.right}px`,
                        }}
                    >
                        {hasPermission(Permission.MANAGE_STUDENTS) && (
                            <button
                                onClick={() => handleEdit(rows.find(r => r.id === showActionsMenu)!)}
                                className="w-full text-left px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors flex items-center gap-2 first:rounded-t-lg text-gray-900 dark:text-gray-100"
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                </svg>
                                Edit
                            </button>
                        )}
                        <button
                            onClick={() => handleView(rows.find(r => r.id === showActionsMenu)!)}
                            className="w-full text-left px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors flex items-center gap-2 text-gray-900 dark:text-gray-100"
                        >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                            </svg>
                            View
                        </button>
                        {hasPermission(Permission.DELETE_STUDENTS) && rows.find(r => r.id === showActionsMenu)?.is_active === false && (
                            <button
                                onClick={() => handleReactivate(rows.find(r => r.id === showActionsMenu)!)}
                                className="w-full text-left px-4 py-2 hover:bg-green-50 dark:hover:bg-green-900/20 transition-colors flex items-center gap-2 text-green-700 dark:text-green-400 last:rounded-b-lg"
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                </svg>
                                Reactivate
                            </button>
                        )}

                        {hasPermission(Permission.DELETE_STUDENTS) && rows.find(r => r.id === showActionsMenu)?.is_active !== false && (
                            <button
                                onClick={() => handleDelete(rows.find(r => r.id === showActionsMenu)!)}
                                className="w-full text-left px-4 py-2 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors flex items-center gap-2 text-red-600 dark:text-red-400 last:rounded-b-lg"
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                                Delete
                            </button>
                        )}
                    </div>
                </>
            )}

            <ConfirmDialog
                isOpen={deleteConfirmOpen}
                title="Delete Parent"
                message={`Delete "${selectedParent?.full_name}"? They will be marked inactive and can no longer log in. All their records are kept, and you can reactivate them at any time.`}
                type="danger"
                confirmText="Yes, Delete"
                cancelText="Cancel"
                isLoading={loading}
                onConfirm={handleConfirmDelete}
                onCancel={() => setDeleteConfirmOpen(false)}
            />

            {renderLoginAccessModals()}

            {selectedParentIdForDialog && (
                <ParentDetailDialog
                    isOpen={isParentDetailOpen}
                    parentId={selectedParentIdForDialog}
                    onClose={() => {
                        setIsParentDetailOpen(false);
                        setSelectedParentIdForDialog(null);
                    }}
                    onEdit={(parent) => handleEdit(parent)}
                />
            )}
        </div>
    );
};

export default ParentList;