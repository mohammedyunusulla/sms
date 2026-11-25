/**
 * Salary Payments Page
 * Generate monthly salary payments and manage paid/unpaid status.
 */

import { FC, useEffect, useState, useMemo } from 'react';
import toast from 'react-hot-toast';
import { PageHeader, DataTable, Badge, Button, StatCard, Modal, ConfirmDialog, FormInput, FormSelect } from '../../components';
import { financeService } from '../../services/modules/financeService';
import { useAuthStore } from '../../stores/authStore';
import { ISalaryPayment, ISalaryPaymentForm } from '../../types/index';
import { formatAmount } from '../../utils/money';
import { staffAttendanceService } from '../../services/modules/staffAttendanceService';

const MONTHS = [
    { label: 'January', value: '1' }, { label: 'February', value: '2' },
    { label: 'March', value: '3' }, { label: 'April', value: '4' },
    { label: 'May', value: '5' }, { label: 'June', value: '6' },
    { label: 'July', value: '7' }, { label: 'August', value: '8' },
    { label: 'September', value: '9' }, { label: 'October', value: '10' },
    { label: 'November', value: '11' }, { label: 'December', value: '12' },
];

const PAYMENT_METHODS = [
    { label: 'Cash', value: 'cash' },
    { label: 'Bank Transfer', value: 'bank_transfer' },
    { label: 'Cheque', value: 'cheque' },
    { label: 'Online', value: 'online' },
];

