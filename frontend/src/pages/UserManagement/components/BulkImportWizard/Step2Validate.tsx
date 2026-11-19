/**
 * Step 2 — Validate
 * Show all rows with per-cell error highlighting. Block Next until errors are zero.
 */
import { FC, useMemo } from 'react';
import { Button } from '../../../../components';
import { IRowValidation, fieldErrorMap } from '../../../../utils/studentImportValidator';

interface IProps {
    rows: Record<string, any>[];
    validations: IRowValidation[];
    onBack: () => void;
    onNext: () => void;
}

const COLUMNS = [
    'username',
    'first_name',
    'last_name',
    'email',
    'phone',
    'gender',
    'date_of_birth',
    'address',
    'roll_no',
    'admission_date',
];

const Step2Validate: FC<IProps> = ({ rows, validations, onBack, onNext }) => {
    const validCount = useMemo(
        () => validations.filter((v) => v.status === 'valid').length,
        [validations]
    );
    const errorCount = validations.length - validCount;

    return (
        <div className="space-y-4">
            {/* Summary */}
            <div className="grid grid-cols-3 gap-4">
                <div className="p-4 rounded-lg bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600">
                    <p className="text-xs text-gray-500 dark:text-gray-400 uppercase">Total Rows</p>
                    <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                        {rows.length}
                    </p>
                </div>
                <div className="p-4 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
                    <p className="text-xs text-green-700 dark:text-green-300 uppercase">Ready</p>
                    <p className="text-2xl font-semibold text-green-700 dark:text-green-300">
                        {validCount}
                    </p>
                </div>
                <div className="p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                    <p className="text-xs text-red-700 dark:text-red-300 uppercase">Errors</p>
                    <p className="text-2xl font-semibold text-red-700 dark:text-red-300">
                        {errorCount}
                    </p>
                </div>
            </div>

            {errorCount > 0 && (
                <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 text-sm text-yellow-900 dark:text-yellow-100">
                    Fix the highlighted cells in your file and re-upload, then try again. Hover a red
                    cell to see the specific error.
                </div>
            )}

            {/* Rows table */}
            <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
                <div className="overflow-x-auto max-h-[60vh]">
                    <table className="w-full text-sm">
                        <thead className="bg-gray-50 dark:bg-gray-700/50 sticky top-0">
                            <tr>
                                <th className="px-3 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">
                                    #
                                </th>
                                <th className="px-3 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">
                                    Status
                                </th>
                                {COLUMNS.map((col) => (
                                    <th
                                        key={col}
                                        className="px-3 py-2 text-left font-semibold text-gray-700 dark:text-gray-300 whitespace-nowrap"
                                    >
                                        {col}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                            {rows.map((row, idx) => {
                                const v = validations[idx];
                                const errMap = fieldErrorMap(v);
                                const isValid = v.status === 'valid';
                                return (
                                    <tr
                                        key={idx}
                                        className={
                                            isValid
                                                ? 'hover:bg-gray-50 dark:hover:bg-gray-700/30'
                                                : 'bg-red-50/40 dark:bg-red-900/10 hover:bg-red-50 dark:hover:bg-red-900/20'
                                        }
                                    >
                                        <td className="px-3 py-2 font-mono text-gray-600 dark:text-gray-400">
                                            {idx + 1}
                                        </td>
                                        <td className="px-3 py-2">
                                            {isValid ? (
                                                <span
                                                    title="Valid"
                                                    className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300"
                                                >
                                                    ✓ OK
                                                </span>
                                            ) : (
                                                <span
                                                    title={v.errors.map((e) => e.message).join(' • ')}
                                                    className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300"
                                                >
                                                    ✗ {v.errors.length} error
                                                    {v.errors.length > 1 ? 's' : ''}
                                                </span>
                                            )}
                                        </td>
                                        {COLUMNS.map((col) => {
                                            const value = row[col] ?? '';
                                            const err = errMap[col];
                                            return (
                                                <td
                                                    key={col}
                                                    title={err || ''}
                                                    className={`px-3 py-2 whitespace-nowrap ${
                                                        err
                                                            ? 'bg-red-100 dark:bg-red-900/30 border-l-2 border-red-500 text-red-900 dark:text-red-200'
                                                            : 'text-gray-800 dark:text-gray-200'
                                                    }`}
                                                >
                                                    {String(value) || (
                                                        <span className="text-gray-400">—</span>
                                                    )}
                                                    {err && (
                                                        <span className="block text-xs text-red-600 dark:text-red-400 mt-0.5 font-medium">
                                                            {err}
                                                        </span>
                                                    )}
                                                </td>
                                            );
                                        })}
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Action bar */}
            <div className="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
                <Button variant="secondary" onClick={onBack}>
                    ← Back
                </Button>
                <Button variant="primary" onClick={onNext} disabled={errorCount > 0}>
                    Next: Confirm →
                </Button>
            </div>
        </div>
    );
};

export default Step2Validate;
