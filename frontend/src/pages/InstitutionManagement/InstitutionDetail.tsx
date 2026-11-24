/**
 * Institution Detail Page
 * View detailed information about a specific institution
 */

import { FC, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router';
import toast from 'react-hot-toast';
import {
    PageHeader,
    Button,
    Badge,
    LoadingSpinner,
    EmptyState,
    ConfirmDialog,
} from '../../components';
import { institutionService } from '../../services/modules/institutionService';
import { usePermissions } from '../../hooks/usePermissions';
import { IInstitution } from '../../types/index';

// Institutions have is_active (there is no `status` field; reading status.charAt crashed the page)
const isInstitutionActive = (institution: unknown): boolean => {
    const value = institution as { is_active?: boolean; status?: string };
    return value.is_active ?? String(value.status ?? '').toLowerCase() === 'active';
};

const InstitutionDetail: FC = () => {
    const navigate = useNavigate();
    const { id } = useParams();
    const { isSuperAdmin } = usePermissions();

    const [selectedInstitution, setSelectedInstitution] = useState<IInstitution | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Fetch institution data on mount
    useEffect(() => {
        if (id) {
            const fetchInstitution = async () => {
                setLoading(true);
                try {
                    const institution = await institutionService.getById(id);
                    setSelectedInstitution(institution);
                } catch (err: any) {
                    setError(err.message || 'Failed to fetch institution');
                } finally {
                    setLoading(false);
                }
            };
            fetchInstitution();
        }
    }, [id]);

    // Handle delete
    // Deleting needs the institution's code typed back (QA S14: it was one confirm click)
    const [deleteOpen, setDeleteOpen] = useState(false);
    const [deleteCode, setDeleteCode] = useState('');
    const [deleting, setDeleting] = useState(false);
    const handleDelete = () => {
        if (!selectedInstitution) return;
        setDeleteCode('');
        setDeleteOpen(true);
    };
    const confirmDelete = async () => {
        if (!selectedInstitution) return;
        try {
            setDeleting(true);
            await institutionService.deleteInstitution(selectedInstitution.id, deleteCode.trim());
            toast.success('Institution deleted successfully');
            setDeleteOpen(false);
            setTimeout(() => navigate('/institutions'), 1500);
        } catch (err: any) {
            toast.error(err.message || 'Failed to delete institution');
        } finally {
            setDeleting(false);
        }
    };

    // Show loading spinner
    if (loading && !selectedInstitution) {
        return <LoadingSpinner fullHeight message="Loading institution details..." />;
    }

    // Show error message
    if (error) {
        return (
            <div className="space-y-6">
                <PageHeader
                    title="Institution Details"
                    subtitle="View institution information"
                    breadcrumbs={[
                        { label: 'Dashboard', href: '/dashboard' },
                        { label: 'Institutions', href: '/institutions' },
                        { label: 'Details', href: '#' },
                    ]}
                />
                <div className="p-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                    <p className="text-red-600 dark:text-red-400 mb-4">{error}</p>
                    <Button variant="secondary" onClick={() => navigate('/institutions')}>
                        Back to Institutions
                    </Button>
                </div>
            </div>
        );
    }

    // Show empty state if no institution found
    if (!selectedInstitution) {
        return (
            <div className="space-y-6">
                <PageHeader
                    title="Institution Details"
                    subtitle="View institution information"
                    breadcrumbs={[
                        { label: 'Dashboard', href: '/dashboard' },
                        { label: 'Institutions', href: '/institutions' },
                        { label: 'Details', href: '#' },
                    ]}
                />
                <EmptyState
                    icon="🏫"
                    title="Institution Not Found"
                    description="The institution you're looking for doesn't exist or has been deleted."
                    action={
                        <Button variant="secondary" onClick={() => navigate('/institutions')}>
                            Back to Institutions
                        </Button>
                    }
                />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Page Header */}
            <PageHeader
                title={selectedInstitution.name}
                subtitle="View and manage institution information"
                breadcrumbs={[
                    { label: 'Dashboard', href: '/dashboard' },
                    { label: 'Institutions', href: '/institutions' },
                    { label: selectedInstitution.name, href: '#' },
                ]}
                actions={
                    <div className="flex items-center gap-3">
                        {isSuperAdmin && (
                            <Button
                                variant="secondary"
                                onClick={() => navigate(`/institutions/${selectedInstitution.id}/edit`)}
                            >
                                Edit Institution
                            </Button>
                        )}
                        {isSuperAdmin && (
                            <Button
                                variant="danger"
                                onClick={handleDelete}
                            >
                                Delete Institution
                            </Button>
                        )}
                    </div>
                }
            />

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Main Content */}
                <div className="lg:col-span-2 space-y-6">
                    {/* Basic Information Card */}
                    <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                            Basic Information
                        </h3>
                        <div className="space-y-4">
                            {/* Institution Name and Status */}
                            <div className="flex items-center justify-between pb-4 border-b border-gray-200 dark:border-gray-700">
                                <div>
                                    <p className="text-sm text-gray-600 dark:text-gray-400">Institution Name</p>
                                    <p className="text-lg font-semibold text-gray-900 dark:text-white">
                                        {selectedInstitution.name}
                                    </p>
                                </div>
                                <Badge
                                    variant={isInstitutionActive(selectedInstitution) ? 'success' : 'warning'}
                                    text={isInstitutionActive(selectedInstitution) ? 'Active' : 'Inactive'}
                                />
                            </div>

                            {/* Email and Phone */}
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <p className="text-sm text-gray-600 dark:text-gray-400">Email</p>
                                    <p className="text-gray-900 dark:text-white font-medium">{selectedInstitution.email}</p>
                                </div>
                                <div>
                                    <p className="text-sm text-gray-600 dark:text-gray-400">Phone</p>
                                    <p className="text-gray-900 dark:text-white font-medium">{selectedInstitution.phone}</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Address Information Card */}
                    <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                            Address Information
                        </h3>
                        <div className="space-y-4">
                            {/* Full Address */}
                            <div>
                                <p className="text-sm text-gray-600 dark:text-gray-400">Street Address</p>
                                <p className="text-gray-900 dark:text-white font-medium">{selectedInstitution.address}</p>
                            </div>

                            {/* City, State, Postal Code */}
                            <div className="grid grid-cols-3 gap-4">
                                <div>
                                    <p className="text-sm text-gray-600 dark:text-gray-400">City</p>
                                    <p className="text-gray-900 dark:text-white font-medium">{selectedInstitution.city}</p>
                                </div>
                                <div>
                                    <p className="text-sm text-gray-600 dark:text-gray-400">State</p>
                                    <p className="text-gray-900 dark:text-white font-medium">{selectedInstitution.state}</p>
                                </div>
                                <div>
                                    <p className="text-sm text-gray-600 dark:text-gray-400">Postal Code</p>
                                    <p className="text-gray-900 dark:text-white font-medium">{selectedInstitution.postal_code}</p>
                                </div>
                            </div>

                            {/* Country */}
                            <div>
                                <p className="text-sm text-gray-600 dark:text-gray-400">Country</p>
                                <p className="text-gray-900 dark:text-white font-medium">{selectedInstitution.country}</p>
                            </div>
                        </div>
                    </div>

                    {/* Quick Actions Card */}
                    <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                            Quick Actions
                        </h3>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                            <button className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-colors">
                                <div className="text-2xl mb-2">👥</div>
                                <span className="text-sm font-medium text-blue-700 dark:text-blue-400">Manage Users</span>
                            </button>
                            <button className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg hover:bg-green-100 dark:hover:bg-green-900/40 transition-colors">
                                <div className="text-2xl mb-2">📚</div>
                                <span className="text-sm font-medium text-green-700 dark:text-green-400">Manage Classes</span>
                            </button>
                            <button className="p-4 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg hover:bg-purple-100 dark:hover:bg-purple-900/40 transition-colors">
                                <div className="text-2xl mb-2">📊</div>
                                <span className="text-sm font-medium text-purple-700 dark:text-purple-400">View Reports</span>
                            </button>
                            <button className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg hover:bg-yellow-100 dark:hover:bg-yellow-900/40 transition-colors">
                                <div className="text-2xl mb-2">💰</div>
                                <span className="text-sm font-medium text-yellow-700 dark:text-yellow-400">Finance</span>
                            </button>
                            <button className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/40 transition-colors">
                                <div className="text-2xl mb-2">📅</div>
                                <span className="text-sm font-medium text-red-700 dark:text-red-400">Timetable</span>
                            </button>
                            <button className="p-4 bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded-lg hover:bg-indigo-100 dark:hover:bg-indigo-900/40 transition-colors">
                                <div className="text-2xl mb-2">⚙️</div>
                                <span className="text-sm font-medium text-indigo-700 dark:text-indigo-400">Settings</span>
                            </button>
                        </div>
                    </div>
                </div>

                {/* Sidebar */}
                <div className="lg:col-span-1 space-y-6">
                    {/* Metadata Card */}
                    <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                            Information
                        </h3>
                        <div className="space-y-3">
                            <div>
                                <p className="text-xs text-gray-600 dark:text-gray-400 uppercase tracking-wide">Institution ID</p>
                                <p className="text-sm font-mono text-gray-900 dark:text-white break-all">{selectedInstitution.id}</p>
                            </div>
                            <div>
                                <p className="text-xs text-gray-600 dark:text-gray-400 uppercase tracking-wide">Created At</p>
                                <p className="text-sm text-gray-900 dark:text-white">
                                    {selectedInstitution.created_at
                                        ? new Date(selectedInstitution.created_at).toLocaleDateString('en-US', {
                                            year: 'numeric',
                                            month: 'long',
                                            day: 'numeric',
                                            hour: '2-digit',
                                            minute: '2-digit',
                                        })
                                        : 'N/A'}
                                </p>
                            </div>
                            <div>
                                <p className="text-xs text-gray-600 dark:text-gray-400 uppercase tracking-wide">Last Updated</p>
                                <p className="text-sm text-gray-900 dark:text-white">
                                    {selectedInstitution.updated_at
                                        ? new Date(selectedInstitution.updated_at).toLocaleDateString('en-US', {
                                            year: 'numeric',
                                            month: 'long',
                                            day: 'numeric',
                                            hour: '2-digit',
                                            minute: '2-digit',
                                        })
                                        : 'N/A'}
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Status Card */}
                    <div className={`p-6 rounded-lg border ${isInstitutionActive(selectedInstitution)
                        ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
                        : 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800'
                        }`}>
                        <p className={`text-sm font-medium ${isInstitutionActive(selectedInstitution)
                            ? 'text-green-700 dark:text-green-400'
                            : 'text-yellow-700 dark:text-yellow-400'
                            }`}>
                            {isInstitutionActive(selectedInstitution)
                                ? '✅ Institution is active and operational'
                                : '⚠️ Institution is inactive'}
                        </p>
                    </div>
                </div>
            </div>

            <ConfirmDialog
                isOpen={deleteOpen}
                title="Delete Institution - CRITICAL ACTION"
                message={`This will permanently delete the institution "${selectedInstitution?.name}" including all users, dedicated database, and academic data. This action cannot be undone.`}
                type="danger"
                confirmText="Yes, Permanently Delete"
                cancelText="Cancel"
                isLoading={deleting}
                onConfirm={confirmDelete}
                onCancel={() => setDeleteOpen(false)}
                confirmDisabled={deleteCode.trim().toLowerCase() !== String(selectedInstitution?.code || '').toLowerCase()}
            >
                <div className="mt-4">
                    <label htmlFor="delete-institution-code" className="block text-sm text-gray-700 dark:text-gray-300">
                        Type <strong className="font-mono">{selectedInstitution?.code}</strong> to confirm
                    </label>
                    <input
                        id="delete-institution-code"
                        name="delete_institution_code"
                        value={deleteCode}
                        onChange={(e) => setDeleteCode(e.target.value)}
                        autoComplete="off"
                        className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                    />
                </div>
            </ConfirmDialog>
        </div>
    );
};

export default InstitutionDetail;