const SalaryPayments: FC = () => {
    const { user, academicYearVersion } = useAuthStore();
    const academicYearId = user?.current_academic_year?.id;

    const [payments, setPayments] = useState<ISalaryPayment[]>([]);
    const [loading, setLoading] = useState(false);
    const [generating, setGenerating] = useState(false);

    const [genMonth, setGenMonth] = useState(String(new Date().getMonth() + 1));
    const [genYear, setGenYear] = useState(String(new Date().getFullYear()));

    const [showPayDialog, setShowPayDialog] = useState(false);
    const [showUnpaidDialog, setShowUnpaidDialog] = useState(false);
    const [selectedPayment, setSelectedPayment] = useState<ISalaryPayment | null>(null);
    const [paymentForm, setPaymentForm] = useState<ISalaryPaymentForm>({
        payment_date: new Date().toISOString().split('T')[0],
        payment_method: '',
        transaction_reference: '',
    });
    const [saving, setSaving] = useState(false);
    // loss of pay: apply (true) / remove (false) on a pending payment
    const [lop, setLop] = useState<{ payment: ISalaryPayment; apply: boolean } | null>(null);

    useEffect(() => {
        if (academicYearId) fetchPayments();
    }, [academicYearId, academicYearVersion]);

    const fetchPayments = async () => {
        try {
            setLoading(true);
            const data = await financeService.listSalaryPayments(academicYearId!);
            setPayments(Array.isArray(data) ? data : (data as any).salary_payments || []);
        } catch (error: any) {
            console.error('Error fetching salary payments:', error);
            toast.error(error.message || 'Failed to fetch salary payments');
        } finally {
            setLoading(false);
        }
    };

    const handleGenerate = async () => {
        try {
            setGenerating(true);
            const data = await financeService.generateSalaryPayments({
                month: parseInt(genMonth),
                year: parseInt(genYear),
                academic_year_id: academicYearId!,
            });
            const generated = data.salary_payments || [];
            if (generated.length > 0) {
                toast.success(`Generated ${generated.length} salary payment(s) successfully`);
            } else {
                toast.error('No new salary payments generated. They may already exist for this period.');
            }
            fetchPayments();
        } catch (error: any) {
            console.error('Error generating salaries:', error);
            toast.error(error.message || 'Failed to generate salaries');
        } finally {
            setGenerating(false);
        }
    };

    const handleMarkPaidClick = (record: ISalaryPayment) => {
        setSelectedPayment(record);
        setPaymentForm({
            payment_date: new Date().toISOString().split('T')[0],
            payment_method: '',
            transaction_reference: '',
        });
        setShowPayDialog(true);
    };

    const handleMarkPaid = async () => {
        if (!selectedPayment || !paymentForm.payment_method) {
            toast.error('Please select a payment method');
            return;
        }
        try {
            setSaving(true);
            await financeService.markSalaryPaid(selectedPayment.id, {
                ...paymentForm,
                paid_by: user?.institution_user_id,
            });
            toast.success('Salary marked as paid');
            setShowPayDialog(false);
            setSelectedPayment(null);
            fetchPayments();
        } catch (error: any) {
            console.error('Error marking salary as paid:', error);
            toast.error(error.message || 'Failed to mark salary as paid');
        } finally {
            setSaving(false);
        }
    };

    const handleMarkUnpaidClick = (record: ISalaryPayment) => {
        setSelectedPayment(record);
        setShowUnpaidDialog(true);
    };

    const confirmMarkUnpaid = async () => {
        if (!selectedPayment) return;
        try {
            setSaving(true);
            await financeService.markSalaryUnpaid(selectedPayment.id);
            toast.success('Salary marked as unpaid');
            setShowUnpaidDialog(false);
            setSelectedPayment(null);
            fetchPayments();
        } catch (error: any) {
            console.error('Error marking salary as unpaid:', error);
            toast.error(error.message || 'Failed to mark salary as unpaid');
        } finally {
            setSaving(false);
        }
    };

    const confirmLossOfPay = async () => {
        if (!lop) return;
        try {
            setSaving(true);
            await staffAttendanceService.lossOfPay(lop.payment.id, lop.apply);
            toast.success(lop.apply ? 'Loss of pay applied' : 'Loss of pay removed');
            setLop(null);
            fetchPayments();
        } catch (error) {
            toast.error((error as { message?: string })?.message || 'Could not update loss of pay');
        } finally {
            setSaving(false);
        }
    };

    const totals = useMemo(() => {
        const result = { paid: 0, pending: 0, total: 0 };
        payments.forEach(p => {
            const amount = parseFloat(String(p.net_amount_paid));
            result.total += amount;
            if (p.status === 'paid') result.paid += amount;
            else if (p.status === 'pending') result.pending += amount;
        });
        return result;
    }, [payments]);

    const columns = [
        {
            key: 'staff_name',
            label: 'Staff Name',
            render: (value: string) => <span className="font-medium">{value}</span>,
        },
        {
            key: 'payment_month',
            label: 'Month/Year',
            render: (_: any, row: ISalaryPayment) => (
                <span className="text-sm">{row.payment_month}/{row.payment_year}</span>
            ),
        },
        {
            key: 'attendance',
            label: 'Attendance',
            render: (_: unknown, row: ISalaryPayment) => {
                const a = row.attendance;
                if (!a) return <span className="text-xs text-gray-400">-</span>;
                const part = (n: number | undefined, label: string, cls: string) =>
                    n ? <span className={cls}>{label} {n}</span> : null;
                return (
                    <div className="flex flex-wrap gap-x-2 text-xs" title="Present · Absent · Half day · Leave · Unpaid leave · Late · Not marked">
                        <span className="text-emerald-700 dark:text-emerald-400">P {a.PRESENT || 0}</span>
                        {part(a.ABSENT, 'A', 'text-red-600 dark:text-red-400')}
                        {part(a.HALF_DAY, 'H', 'text-orange-600 dark:text-orange-400')}
                        {part(a.LEAVE, 'LV', 'text-blue-600 dark:text-blue-400')}
                        {part(a.UNPAID_LEAVE, 'UL', 'text-purple-600 dark:text-purple-400')}
                        {part(a.LATE, 'L', 'text-amber-600 dark:text-amber-400')}
                        {part(a.NOT_MARKED, 'NM', 'text-gray-500')}
                    </div>
                );
            },
        },
        {
            key: 'basic_salary',
            label: 'Basic',
            className: 'text-right',
            render: (value: number) => <span>{'\u20B9'}{formatAmount(value)}</span>,
        },
        {
            key: 'allowances_paid',
            label: 'Allowances',
            className: 'text-right',
            render: (value: any) => {
                const total = Object.values(value || {}).reduce((sum: number, val: any) => sum + (parseFloat(val) || 0), 0);
                return <span>{'\u20B9'}{formatAmount(total)}</span>;
            },
        },
        {
            key: 'deductions_applied',
            label: 'Deductions',
            className: 'text-right',
            render: (value: Record<string, number | string> | null, row: ISalaryPayment) => {
                const total = Object.values(value || {}).reduce((sum: number, val) => sum + (parseFloat(String(val)) || 0), 0);
                return (
                    <div>
                        <span className="text-red-600 dark:text-red-400">-{'\u20B9'}{formatAmount(total)}</span>
                        {row.loss_of_pay_applied != null && (
                            <p className="text-[11px] text-gray-500 dark:text-gray-400">incl. loss of pay {'\u20B9'}{formatAmount(row.loss_of_pay_applied)}</p>
                        )}
                    </div>
                );
            },
        },
        {
            key: 'net_amount_paid',
            label: 'Net Salary',
            className: 'text-right',
            render: (value: number) => (
                <span className="font-bold text-green-600 dark:text-green-400">
                    {'\u20B9'}{formatAmount(value)}
                </span>
            ),
        },
        {
            key: 'payment_date',
            label: 'Payment Date',
            render: (value: string) => (
                <span className="text-sm">{value ? new Date(value).toLocaleDateString('en-IN') : 'Not Paid'}</span>
            ),
        },
        {
            key: 'status',
            label: 'Status',
            render: (value: string) => {
                const variant = value === 'paid' ? 'success' : value === 'pending' ? 'warning' : 'danger';
                return <Badge variant={variant} size="sm">{value?.toUpperCase()}</Badge>;
            },
        },
    ];

    const breadcrumbs = [
        { label: 'Dashboard', href: '/dashboard' },
        { label: 'Salary Payments', href: '#' },
    ];

    return (
        <div className="space-y-6">
            <PageHeader
                title="Salary Payment Management"
                subtitle="Generate and manage monthly salary payments"
                breadcrumbs={breadcrumbs}
            />

            {/* Generation Section */}
            <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Generate Monthly Salaries</h3>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-end">
                    <FormSelect
                        label="Month"
                        value={genMonth}
                        onChange={(e) => setGenMonth(e.target.value)}
                        options={MONTHS}
                    />
                    <FormInput
                        label="Year"
                        type="number"
                        min="2000"
                        max="2100"
                        value={genYear}
                        onChange={(e) => setGenYear(e.target.value)}
                    />
                    <Button
                        variant="primary"
                        onClick={handleGenerate}
                        isLoading={generating}
                        loadingText="Generating..."
                    >
                        Generate Salaries
                    </Button>
                </div>
                <div className="mt-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
                    <p className="text-sm text-blue-700 dark:text-blue-300">
                        This will generate salary payment records for all staff with active salary setups for the selected month/year.
                        Each payment shows that month's staff attendance; for absences and half days you can apply a loss of pay before paying.
                    </p>
                </div>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <StatCard title="Paid Salaries" value={`\u20B9${formatAmount(totals.paid)}`} icon="✅" />
                <StatCard title="Pending Salaries" value={`\u20B9${formatAmount(totals.pending)}`} icon="⏳" />
                <StatCard title="Total Amount" value={`\u20B9${formatAmount(totals.total)}`} icon="💰" />
            </div>

            {/* Payments Table */}
            <DataTable
                columns={columns}
                data={payments}
                loading={loading}
                emptyMessage="No salary payments found. Generate salaries for a month to get started."
                striped
                actions={(row: ISalaryPayment) => (
                    <div className="flex items-center gap-2">
                        {row.status === 'pending' && (
                            <Button variant="success" size="sm" onClick={() => handleMarkPaidClick(row)}>
                                Mark Paid
                            </Button>
                        )}
                        {row.status === 'pending' && row.loss_of_pay_applied == null && !!row.loss_of_pay_suggested && (
                            <Button variant="warning" size="sm" onClick={() => setLop({ payment: row, apply: true })}>
                                Loss of pay {'\u20B9'}{formatAmount(row.loss_of_pay_suggested)}
                            </Button>
                        )}
                        {row.status === 'pending' && row.loss_of_pay_applied != null && (
                            <Button variant="ghost" size="sm" onClick={() => setLop({ payment: row, apply: false })}>
                                Remove loss of pay
                            </Button>
                        )}
                        {row.status === 'paid' && (
                            <Button variant="danger" size="sm" onClick={() => handleMarkUnpaidClick(row)}>
                                Mark Unpaid
                            </Button>
                        )}
                    </div>
                )}
            />

            {/* Mark Paid Dialog */}
            <Modal
                isOpen={showPayDialog}
                onClose={() => setShowPayDialog(false)}
                title="Mark Salary as Paid"
                size="md"
                footer={
                    <div className="flex justify-end gap-3">
                        <Button variant="secondary" onClick={() => setShowPayDialog(false)}>Cancel</Button>
                        <Button
                            variant="success"
                            onClick={handleMarkPaid}
                            isLoading={saving}
                            loadingText="Processing..."
                            disabled={!paymentForm.payment_method}
                        >
                            Confirm Payment
                        </Button>
                    </div>
                }
            >
                {selectedPayment && (
                    <div className="space-y-4">
                        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                            <p className="font-semibold text-gray-900 dark:text-white">Staff: {selectedPayment.staff_name}</p>
                            <p className="text-sm text-gray-700 dark:text-gray-300">
                                Amount: {'\u20B9'}{formatAmount(selectedPayment.net_amount_paid)}
                            </p>
                            <p className="text-sm text-gray-700 dark:text-gray-300">
                                Period: {selectedPayment.payment_month}/{selectedPayment.payment_year}
                            </p>
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <FormInput
                                label="Payment Date"
                                type="date"
                                max={new Date().toLocaleDateString('en-CA')}
                                required
                                value={paymentForm.payment_date}
                                onChange={(e) => setPaymentForm({ ...paymentForm, payment_date: e.target.value })}
                            />
                            <FormSelect
                                label="Payment Method"
                                required
                                value={paymentForm.payment_method}
                                onChange={(e) => setPaymentForm({ ...paymentForm, payment_method: e.target.value })}
                                options={PAYMENT_METHODS}
                            />
                        </div>
                        <FormInput
                            label="Transaction Reference (optional)"
                            value={paymentForm.transaction_reference}
                            onChange={(e) => setPaymentForm({ ...paymentForm, transaction_reference: e.target.value })}
                            placeholder="Enter transaction ID, cheque number, or reference"
                            help="Enter transaction ID, cheque number, or reference"
                        />
                    </div>
                )}
            </Modal>

            {/* Loss of pay */}
            <ConfirmDialog
                isOpen={!!lop}
                title={lop?.apply ? 'Apply loss of pay' : 'Remove loss of pay'}
                message={lop ? (lop.apply
                    ? `${lop.payment.staff_name} has ${lop.payment.loss_of_pay_days} unpaid day(s) in ${lop.payment.payment_month}/${lop.payment.payment_year} (absent days, half of the half days, and approved leave beyond the yearly balance). Deduct \u20B9${formatAmount(lop.payment.loss_of_pay_suggested || 0)}? (basic \u20B9${formatAmount(lop.payment.basic_salary)} / ${lop.payment.attendance?.days ?? 'days in month'} days x ${lop.payment.loss_of_pay_days})`
                    : `Remove the \u20B9${formatAmount(lop.payment.loss_of_pay_applied || 0)} loss-of-pay deduction from ${lop.payment.staff_name}'s salary for ${lop.payment.payment_month}/${lop.payment.payment_year}?`) : ''}
                onConfirm={confirmLossOfPay}
                onCancel={() => setLop(null)}
                confirmText={lop?.apply ? 'Apply' : 'Remove'}
                type="warning"
                isLoading={saving}
            />

            {/* Mark Unpaid Confirmation */}
            <ConfirmDialog
                isOpen={showUnpaidDialog}
                title="Mark Salary as Unpaid"
                message={selectedPayment ? `Are you sure you want to mark ${selectedPayment.staff_name}'s salary for ${selectedPayment.payment_month}/${selectedPayment.payment_year} as unpaid?` : ''}
                onConfirm={confirmMarkUnpaid}
                onCancel={() => { setShowUnpaidDialog(false); setSelectedPayment(null); }}
                confirmText="Mark Unpaid"
                type="warning"
                isLoading={saving}
            />
        </div>
    );
};

export default SalaryPayments;
