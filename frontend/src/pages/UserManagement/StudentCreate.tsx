import { FC, useState } from 'react';
import { PageHeader } from '../../components';
import StudentForm from './StudentForm';
import BulkImportWizard from './components/BulkImportWizard';

const StudentCreate: FC = () => {
    const [createMode, setCreateMode] = useState<'single' | 'bulk'>('single');

    return (
        <div className="space-y-6">
            <PageHeader
                title="Create Student"
                subtitle="Choose how to add students"
                breadcrumbs={[
                    { label: 'Dashboard', href: '/dashboard' },
                    { label: 'Students', href: '/students' },
                    { label: 'Create', href: '#' },
                ]}
            />

            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md">
                <div className="flex border-b border-gray-200 dark:border-gray-700">
                    <button
                        onClick={() => setCreateMode('single')}
                        className={`flex-1 px-6 py-4 text-center font-medium transition-colors ${
                            createMode === 'single'
                                ? 'text-brand-600 dark:text-blue-400 border-b-2 border-brand-600 dark:border-brand-400'
                                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
                        }`}
                    >
                        Single Create
                    </button>
                    <button
                        onClick={() => setCreateMode('bulk')}
                        className={`flex-1 px-6 py-4 text-center font-medium transition-colors ${
                            createMode === 'bulk'
                                ? 'text-brand-600 dark:text-blue-400 border-b-2 border-brand-600 dark:border-brand-400'
                                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
                        }`}
                    >
                        Bulk Import
                    </button>
                </div>

                <div className="p-6">
                    {createMode === 'single' ? <StudentForm mode="create" /> : <BulkImportWizard />}
                </div>
            </div>
        </div>
    );
};

export default StudentCreate;
