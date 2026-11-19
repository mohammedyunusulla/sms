import { FC, useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { PageHeader, Skeleton } from '../../components';
import { financeService } from '../../services/modules/financeService';
import { useAuthStore } from '../../stores/authStore';
import { useParentStore } from '../../stores/parentStore';

type FeeStatus = 'PAID' | 'PARTIAL' | 'PENDING' | 'OVERDUE' | 'CANCELLED';

interface FeeStructure {
    fee_name?: string;
    description?: string;
    is_recurring?: boolean;
    recurrence_type?: string;
    recurrence_amount?: number;
    recurrence_months?: number;
}

interface Payment {
    id: number;
    payment_mode?: string;
    payment_date?: string;
    receipt_number?: string;
    amount_paid?: number;
    is_cancelled?: boolean;
}

interface Fee {
    id: number;
    status: FeeStatus;
    total_amount?: number;
    paid_amount?: number;
    discount_amount?: number;
    balance_amount?: number;
    has_installments?: boolean;
    fee_structure?: FeeStructure;
    payments?: Payment[];
}

interface Installment {
    id: number;
    installment_number?: number;
    installment_name?: string;
    due_date?: string;
    amount?: number;
    paid_amount?: number;
    balance_amount?: number;
    status: FeeStatus;
}

interface FeeSummary {
    total_amount: number;
    total_paid: number;
    total_discount: number;
    balance: number;
    fees: Fee[];
}

const STATUS_BADGE: Record<FeeStatus, { label: string; classes: string }> = {
    PAID: { label: 'Paid', classes: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400' },
    PARTIAL: { label: 'Partial', classes: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400' },
    PENDING: { label: 'Pending', classes: 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400' },
    OVERDUE: { label: 'Overdue', classes: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400' },
    CANCELLED: { label: 'Cancelled', classes: 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400' },
};

function formatCurrency(amount?: number): string {
    if (amount == null) return '₹0';
    return `₹${Number(amount).toLocaleString('en-IN')}`;
}

function formatDate(dateStr?: string): string {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return `${months[date.getMonth()]} ${date.getDate()}, ${date.getFullYear()}`;
}

function StatusBadge({ status }: { status: FeeStatus }) {
    const config = STATUS_BADGE[status] || STATUS_BADGE.PENDING;
    return (
        <span
            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.classes}`}
        >
            {config.label}
        </span>
    );
}

const ParentFees: FC = () => {
    const academicYear = useAuthStore((s) => s.user?.current_academic_year);
    const academicYearVersion = useAuthStore((s) => s.academicYearVersion);
    const selectedChild = useParentStore((s) => s.selectedChild);
    const childrenLoaded = useParentStore((s) => s.loaded);
    const childrenLoading = useParentStore((s) => s.loading);

    const [summary, setSummary] = useState<FeeSummary | null>(null);
    const [loading, setLoading] = useState(false);

    const studentId = selectedChild?.student_id;
    const academicYearId = academicYear?.id;

    const fetchFees = useCallback(async () => {
        if (!studentId || !academicYearId) {
            setSummary(null);
            return;
        }
        setLoading(true);
        try {
            const res: any = await financeService.getStudentFeeSummary(studentId, academicYearId);
            // axios interceptor unwraps once; backend may still wrap as { data: {...} }
            const data = res?.data || res || {};
            setSummary({
                total_amount: data.total_amount || 0,
                total_paid: data.total_paid || 0,
                total_discount: data.total_discount || 0,
                balance: data.balance || 0,
                fees: Array.isArray(data.fees) ? data.fees : [],
            });
        } catch (err: any) {
            toast.error(err?.message || 'Failed to load fees');
            setSummary(null);
        } finally {
            setLoading(false);
        }
    }, [studentId, academicYearId]);

    useEffect(() => {
        fetchFees();
    }, [fetchFees, academicYearVersion]);

    const childName = selectedChild?.full_name || selectedChild?.first_name || '';

    return (
        <div className="space-y-6">
            <PageHeader
                title="My Child's Fees"
                subtitle={
                    selectedChild
                        ? `${childName}'s fee summary${academicYear?.year_name ? ` — ${academicYear.year_name}` : ''}`
                        : 'Pick a child from the header dropdown to view their fees'
                }
                breadcrumbs={[
                    { label: 'Dashboard', href: '/dashboard' },
                    { label: "My Child's Fees", href: '#' },
                ]}
            />

            {!selectedChild ? (
                <div className="bg-white dark:bg-gray-800 p-8 rounded-lg border border-gray-200 dark:border-gray-700 text-center">
                    <p className="text-gray-500 dark:text-gray-400">
                        {childrenLoading
                            ? 'Loading your children…'
                            : childrenLoaded
                            ? 'No children linked to your account yet.'
                            : 'Select a child from the dropdown in the header to begin.'}
                    </p>
                </div>
            ) : loading ? (
                <>
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                        {Array.from({ length: 4 }).map((_, i) => (
                            <div key={i} className="bg-gray-50 dark:bg-gray-800 rounded-xl p-4 border border-gray-100 dark:border-gray-700">
                                <Skeleton className="h-3 w-16 mb-2" />
                                <Skeleton className="h-6 w-24" />
                            </div>
                        ))}
                    </div>
                    <div>
                        <Skeleton className="h-5 w-36 mb-3" />
                        <div className="space-y-3">
                            {Array.from({ length: 3 }).map((_, i) => (
                                <div key={i} className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
                                    <div className="flex items-start justify-between gap-3 mb-3">
                                        <Skeleton className="h-4 w-32" />
                                        <Skeleton className="h-5 w-16 rounded-full" />
                                    </div>
                                    <div className="grid grid-cols-4 gap-2">
                                        {Array.from({ length: 4 }).map((_, j) => (
                                            <div key={j}>
                                                <Skeleton className="h-2.5 w-10 mb-1" />
                                                <Skeleton className="h-4 w-14" />
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </>
            ) : !summary ? (
                <div className="bg-white dark:bg-gray-800 p-8 rounded-lg border border-gray-200 dark:border-gray-700 text-center">
                    <p className="text-base font-semibold text-gray-700 dark:text-gray-200">No fee data available</p>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                        Fees have not been assigned yet for this academic year.
                    </p>
                </div>
            ) : (
                <>
                    {/* Summary cards */}
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                        <SummaryCard label="Total" value={formatCurrency(summary.total_amount)} tone="indigo" />
                        <SummaryCard label="Paid" value={formatCurrency(summary.total_paid)} tone="green" />
                        <SummaryCard label="Discount" value={formatCurrency(summary.total_discount)} tone="blue" />
                        <SummaryCard label="Balance" value={formatCurrency(summary.balance)} tone="red" />
                    </div>

                    {/* Fee Breakdown */}
                    <div>
                        <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-3">
                            Fee Breakdown
                        </h3>

                        {summary.fees.length === 0 ? (
                            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700 text-center">
                                <p className="text-sm text-gray-500 dark:text-gray-400">No fees assigned.</p>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                {summary.fees.map((fee) => (
                                    <FeeCard key={fee.id} fee={fee} />
                                ))}
                            </div>
                        )}
                    </div>
                </>
            )}
        </div>
    );
};

function SummaryCard({
    label,
    value,
    tone,
}: {
    label: string;
    value: string;
    tone: 'indigo' | 'green' | 'blue' | 'red';
}) {
    const toneStyles = {
        indigo: { bg: 'bg-indigo-50 dark:bg-indigo-900/20', label: 'text-indigo-700 dark:text-indigo-300', value: 'text-indigo-700 dark:text-indigo-200' },
        green: { bg: 'bg-green-50 dark:bg-green-900/20', label: 'text-green-700 dark:text-green-300', value: 'text-green-700 dark:text-green-200' },
        blue: { bg: 'bg-blue-50 dark:bg-blue-900/20', label: 'text-brand-700 dark:text-blue-300', value: 'text-brand-700 dark:text-blue-200' },
        red: { bg: 'bg-red-50 dark:bg-red-900/20', label: 'text-red-700 dark:text-red-300', value: 'text-red-700 dark:text-red-200' },
    } as const;
    const c = toneStyles[tone];
    return (
        <div className={`${c.bg} rounded-xl p-4`}>
            <p className={`text-[11px] font-semibold uppercase tracking-wider ${c.label}`}>{label}</p>
            <p className={`text-xl font-bold mt-1 ${c.value}`}>{value}</p>
        </div>
    );
}

function FeeCard({ fee }: { fee: Fee }) {
    const [expanded, setExpanded] = useState(false);
    const [installments, setInstallments] = useState<Installment[]>([]);
    const [installmentsLoading, setInstallmentsLoading] = useState(false);
    const [installmentsLoaded, setInstallmentsLoaded] = useState(false);

    const feeName = fee.fee_structure?.fee_name || 'Fee';
    const description = fee.fee_structure?.description || '';
    const isRecurring = fee.fee_structure?.is_recurring;
    const recurrenceType = fee.fee_structure?.recurrence_type;
    const recurrenceAmount = fee.fee_structure?.recurrence_amount;
    const recurrenceMonths = fee.fee_structure?.recurrence_months;
    const hasInstallments = !!fee.has_installments;
    const validPayments = (fee.payments || []).filter((p) => !p.is_cancelled);

    const handleToggle = async () => {
        if (!expanded && hasInstallments && !installmentsLoaded) {
            setInstallmentsLoading(true);
            try {
                const res: any = await financeService.getInstallments(fee.id);
                const data = Array.isArray(res) ? res : res?.data || [];
                setInstallments(Array.isArray(data) ? data : []);
                setInstallmentsLoaded(true);
            } catch (err: any) {
                toast.error(err?.message || 'Failed to load installments');
            } finally {
                setInstallmentsLoading(false);
            }
        }
        setExpanded(!expanded);
    };

    const canExpand = hasInstallments || validPayments.length > 0;

    return (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
            <button
                onClick={canExpand ? handleToggle : undefined}
                className={`w-full text-left p-4 ${canExpand ? 'cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/30' : 'cursor-default'}`}
            >
                {/* Top row */}
                <div className="flex items-start justify-between gap-3 mb-2">
                    <div className="min-w-0">
                        <p className="text-sm font-semibold text-gray-900 dark:text-white">{feeName}</p>
                        {description && (
                            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 truncate">
                                {description}
                            </p>
                        )}
                    </div>
                    <StatusBadge status={fee.status} />
                </div>

                {/* Tags */}
                <div className="flex flex-wrap gap-1.5 mb-3">
                    {isRecurring && (
                        <span className="bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-300 rounded-full px-2 py-0.5 text-[10px] font-medium">
                            {recurrenceType || 'Recurring'}
                        </span>
                    )}
                    {isRecurring && recurrenceAmount != null && recurrenceMonths != null && (
                        <span className="bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-full px-2 py-0.5 text-[10px] font-medium">
                            {formatCurrency(recurrenceAmount)} × {recurrenceMonths} months
                        </span>
                    )}
                    {hasInstallments && (
                        <span className="bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-300 rounded-full px-2 py-0.5 text-[10px] font-medium">
                            Installment Mode
                        </span>
                    )}
                </div>

                {/* Amounts grid */}
                <div className="grid grid-cols-4 gap-2">
                    <AmountBlock label="Total" value={formatCurrency(fee.total_amount)} />
                    <AmountBlock label="Paid" value={formatCurrency(fee.paid_amount)} tone="text-green-600 dark:text-green-400" />
                    <AmountBlock label="Discount" value={formatCurrency(fee.discount_amount)} tone="text-brand-600 dark:text-blue-400" />
                    <AmountBlock label="Balance" value={formatCurrency(fee.balance_amount)} tone="text-red-600 dark:text-red-400" />
                </div>

                {/* Expand indicator */}
                {canExpand && (
                    <p className="text-center text-xs text-indigo-600 dark:text-indigo-400 mt-3 font-medium">
                        {expanded
                            ? `Hide ${hasInstallments ? 'installments' : 'payments'} ▲`
                            : hasInstallments
                            ? 'View installments ▼'
                            : `View payments (${validPayments.length}) ▼`}
                    </p>
                )}
            </button>

            {expanded && (
                <div className="px-4 pb-4 border-t border-gray-100 dark:border-gray-700 pt-3">
                    {hasInstallments ? (
                        installmentsLoading ? (
                            <p className="text-xs text-gray-400 dark:text-gray-500 italic text-center py-2">
                                Loading installments…
                            </p>
                        ) : installments.length === 0 ? (
                            <p className="text-xs text-gray-400 dark:text-gray-500 italic text-center py-2">
                                No installments found.
                            </p>
                        ) : (
                            installments.map((inst) => <InstallmentRow key={inst.id} installment={inst} />)
                        )
                    ) : validPayments.length > 0 ? (
                        validPayments.map((payment) => <PaymentRow key={payment.id} payment={payment} />)
                    ) : (
                        <p className="text-xs text-gray-400 dark:text-gray-500 italic text-center py-2">
                            No payment history.
                        </p>
                    )}
                </div>
            )}
        </div>
    );
}

function AmountBlock({ label, value, tone = 'text-gray-700 dark:text-gray-200' }: { label: string; value: string; tone?: string }) {
    return (
        <div>
            <p className="text-[9px] font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-0.5">
                {label}
            </p>
            <p className={`text-sm font-bold ${tone}`}>{value}</p>
        </div>
    );
}

function InstallmentRow({ installment }: { installment: Installment }) {
    const isOverdue =
        installment.status !== 'PAID' &&
        installment.due_date &&
        new Date(installment.due_date) < new Date();
    const isPaid = installment.status === 'PAID';

    const numberCircle = isPaid
        ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
        : isOverdue
        ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
        : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300';

    return (
        <div className="flex items-center py-2.5 border-b border-gray-100 dark:border-gray-700 last:border-b-0">
            <div className={`w-7 h-7 rounded-full flex items-center justify-center mr-3 text-xs font-bold ${numberCircle}`}>
                {installment.installment_number}
            </div>
            <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-800 dark:text-gray-200">
                    {installment.installment_name || `Installment ${installment.installment_number}`}
                </p>
                <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[11px] text-gray-500 dark:text-gray-400">
                        Due: {formatDate(installment.due_date)}
                    </span>
                    {isOverdue && (
                        <span className="bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-full px-1.5 py-0.5 text-[9px] font-bold">
                            OVERDUE
                        </span>
                    )}
                </div>
            </div>
            <div className="text-right">
                <p className="text-sm font-bold text-gray-800 dark:text-gray-200">
                    {formatCurrency(installment.amount)}
                </p>
                {installment.paid_amount != null && installment.paid_amount > 0 && (
                    <p className="text-[10px] text-green-600 dark:text-green-400">
                        Paid: {formatCurrency(installment.paid_amount)}
                    </p>
                )}
                {installment.balance_amount != null && installment.balance_amount > 0 && (
                    <p className="text-[10px] text-red-500 dark:text-red-400">
                        Due: {formatCurrency(installment.balance_amount)}
                    </p>
                )}
                {isPaid && (
                    <p className="text-[10px] font-bold text-green-600 dark:text-green-400 mt-0.5">✓ Paid</p>
                )}
            </div>
        </div>
    );
}

function PaymentRow({ payment }: { payment: Payment }) {
    return (
        <div className="flex items-center py-2.5 border-b border-gray-100 dark:border-gray-700 last:border-b-0">
            <div className="w-7 h-7 rounded-full bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 flex items-center justify-center mr-3 text-xs font-bold">
                ✓
            </div>
            <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-800 dark:text-gray-200">
                    {payment.payment_mode}
                </p>
                <p className="text-[11px] text-gray-500 dark:text-gray-400">
                    {formatDate(payment.payment_date)}
                    {payment.receipt_number ? ` · ${payment.receipt_number}` : ''}
                </p>
            </div>
            <p className="text-sm font-bold text-green-600 dark:text-green-400">
                {formatCurrency(payment.amount_paid)}
            </p>
        </div>
    );
}

export default ParentFees;
