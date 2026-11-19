/**
 * Step 3 — Confirm
 * Final review before hitting the import endpoint.
 */
import { FC } from 'react';
import { Button } from '../../../../components';
import { ILocalClass } from './types';

interface IProps {
    rowsCount: number;
    classes: ILocalClass[];
    classId: string;
    sections: any[];
    sectionId: string;
    defaultPassword: string;
    isSubmitting: boolean;
    onBack: () => void;
    onConfirm: () => void;
}

const Step3Confirm: FC<IProps> = ({
    rowsCount,
    classes,
    classId,
    sections,
    sectionId,
    defaultPassword,
    isSubmitting,
    onBack,
    onConfirm,
}) => {
    const className =
        classes.find((c) => String(c.id) === String(classId))?.class_name ||
        classes.find((c) => String(c.id) === String(classId))?.name ||
        `#${classId}`;
    const sectionName =
        sections.find((s: any) => String(s.id) === String(sectionId))?.section_name || '—';

    return (
        <div className="space-y-6">
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6 text-center">
                <p className="text-sm text-brand-700 dark:text-blue-300 uppercase tracking-wider">
                    About to import
                </p>
                <p className="text-5xl font-bold text-blue-900 dark:text-blue-100 mt-2">
                    {rowsCount}
                </p>
                <p className="text-sm text-brand-700 dark:text-blue-300 mt-1">
                    student{rowsCount === 1 ? '' : 's'}
                </p>
            </div>

            <dl className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-5 grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                    <dt className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">
                        Class
                    </dt>
                    <dd className="mt-1 text-base font-medium text-gray-900 dark:text-white">
                        {className}
                    </dd>
                </div>
                <div>
                    <dt className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">
                        Section
                    </dt>
                    <dd className="mt-1 text-base font-medium text-gray-900 dark:text-white">
                        {sectionName}
                    </dd>
                </div>
                <div>
                    <dt className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">
                        Default Password
                    </dt>
                    <dd className="mt-1 text-base font-mono text-gray-900 dark:text-white">
                        {defaultPassword || '(empty)'}
                    </dd>
                </div>
            </dl>

            <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 text-sm text-yellow-900 dark:text-yellow-100">
                The server will still check for duplicate emails / usernames against existing students.
                Any rows that fail those checks will appear on the next screen.
            </div>

            <div className="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
                <Button variant="secondary" onClick={onBack} disabled={isSubmitting}>
                    ← Back
                </Button>
                <Button variant="primary" onClick={onConfirm} disabled={isSubmitting}>
                    {isSubmitting ? 'Importing…' : `Import ${rowsCount} Student${rowsCount === 1 ? '' : 's'}`}
                </Button>
            </div>
        </div>
    );
};

export default Step3Confirm;
