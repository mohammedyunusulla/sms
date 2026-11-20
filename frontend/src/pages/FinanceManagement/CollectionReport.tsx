/**
 * Fee Collection Report
 * Payments received in a date range (optionally one class): totals, split by payment mode, every payment,
 * and an Excel export. Cancelled payments are left out.
 */

import { FC, useCallback, useEffect, useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import * as XLSX from 'xlsx';
import { PageHeader, DataTable, Button, StatCard, FormInput, FormSelect } from '../../components';
import { financeService } from '../../services/modules/financeService';
import { ICollectionPayment, ICollectionReport } from '../../types/index';

const money = (v: number) => `₹${Number(v || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
const formatDate = (d?: string) =>
    d ? new Date(d + 'T00:00:00').toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '-';
const ymd = (d: Date) => d.toLocaleDateString('en-CA');
const modeLabel = (p: ICollectionPayment) => p.payment_mode_label || p.payment_mode || '-';

type Range = { from: string; to: string };
const PRESETS: { key: string; label: string; range: () => Range }[] = [
    { key: 'today', label: 'Today', range: () => ({ from: ymd(new Date()), to: ymd(new Date()) }) },
    {
        key: 'week',
        label: 'This week',
        range: () => {
            const now = new Date();
            const monday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - ((now.getDay() + 6) % 7));
            return { from: ymd(monday), to: ymd(now) };
        },
    },
    {
        key: 'month',
        label: 'This month',
        range: () => {
            const now = new Date();
            return { from: ymd(new Date(now.getFullYear(), now.getMonth(), 1)), to: ymd(now) };
        },
    },
];

const CollectionReport: FC = () => {
    const [range, setRange] = useState<Range>(() => PRESETS[2].range());
    const [classId, setClassId] = useState('');
    const [classes, setClasses] = useState<{ label: string; value: string }[]>([]);
    const [report, setReport] = useState<ICollectionReport | null>(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        financeService
            .listClasses()
            .then((list: { id: number; class_name?: string; name?: string }[]) =>
                setClasses(list.map((c) => ({ label: c.class_name || c.name || `Class ${c.id}`, value: String(c.id) }))))
            .catch(() => setClasses([]));
    }, []);

    const load = useCallback(async () => {
        if (range.from > range.to) {
            toast.error("'From' date can't be after 'To' date");
            return;
        }
        try {
            setLoading(true);
            setReport(await financeService.getCollectionReport({ start_date: range.from, end_date: range.to, class_id: classId }));
        } catch (error) {
            toast.error((error as Error).message || 'Failed to load the collection report');
            setReport(null);
        } finally {
            setLoading(false);
        }
    }, [range, classId]);

    useEffect(() => { load(); }, [load]);

    const rows = report?.payments || [];
    const modes = useMemo(
        () => Object.entries(report?.collection_by_mode || {}).sort((a, b) => b[1] - a[1]),
        [report],
    );
    const activePreset = PRESETS.find((p) => {
        const r = p.range();
        return r.from === range.from && r.to === range.to;
    })?.key;
    const className = classes.find((c) => c.value === classId)?.label;

    const exportExcel = () => {
        const header = ['Date', 'Receipt No', 'Student', 'Admission No', 'Class', 'Section', 'Fee', 'Mode', 'Reference', 'Amount', 'Collected By'];
        const body = rows.map((p) => [
            p.payment_date, p.receipt_number || '', p.student_name, p.admission_number || '', p.class || '', p.section || '',
            p.fee_name || '', modeLabel(p), p.transaction_id || p.cheque_number || '', Number(p.amount_paid), p.collected_by_name || '',
        ]);
        const summary = [
            ['Fee Collection Report'],
            ['From', range.from, 'To', range.to, 'Class', className || 'All classes'],
            ['Total collected', Number(report?.total_collected || 0), 'Payments', rows.length],
            ...modes.map(([mode, amount]) => [mode, amount]),
            [],
        ];
        const sheet = XLSX.utils.aoa_to_sheet([...summary, header, ...body]);
        sheet['!cols'] = [12, 16, 24, 14, 12, 8, 20, 10, 16, 12, 20].map((wch) => ({ wch }));
        const book = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(book, sheet, 'Collection');
        XLSX.writeFile(book, `Fee_Collection_${range.from}_to_${range.to}${className ? `_${className.replace(/\s+/g, '_')}` : ''}.xlsx`);
    };

    const columns = [
        { key: 'payment_date', label: 'Date', render: (v: string) => <span className="whitespace-nowrap">{formatDate(v)}</span> },
        { key: 'receipt_number', label: 'Receipt No', render: (v: string) => <span className="whitespace-nowrap">{v || '-'}</span> },
        {
            key: 'student_name',
            label: 'Student',
            render: (_: unknown, p: ICollectionPayment) => (
                <div>
                    <p className="font-medium text-gray-900 dark:text-white">{p.student_name}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                        {[p.class, p.section && `Section ${p.section}`, p.admission_number].filter(Boolean).join(' · ') || '-'}
                    </p>
                </div>
            ),
        },
        { key: 'fee_name', label: 'Fee', render: (v: string) => <span>{v || '-'}</span> },
        {
            key: 'payment_mode',
            label: 'Mode',
            render: (_: unknown, p: ICollectionPayment) => (
                <div>
                    <p className="text-sm">{modeLabel(p)}</p>
                    {(p.transaction_id || p.cheque_number) && (
                        <p className="text-xs text-gray-500 dark:text-gray-400">{p.transaction_id || p.cheque_number}</p>
                    )}
                </div>
            ),
        },
        {
            key: 'amount_paid',
            label: 'Amount',
            className: 'text-right',
            render: (v: number) => <span className="font-semibold text-gray-900 dark:text-white">{money(v)}</span>,
        },
        { key: 'collected_by_name', label: 'Collected By', render: (v: string) => <span>{v || '-'}</span> },
    ];

    return (
        <div className="space-y-6">
            <PageHeader
                title="Collection Report"
                subtitle="Fee payments received in a period (cancelled payments are not counted)"
                breadcrumbs={[{ label: 'Dashboard', href: '/dashboard' }, { label: 'Collection Report', href: '#' }]}
            />

            <div className="space-y-4 rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
                <div className="flex flex-wrap gap-2" data-testid="collection-presets">
                    {PRESETS.map((p) => (
                        <button
                            key={p.key}
                            type="button"
                            onClick={() => setRange(p.range())}
                            className={`rounded-full border px-3 py-1 text-sm ${activePreset === p.key
                                ? 'border-blue-600 bg-blue-600 text-white'
                                : 'border-gray-300 text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700'}`}
                        >
                            {p.label}
                        </button>
                    ))}
                </div>
                <div className="grid grid-cols-1 items-end gap-4 sm:grid-cols-2 md:grid-cols-4">
                    <FormInput label="From" type="date" name="from" value={range.from} max={range.to}
                        onChange={(e) => e.target.value && setRange((r) => ({ ...r, from: e.target.value }))} />
                    <FormInput label="To" type="date" name="to" value={range.to} min={range.from}
                        onChange={(e) => e.target.value && setRange((r) => ({ ...r, to: e.target.value }))} />
                    <FormSelect
                        label="Class"
                        name="class"
                        value={classId}
                        onChange={(e) => setClassId(e.target.value)}
                        options={[{ label: 'All classes', value: '' }, ...classes]}
                    />
                    <div className="flex gap-2 md:justify-end">
                        <Button variant="secondary" onClick={load} isLoading={loading} loadingText="Loading...">Refresh</Button>
                        <Button variant="primary" onClick={exportExcel} disabled={rows.length === 0}>Export to Excel</Button>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3" data-testid="collection-totals">
                <StatCard title="Total Collected" value={money(report?.total_collected || 0)} icon="💰" />
                <StatCard title="Payments" value={report?.total_transactions || 0} icon="🧾" />
                <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
                    <p className="mb-2 text-sm text-gray-500 dark:text-gray-400">By payment mode</p>
                    {modes.length === 0 ? (
                        <p className="text-sm text-gray-400">-</p>
                    ) : (
                        <ul className="space-y-1" data-testid="collection-modes">
                            {modes.map(([mode, amount]) => (
                                <li key={mode} className="flex justify-between text-sm text-gray-700 dark:text-gray-200">
                                    <span>{mode}</span>
                                    <span className="font-medium">{money(amount)}</span>
                                </li>
                            ))}
                        </ul>
                    )}
                </div>
            </div>

            <DataTable
                columns={columns}
                data={rows}
                loading={loading}
                striped
                emptyMessage={`No payments between ${formatDate(range.from)} and ${formatDate(range.to)}`}
            />
        </div>
    );
};

export default CollectionReport;
