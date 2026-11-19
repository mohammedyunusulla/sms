/**
 * Step 4 — Result
 * Server response: per-row outcome + download-failed-rows + reset.
 */
import { FC } from 'react';
import { Button } from '../../../../components';
import { downloadBlob } from '../../../../utils/sheetParser';
import { IBulkResult, IBulkRowError } from './types';

interface IProps {
    result: IBulkResult;
    onImportMore: () => void;
    onDone: () => void;
}

function downloadFailedRowsCSV(errors: IBulkRowError[]) {
    const escape = (val: string) => `"${(val || '').replace(/"/g, '""')}"`;
    const lines = [
        ['row', 'name', 'email', 'error'].join(','),
        ...errors.map((e) =>
            [e.row, escape(e.name || ''), escape(e.email || ''), escape(e.error || '')].join(',')
        ),
    ];
    const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8' });
    downloadBlob(blob, 'student_import_errors.csv');
}

const Step4Result: FC<IProps> = ({ result, onImportMore, onDone }) => {
    const allOk = result.failed === 0;
    return (
        <div className="space-y-4">
            {/* Summary cards */}
            <div className="grid grid-cols-3 gap-4">
                <div className="p-4 rounded-lg bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600">
                    <p className="text-xs text-gray-500 dark:text-gray-400 uppercase">Total</p>
                    <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                        {result.total}
                    </p>
                </div>
                <div className="p-4 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
                    <p className="text-xs text-green-700 dark:text-green-300 uppercase">Successful</p>
                    <p className="text-2xl font-semibold text-green-700 dark:text-green-300">
                        {result.successful}
                    </p>
                </div>
                <div className="p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                    <p className="text-xs text-red-700 dark:text-red-300 uppercase">Failed</p>
                    <p className="text-2xl font-semibold text-red-700 dark:text-red-300">
                        {result.failed}
                    </p>
                </div>
            </div>

            {allOk && (
                <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4 text-sm text-green-900 dark:text-green-100">
                    🎉 All {result.successful} students imported successfully.
                </div>
            )}

            {/* Errors */}
            {result.errors && result.errors.length > 0 && (
                <div className="bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800 rounded-lg overflow-hidden">
                    <div className="flex items-center justify-between px-4 py-3 border-b border-red-200 dark:border-red-800">
                        <h4 className="font-semibold text-red-800 dark:text-red-200">
                            Failed Rows ({result.errors.length})
                        </h4>
                        <button
                            type="button"
                            onClick={() => downloadFailedRowsCSV(result.errors!)}
                            className="text-sm text-red-700 dark:text-red-300 hover:underline"
                        >
                            📥 Download failed rows
                        </button>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead className="bg-red-100/60 dark:bg-red-900/30">
                                <tr>
                                    <th className="px-4 py-2 text-left font-medium text-red-900 dark:text-red-200">
                                        Row
                                    </th>
                                    <th className="px-4 py-2 text-left font-medium text-red-900 dark:text-red-200">
                                        Name
                                    </th>
                                    <th className="px-4 py-2 text-left font-medium text-red-900 dark:text-red-200">
                                        Email
                                    </th>
                                    <th className="px-4 py-2 text-left font-medium text-red-900 dark:text-red-200">
                                        Error
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-red-200 dark:divide-red-800">
                                {result.errors.map((err) => (
                                    <tr
                                        key={err.row}
                                        className="hover:bg-red-100/40 dark:hover:bg-red-900/20"
                                    >
                                        <td className="px-4 py-2 font-mono text-red-900 dark:text-red-200">
                                            {err.row}
                                        </td>
                                        <td className="px-4 py-2 text-gray-800 dark:text-gray-200">
                                            {err.name?.trim() || '—'}
                                        </td>
                                        <td className="px-4 py-2 text-gray-800 dark:text-gray-200">
                                            {err.email || '—'}
                                        </td>
                                        <td className="px-4 py-2 text-red-700 dark:text-red-300">
                                            {err.error}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Successes (collapsed) */}
            {result.created_students && result.created_students.length > 0 && (
                <details className="bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-800 rounded-lg">
                    <summary className="px-4 py-3 cursor-pointer font-semibold text-green-800 dark:text-green-200">
                        Successful Rows ({result.created_students.length})
                    </summary>
                    <div className="overflow-x-auto border-t border-green-200 dark:border-green-800">
                        <table className="w-full text-sm">
                            <thead className="bg-green-100/60 dark:bg-green-900/30">
                                <tr>
                                    <th className="px-4 py-2 text-left font-medium text-green-900 dark:text-green-200">
                                        Row
                                    </th>
                                    <th className="px-4 py-2 text-left font-medium text-green-900 dark:text-green-200">
                                        Name
                                    </th>
                                    <th className="px-4 py-2 text-left font-medium text-green-900 dark:text-green-200">
                                        Email
                                    </th>
                                    <th className="px-4 py-2 text-left font-medium text-green-900 dark:text-green-200">
                                        Roll No
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-green-200 dark:divide-green-800">
                                {result.created_students.map((s) => (
                                    <tr
                                        key={s.row}
                                        className="hover:bg-green-100/40 dark:hover:bg-green-900/20"
                                    >
                                        <td className="px-4 py-2 font-mono text-green-900 dark:text-green-200">
                                            {s.row}
                                        </td>
                                        <td className="px-4 py-2 text-gray-800 dark:text-gray-200">
                                            {s.name?.trim() || '—'}
                                        </td>
                                        <td className="px-4 py-2 text-gray-800 dark:text-gray-200">
                                            {s.email || '—'}
                                        </td>
                                        <td className="px-4 py-2 text-gray-800 dark:text-gray-200">
                                            {s.roll_no || '—'}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </details>
            )}

            <div className="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
                <Button variant="secondary" onClick={onImportMore}>
                    Import More
                </Button>
                <Button variant="primary" onClick={onDone}>
                    Done
                </Button>
            </div>
        </div>
    );
};

export default Step4Result;
