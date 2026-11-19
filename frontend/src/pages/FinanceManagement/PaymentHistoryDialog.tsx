/**
 * Payment History Dialog
 * Lists a fee's payments; a payment entered by mistake can be cancelled with a reason.
 * Cancelling reverses it on the fee (and on its installment, if it paid one).
 */

import { FC, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { Modal, Button, Badge, FormTextarea } from '../../components';
import { financeService } from '../../services/modules/financeService';
import { IStudentFee, IInstallment, IFeePayment } from '../../types/index';

interface PaymentHistoryDialogProps {
    isOpen: boolean;
    onClose: () => void;
    fee: IStudentFee | null;
    installments: IInstallment[];
    /** Cancelling is admin-only on the server; others just see the history. */
    canCancel?: boolean;
    onCancelled: () => void;
}

const money = (v: number | string | undefined) => `₹${parseFloat(String(v || 0)).toLocaleString('en-IN')}`;

const formatDate = (d?: string) =>
    d ? new Date(d).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '-';

const PaymentHistoryDialog: FC<PaymentHistoryDialogProps> = ({ isOpen, onClose, fee, installments, canCancel = true, onCancelled }) => {
    const [cancelling, setCancelling] = useState<IFeePayment | null>(null);
    const [reason, setReason] = useState('');
    const [reasonError, setReasonError] = useState('');
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (!isOpen) {
            setCancelling(null);
            setReason('');
            setReasonError('');
        }
    }, [isOpen]);

    const payments = [...(fee?.payments || [])].sort((a, b) => (a.payment_date < b.payment_date ? 1 : -1));
    const installmentName = (id?: number | null) => installments.find((i) => i.id === id)?.installment_name;

    const confirmCancel = async () => {
        if (!cancelling) return;
        if (!reason.trim()) {
            setReasonError('Give a reason for cancelling the payment');
            return;
        }
        try {
            setSaving(true);
            await financeService.cancelPayment(cancelling.id, reason.trim());
            toast.success(`Payment ${cancelling.receipt_number} cancelled`);
            setCancelling(null);
            setReason('');
            onCancelled();
        } catch (error) {
            toast.error((error as Error).message || 'Failed to cancel the payment');
        } finally {
            setSaving(false);
        }
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={`Payments - ${fee?.fee_structure?.fee_name || fee?.fee_name || 'Fee'}`}
            size="lg"
            footer={
                <div className="flex justify-end gap-3">
                    {cancelling ? (
                        <>
                            <Button variant="secondary" onClick={() => { setCancelling(null); setReasonError(''); }} disabled={saving}>
                                Keep Payment
                            </Button>
                            <Button variant="danger" onClick={confirmCancel} isLoading={saving} loadingText="Cancelling...">
                                Cancel Payment
                            </Button>
                        </>
                    ) : (
                        <Button variant="secondary" onClick={onClose}>Close</Button>
                    )}
                </div>
            }
        >
            {cancelling ? (
                <div className="space-y-4">
                    <div className="rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20">
                        <p className="font-semibold text-gray-900 dark:text-white">
                            Cancel receipt {cancelling.receipt_number} ({money(cancelling.amount_paid)})?
                        </p>
                        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                            The amount is taken off what this student has paid
                            {cancelling.installment_id ? ` and off ${installmentName(cancelling.installment_id) || 'its installment'}` : ''}.
                            The receipt stays on record as cancelled.
                        </p>
                    </div>
                    <FormTextarea
                        label="Reason"
                        required
                        rows={3}
                        value={reason}
                        onChange={(e) => { setReason(e.target.value); setReasonError(''); }}
                        placeholder="e.g. Amount entered twice"
                        error={reasonError}
                    />
                </div>
            ) : payments.length === 0 ? (
                <p className="py-6 text-center text-sm text-gray-500 dark:text-gray-400">No payments recorded for this fee.</p>
            ) : (
                <div className="space-y-2" data-testid="payment-history">
                    {payments.map((p) => (
                        <div
                            key={p.id}
                            className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-gray-200 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-700/50"
                        >
                            <div className="min-w-0">
                                <p className="font-medium text-gray-900 dark:text-white">
                                    {money(p.amount_paid)}{' '}
                                    <span className="text-sm font-normal text-gray-500 dark:text-gray-400">
                                        on {formatDate(p.payment_date)}
                                    </span>
                                </p>
                                <p className="text-xs text-gray-500 dark:text-gray-400">
                                    Receipt {p.receipt_number}
                                    {p.payment_mode ? ` · ${p.payment_mode.replace('_', ' ')}` : ''}
                                    {p.installment_id && installmentName(p.installment_id) ? ` · ${installmentName(p.installment_id)}` : ''}
                                    {p.remarks ? ` · ${p.remarks}` : ''}
                                </p>
                            </div>
                            <div className="flex items-center gap-2">
                                <Badge variant="success" size="sm">Paid</Badge>
                                {canCancel && <Button variant="danger" size="sm" onClick={() => setCancelling(p)}>Cancel</Button>}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </Modal>
    );
};

export default PaymentHistoryDialog;
