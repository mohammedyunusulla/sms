import { FC, useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import toast from 'react-hot-toast';
import {
    PageHeader,
    Button,
    Badge,
    DataTable,
    LoadingSpinner,
    EmptyState,
    ConfirmDialog,
} from '@/components';
import { examService } from '@/services/modules/examService';
import { usePermissions } from '@/hooks/usePermissions';
import { useAuthStore } from '@/stores/authStore';
import { Permission } from '@/config/permissions';

interface IExamConfig {
    id: number;
    exam_category: string;
    exam_code: string;
    exam_name: string;
    sequence_order: number;
}

const ExamList: FC = () => {
    const navigate = useNavigate();
    const { hasPermission } = usePermissions();
    const user = useAuthStore((s) => s.user);
    const academicYear = user?.current_academic_year;
    // Publishing results is for the institution's admins (the backend allows Institution Admin and Principal)
    const canPublish = ['SUPER_ADMIN', 'INSTITUTION_ADMIN', 'PRINCIPAL'].includes(String(user?.role || ''));
    const [published, setPublished] = useState<Record<number, string>>({});
    const [publishTarget, setPublishTarget] = useState<IExamConfig | null>(null);
    const [publishing, setPublishing] = useState(false);

    // State
    const [exams, setExams] = useState<IExamConfig[]>([]);
    const [loading, setLoading] = useState(false);
    const [selectedRows, setSelectedRows] = useState<IExamConfig[]>([]);
    const [showBulkDeleteConfirm, setShowBulkDeleteConfirm] = useState(false);
    const [deleteTarget, setDeleteTarget] = useState<number | null>(null);
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

    // Fetch exams on mount
    useEffect(() => {
        fetchExams();
    }, []);

    const fetchPublished = async () => {
        if (!academicYear?.id) return;
        try {
            const rows = await examService.listPublishedResults(academicYear.id);
            setPublished(Object.fromEntries(rows.map((r) => [r.exam_type_id, r.published_at])));
        } catch {
            setPublished({});
        }
    };
    useEffect(() => {
        fetchPublished();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [academicYear?.id]);

    const confirmPublishToggle = async () => {
        if (!publishTarget || !academicYear?.id) return;
        const publish = !published[publishTarget.id];
        try {
            setPublishing(true);
            await examService.setResultsPublished(publishTarget.id, academicYear.id, publish);
            toast.success(publish
                ? `${publishTarget.exam_name} results are now visible to students and parents`
                : `${publishTarget.exam_name} results are hidden from students and parents`);
            await fetchPublished();
        } catch (err) {
            toast.error((err as Error).message || 'Failed to update results');
        } finally {
            setPublishing(false);
            setPublishTarget(null);
        }
    };

    const fetchExams = async () => {
        setLoading(true);
        try {
            const response = await examService.list();
            // Extract array from response - handle both array and object with data property
            const examData = Array.isArray(response) ? response : (response?.data || []);
            setExams(examData as IExamConfig[]);
        } catch (err: any) {
            toast.error(err.message || 'Failed to fetch exams');
            setExams([]);
        } finally {
            setLoading(false);
        }
    };

    const handleDeleteExam = (id: number) => {
        setDeleteTarget(id);
        setShowDeleteConfirm(true);
    };

    const confirmDelete = async () => {
        if (!deleteTarget) return;

        try {
            await examService.delete(String(deleteTarget));
            toast.success('Exam deleted successfully');
            setShowDeleteConfirm(false);
            setDeleteTarget(null);
            await fetchExams();
        } catch (err: any) {
            toast.error(err.message || 'Failed to delete exam');
        }
    };

    const handleBulkDelete = () => {
        if (selectedRows.length === 0) {
            toast.error('Please select exams to delete');
            return;
        }
        setShowBulkDeleteConfirm(true);
    };

    // Try every selected exam; exams still in use (marks, timetable, seating) are refused with the reason
    const confirmBulkDelete = async () => {
        let deleted = 0;
        const refused: string[] = [];
        for (const exam of selectedRows) {
            try {
                await examService.delete(String(exam.id));
                deleted += 1;
            } catch (err: unknown) {
                refused.push((err as { message?: string })?.message || `Couldn't delete ${exam.exam_name || 'an exam'}`);
            }
        }
        if (deleted) toast.success(`${deleted} exam(s) deleted`);
        refused.slice(0, 3).forEach((message) => toast.error(message));
        if (refused.length > 3) toast.error(`…and ${refused.length - 3} more couldn't be deleted`);
        setShowBulkDeleteConfirm(false);
        setSelectedRows([]);
        await fetchExams();
    };

    // Get category color variant
    const getCategoryVariant = (category: string): 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'secondary' => {
        switch (category?.toLowerCase()) {
            case 'Formative':
                return 'info';
            case 'Summative':
                return 'success';
            default:
                return 'secondary';
        }
    };

    // Table columns
    const columns = [
        {
            key: 'exam_name',
            label: 'Exam Name',
            render: (value: string, row: IExamConfig) => (
                <div
                    className="font-medium text-gray-900 dark:text-white cursor-pointer hover:text-blue-600 dark:hover:text-blue-400"
                    onClick={() => navigate(`/exams/${row.id}`)}
                >
                    {value}
                </div>
            )
        },
        {
            key: 'exam_code',
            label: 'Code',
            render: (value: string) => (
                <div className="font-mono text-sm text-gray-900 dark:text-white">
                    {value}
                </div>
            )
        },
        {
            key: 'exam_category',
            label: 'Category',
            render: (value: string) => (
                <Badge variant={getCategoryVariant(value)} children={value} />
            )
        },
        {
            key: 'sequence_order',
            label: 'Order',
            render: (value: number) => (
                <div className="text-center text-gray-900 dark:text-white font-medium">
                    #{value}
                </div>
            )
        },
        {
            key: 'id',
            label: `Results${academicYear?.year_name ? ` (${academicYear.year_name})` : ''}`,
            render: (_: number, row: IExamConfig) => (
                <div data-testid={`results-${row.id}`}>
                    {published[row.id] ? (
                        <Badge variant="success" children="Published" />
                    ) : (
                        <Badge variant="secondary" children="Not published" />
                    )}
                    {published[row.id] && (
                        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                            {new Date(published[row.id]).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}
                        </p>
                    )}
                </div>
            )
        }
    ];

    // Show loading spinner
    if (loading && exams.length === 0) {
        return <LoadingSpinner fullHeight message="Loading exams..." />;
    }

    return (
        <div className="space-y-6">
            {/* Page Header */}
            <PageHeader
                title="Exam Configuration"
                subtitle="Manage exam types and categories"
                breadcrumbs={[
                    { label: 'Dashboard', href: '/dashboard' },
                    { label: 'Exams Types & Configs', href: '/exams' },
                ]}
                actions={
                    hasPermission(Permission.MANAGE_EXAMS) ? (
                        <Button
                            variant="primary"
                            onClick={() => navigate('/exams/new')}
                        >
                            + New Exam Type
                        </Button>
                    ) : undefined
                }
            />

            {/* Bulk Actions */}
            {selectedRows.length > 0 && (
                <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 p-4 rounded-lg flex items-center justify-between">
                    <span className="text-sm text-blue-700 dark:text-blue-300">
                        {selectedRows.length} exam{selectedRows.length !== 1 ? 's' : ''} selected
                    </span>
                    {hasPermission(Permission.MANAGE_EXAMS) && (
                        <Button
                            variant="danger"
                            size="sm"
                            onClick={handleBulkDelete}
                        >
                            🗑️ Delete Selected
                        </Button>
                    )}
                </div>
            )}

            {/* Exams Table */}
            {exams.length > 0 ? (
                <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                    <DataTable
                        columns={columns}
                        data={exams}
                        loading={loading}
                        selectable={hasPermission(Permission.MANAGE_EXAMS)}
                        // the table only knows what's ticked through this (without it each tick started from nothing)
                        selectedRows={selectedRows.map((r) => r.id) as unknown as string[]}
                        onSelectionChange={(selected) => {
                            setSelectedRows(selected.map(item => item as unknown as IExamConfig) || []);
                        }}
                        actions={(row: IExamConfig) => (
                            <div className="flex gap-2">
                                {canPublish && academicYear?.id && (
                                    <Button
                                        size="sm"
                                        variant={published[row.id] ? 'secondary' : 'success'}
                                        onClick={() => setPublishTarget(row)}
                                    >
                                        {published[row.id] ? 'Unpublish results' : 'Publish results'}
                                    </Button>
                                )}
                                {hasPermission(Permission.MANAGE_EXAMS) && (
                                    <Button
                                        size="sm"
                                        variant="info"
                                        onClick={() => navigate(`/exams/${row.id}/edit`)}
                                    >
                                        Edit
                                    </Button>
                                )}
                                {hasPermission(Permission.MANAGE_EXAMS) && (
                                    <Button
                                        size="sm"
                                        variant="danger"
                                        onClick={() => handleDeleteExam(row.id)}
                                    >
                                        Delete
                                    </Button>
                                )}
                            </div>
                        )}
                    />
                </div>
            ) : (
                <EmptyState
                    icon="📝"
                    title="No Exam Types Found"
                    description="Create exam types to get started."
                    action={
                        hasPermission(Permission.MANAGE_EXAMS) ? (
                            <Button
                                variant="primary"
                                onClick={() => navigate('/exams/new')}
                            >
                                + Create First Exam Type
                            </Button>
                        ) : undefined
                    }
                />
            )}

            {/* Delete Confirmation Dialog */}
            <ConfirmDialog
                isOpen={!!publishTarget}
                type={publishTarget && published[publishTarget.id] ? 'warning' : 'success'}
                title={publishTarget && published[publishTarget.id] ? 'Unpublish results' : 'Publish results'}
                message={publishTarget
                    ? (published[publishTarget.id]
                        ? `Hide ${publishTarget.exam_name} results (${academicYear?.year_name || 'this year'}) from students and parents again?`
                        : `Show ${publishTarget.exam_name} results (${academicYear?.year_name || 'this year'}) to students and parents? They will see each subject's marks, grade, rank and can download the report card. Make sure all marks are entered first.`)
                    : ''}
                confirmText={publishTarget && published[publishTarget.id] ? 'Unpublish' : 'Publish'}
                isLoading={publishing}
                onConfirm={confirmPublishToggle}
                onCancel={() => setPublishTarget(null)}
            />

            <ConfirmDialog
                isOpen={showDeleteConfirm}
                type="danger"
                title="Delete Exam"
                message="Delete this exam type? Exams that already have marks, an exam timetable or seating plans can't be deleted - you'll be told what is in the way."
                onConfirm={confirmDelete}
                onCancel={() => {
                    setShowDeleteConfirm(false);
                    setDeleteTarget(null);
                }}
            />

            {/* Bulk Delete Confirmation Dialog */}
            <ConfirmDialog
                isOpen={showBulkDeleteConfirm}
                type="danger"
                title="Delete Multiple Exams"
                message={`Are you sure you want to delete ${selectedRows.length} exam type(s)? This action cannot be undone.`}
                onConfirm={confirmBulkDelete}
                onCancel={() => setShowBulkDeleteConfirm(false)}
            />
        </div>
    );
};

export default ExamList;
