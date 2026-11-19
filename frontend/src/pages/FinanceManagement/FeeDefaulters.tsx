/**
 * Fee Defaulters Report
 * Students with overdue fees as of a date: fees past their due date with a balance, or installment
 * plans with unpaid installments past their due date. Filter by class; download as CSV.
 */

import { FC, useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router';
import toast from 'react-hot-toast';
import { PageHeader, DataTable, Button, StatCard, FormInput, FormSelect, Badge } from '../../components';
import { financeService } from '../../services/modules/financeService';
import { useAuthStore } from '../../stores/authStore';
import { IDefaulterRow, IDefaultersReport } from '../../types/index';

const money = (v: number) => `₹${Number(v || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
const formatDate = (d?: string) =>
    d ? new Date(d).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '-';
const today = () => new Date().toLocaleDateString('en-CA');

const FeeDefaulters: FC = () => {
    const navigate = useNavigate();
    const { user } = useAuthStore();
    const academicYearId = user?.current_academic_year?.id;

    const [asOf, setAsOf] = useState(today());
    const [classFilter, setClassFilter] = useState('');
    const [report, setReport] = useState<IDefaultersReport | null>(null);
    const [loading, setLoading] = useState(false);

    const load = useCallback(async () => {
        if (!academicYearId) return;
        try {
            setLoading(true);
            setReport(await financeService.getDefaulters(academicYearId, asOf));
        } catch (error) {
            toast.error((error as Error).message || 'Failed to load the defaulters report');
            setReport(null);
        } finally {
            setLoading(false);
        }
    }, [academicYearId, asOf]);

    useEffect(() => { load(); }, [load]);

    const rows = useMemo(
        () => (report?.defaulters || []).filter((r) => !classFilter || r.class === classFilter),
        [report, classFilter],
    );
    const classOptions = useMemo(
        () => [...new Set((report?.defaulters || []).map((r) => r.class).filter(Boolean) as string[])].sort()
            .map((c) => ({ label: c, value: c })),
        [report],
    );
    const students = new Set(rows.map((r) => r.student_id)).size;
    const overdue = rows.reduce((s, r) => s + Number(r.overdue_amount), 0);
    const owed = rows.reduce((s, r) => s + Number(r.balance), 0);

    const downloadCsv = () => {
        const header = ['Student', 'Admission No', 'Class', 'Section', 'Fee', 'Due Date', 'Days Overdue', 'Overdue Amount', 'Total Balance', 'Parent Phone', 'Student Phone'];
        const quote = (v: unknown) => `"${String(v ?? '').replace(/"/g, '""')}"`;
        const lines = rows.map((r) => [r.student_name, r.admission_number, r.class, r.section, r.fee_name, r.due_date,
            r.days_overdue, r.overdue_amount, r.balance, r.parent_phone, r.phone].map(quote).join(','));
        const blob = new Blob([[header.map(quote).join(','), ...lines].join('\r\n')], { type: 'text/csv;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `fee-defaulters-${asOf}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    };

    const columns = [
        {
            key: 'student_name',
            label: 'Student',
            render: (_: unknown, r: IDefaulterRow) => (
                <div>
                    <p className="font-medium text-gray-900 dark:text-white">{r.student_name}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                        {[r.class, r.section && `Section ${r.section}`, r.admission_number].filter(Boolean).join(' · ') || '-'}
                    </p>
                </div>
            ),
        },
        { key: 'fee_name', label: 'Fee', render: (v: string) => <span>{v || '-'}</span> },
        {
            key: 'due_date',
            label: 'Due Since',
            render: (_: unknown, r: IDefaulterRow) => (
                <div>
                    <p className="text-sm">{formatDate(r.due_date)}</p>
                    <Badge variant={r.days_overdue > 30 ? 'danger' : 'warning'} size="sm">{r.days_overdue} days</Badge>
                </div>
            ),
        },
        {
            key: 'overdue_amount',
            label: 'Overdue',
            className: 'text-right',
            render: (v: number) => <span className="font-semibold text-red-600 dark:text-red-400">{money(v)}</span>,
        },
        { key: 'balance', label: 'Total Balance', className: 'text-right', render: (v: number) => <span>{money(v)}</span> },
        {
            key: 'parent_phone',
            label: 'Contact',
            render: (_: unknown, r: IDefaulterRow) => (
                <div className="text-sm">
                    {r.parent_phone && <p>Parent: {r.parent_phone}</p>}
                    {r.phone && <p className="text-xs text-gray-500 dark:text-gray-400">Student: {r.phone}</p>}
                    {!r.parent_phone && !r.phone && '-'}
                </div>
            ),
        },
    ];

    return (
        <div className="space-y-6">
            <PageHeader
                title="Fee Defaulters"
                subtitle="Students with fees or installments past their due date"
                breadcrumbs={[{ label: 'Dashboard', href: '/dashboard' }, { label: 'Fee Defaulters', href: '#' }]}
            />

            <div className="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
                <div className="grid grid-cols-1 items-end gap-4 md:grid-cols-4">
                    <FormInput label="Overdue as of" type="date" value={asOf} max={today()} onChange={(e) => setAsOf(e.target.value || today())} />
                    <FormSelect
                        label="Class"
                        value={classFilter}
                        onChange={(e) => setClassFilter(e.target.value)}
                        options={[{ label: 'All classes', value: '' }, ...classOptions]}
                    />
                    <div className="flex gap-2 md:col-span-2 md:justify-end">
                        <Button variant="secondary" onClick={load} isLoading={loading} loadingText="Loading...">Refresh</Button>
                        <Button variant="primary" onClick={downloadCsv} disabled={rows.length === 0}>Download CSV</Button>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <StatCard title="Students Overdue" value={students} icon="👥" />
                <StatCard title="Overdue Amount" value={money(overdue)} icon="⏰" />
                <StatCard title="Total Balance of These Students' Fees" value={money(owed)} icon="⏳" />
            </div>

            <DataTable
                columns={columns}
                data={rows}
                loading={loading}
                striped
                emptyMessage={academicYearId ? `No overdue fees as of ${formatDate(asOf)}` : 'No academic year selected'}
                actions={() => (
                    <Button variant="outline" size="sm" onClick={() => navigate('/finance/fee-collection')}>
                        Collect
                    </Button>
                )}
            />
        </div>
    );
};

export default FeeDefaulters;
