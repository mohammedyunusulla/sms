/**
 * Apply Discount Dialog
 * Gives a student a discount on the fees chosen here (default: every fee that still has a balance).
 * Percentage: that share of each fee. Fixed: one amount spread over the chosen fees.
 * The server caps it at what is still owed and shrinks installment plans to match.
 */

import { FC, useEffect, useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import { Modal, Button, FormInput, FormSelect, FormTextarea } from '../../components';
import { financeService } from '../../services/modules/financeService';
import { IStudentFee } from '../../types/index';

interface DiscountDialogProps {
    isOpen: boolean;
    onClose: () => void;
    studentId: number | null;
    studentName?: string;
    academicYearId?: number | string;
    fees: IStudentFee[];
    onApplied: () => void;
}

const money = (v: number) => `₹${v.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;

const DiscountDialog: FC<DiscountDialogProps> = ({ isOpen, onClose, studentId, studentName, academicYearId, fees, onApplied }) => {
    const openFees = useMemo(() => fees.filter((f) => Number(f.balance_amount) > 0), [fees]);
    const [name, setName] = useState('');
    const [kind, setKind] = useState<'PERCENTAGE' | 'FIXED'>('PERCENTAGE');
    const [value, setValue] = useState('');
    const [chosen, setChosen] = useState<number[]>([]);
    const [reason, setReason] = useState('');
    const [errors, setErrors] = useState<Record<string, string>>({});
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (isOpen) {
            setName('');
            setKind('PERCENTAGE');
            setValue('');
            setReason('');
            setErrors({});
            setChosen(openFees.map((f) => f.id));
        }
    }, [isOpen, openFees]);

    const owed = openFees.filter((f) => chosen.includes(f.id)).reduce((s, f) => s + Number(f.balance_amount), 0);
    const amount = parseFloat(value) || 0;
    const estimate = kind === 'PERCENTAGE'
        ? openFees.filter((f) => chosen.includes(f.id)).reduce((s, f) => s + Math.min((Number(f.total_amount) * amount) / 100, Number(f.balance_amount)), 0)
        : Math.min(amount, owed);

    const toggle = (id: number) => setChosen((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));

    const submit = async () => {
        const next: Record<string, string> = {};
        if (!name.trim()) next.name = 'Give the discount a name';
        if (!(amount > 0)) next.value = 'Enter a value greater than 0';
        else if (kind === 'PERCENTAGE' && amount > 100) next.value = "A percentage can't be more than 100";
        else if (kind === 'FIXED' && amount > owed + 0.001) next.value = `Can't be more than what is still owed (${money(owed)})`;
        if (chosen.length === 0) next.fees = 'Choose at least one fee';
        setErrors(next);
        if (Object.keys(next).length || !studentId || !academicYearId) return;
        try {
            setSaving(true);
            const result = await financeService.applyDiscount({
                student_id: studentId,
                academic_year_id: academicYearId,
                discount_name: name.trim(),
                discount_type: kind,
                discount_value: amount,
                student_fee_ids: chosen,
                reason: reason.trim() || undefined,
            });
            const added = Number(result?.data?.total_discount_added ?? estimate);
            toast.success(`Discount of ${money(added)} applied`);
            onApplied();
            onClose();
        } catch (error) {
            toast.error((error as Error).message || 'Failed to apply the discount');
        } finally {
            setSaving(false);
        }
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={`Apply Discount${studentName ? ` - ${studentName}` : ''}`}
            size="md"
            footer={
                <div className="flex justify-end gap-3">
                    <Button variant="secondary" onClick={onClose} disabled={saving}>Close</Button>
                    <Button variant="primary" onClick={submit} isLoading={saving} loadingText="Applying...">Apply Discount</Button>
                </div>
            }
        >
            {openFees.length === 0 ? (
                <p className="py-6 text-center text-sm text-gray-500 dark:text-gray-400">Nothing is left to pay on this student's fees.</p>
            ) : (
                <div className="space-y-4">
                    <FormInput
                        label="Discount Name"
                        required
                        value={name}
                        onChange={(e) => { setName(e.target.value); setErrors((p) => ({ ...p, name: '' })); }}
                        placeholder="e.g. Sibling concession"
                        error={errors.name}
                    />
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                        <FormSelect
                            label="Type"
                            required
                            value={kind}
                            onChange={(e) => setKind(e.target.value as 'PERCENTAGE' | 'FIXED')}
                            options={[
                                { label: 'Percentage of each fee', value: 'PERCENTAGE' },
                                { label: 'Fixed amount', value: 'FIXED' },
                            ]}
                        />
                        <FormInput
                            label={kind === 'PERCENTAGE' ? 'Percentage (%)' : 'Amount (₹)'}
                            type="number"
                            required
                            min="0.01"
                            max={kind === 'PERCENTAGE' ? '100' : String(owed)}
                            step="0.01"
                            value={value}
                            onChange={(e) => { setValue(e.target.value); setErrors((p) => ({ ...p, value: '' })); }}
                            error={errors.value}
                        />
                    </div>

                    <div>
                        <p className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">Apply to <span className="text-red-500">*</span></p>
                        <div className="space-y-2">
                            {openFees.map((f) => (
                                <label key={f.id} className="flex cursor-pointer items-center justify-between gap-3 rounded-lg border border-gray-200 p-3 dark:border-gray-700">
                                    <span className="flex items-center gap-3">
                                        <input
                                            type="checkbox"
                                            className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                            checked={chosen.includes(f.id)}
                                            onChange={() => { toggle(f.id); setErrors((p) => ({ ...p, fees: '' })); }}
                                        />
                                        <span className="text-sm font-medium text-gray-900 dark:text-white">{f.fee_structure?.fee_name || f.fee_name || 'Fee'}</span>
                                    </span>
                                    <span className="text-xs text-gray-500 dark:text-gray-400">Balance {money(Number(f.balance_amount))}</span>
                                </label>
                            ))}
                        </div>
                        {errors.fees && <p role="alert" className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.fees}</p>}
                    </div>

                    <FormTextarea
                        label="Reason"
                        rows={2}
                        value={reason}
                        onChange={(e) => setReason(e.target.value)}
                        placeholder="Optional, e.g. approved by the principal"
                    />

                    {amount > 0 && chosen.length > 0 && (
                        <p className="rounded-lg bg-blue-50 p-3 text-sm text-blue-800 dark:bg-blue-900/20 dark:text-blue-300" data-testid="discount-estimate">
                            About {money(estimate)} off. What is still owed on the chosen fees goes from {money(owed)} to {money(Math.max(0, owed - estimate))}.
                        </p>
                    )}
                </div>
            )}
        </Modal>
    );
};

export default DiscountDialog;
