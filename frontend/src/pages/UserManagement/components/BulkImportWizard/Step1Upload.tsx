/**
 * Step 1 — Upload
 * Class/section selection, default password, file dropzone, template downloads.
 */
import { FC } from 'react';
import { useDropzone } from 'react-dropzone';
import toast from 'react-hot-toast';
import { Button, FormField, FormInput, FormSelect, MandatoryIndicator } from '../../../../components';
import { parseSheet, buildXlsx, downloadBlob } from '../../../../utils/sheetParser';
import { ILocalClass } from './types';

interface IProps {
    file: File | null;
    onFileParsed: (file: File, rows: Record<string, any>[]) => void;
    classes: ILocalClass[];
    classId: string;
    setClassId: (v: string) => void;
    sections: any[];
    sectionId: string;
    setSectionId: (v: string) => void;
    defaultPassword: string;
    setDefaultPassword: (v: string) => void;
    canGoNext: boolean;
    onNext: () => void;
    onCancel: () => void;
}

const TEMPLATE_HEADERS = [
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

const TEMPLATE_ROWS: string[][] = [
    ['student001', 'John', 'Doe', 'john.doe@example.com', '9876543210', 'Male', '2008-01-15', '123 Main St', '1', '2024-01-15'],
    ['student002', 'Jane', 'Smith', 'jane.smith@example.com', '9876543211', 'Female', '2008-03-20', '456 Oak Ave', '2', '2024-01-15'],
    ['student003', 'Michael', 'Brown', 'michael.brown@example.com', '9876543212', 'Male', '2008-05-10', '789 Pine Rd', '3', '2024-01-15'],
];

function downloadCsvTemplate() {
    const lines = [TEMPLATE_HEADERS.join(','), ...TEMPLATE_ROWS.map((r) => r.join(','))];
    const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8' });
    downloadBlob(blob, 'student_template.csv');
}

function downloadXlsxTemplate() {
    const blob = buildXlsx(TEMPLATE_HEADERS, TEMPLATE_ROWS);
    downloadBlob(blob, 'student_template.xlsx');
}

const Step1Upload: FC<IProps> = ({
    file,
    onFileParsed,
    classes,
    classId,
    setClassId,
    sections,
    sectionId,
    setSectionId,
    defaultPassword,
    setDefaultPassword,
    canGoNext,
    onNext,
    onCancel,
}) => {
    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        accept: {
            'text/csv': ['.csv'],
            'application/vnd.ms-excel': ['.xls'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
        },
        multiple: false,
        onDrop: async (accepted) => {
            const f = accepted[0];
            if (!f) return;
            try {
                const rows = await parseSheet(f);
                if (rows.length === 0) {
                    toast.error('File is empty or could not be parsed');
                    return;
                }
                onFileParsed(f, rows);
            } catch (err: any) {
                toast.error(err?.message || 'Failed to parse file');
            }
        },
    });

    return (
        <div className="space-y-6">
            {/* Template downloads — prominent at the top */}
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-5">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                    <div>
                        <h4 className="font-semibold text-blue-900 dark:text-blue-100 mb-1">
                            Step 1 — Start with a template
                        </h4>
                        <p className="text-sm text-blue-800 dark:text-blue-200">
                            Download the template, fill in your students, then upload below.
                        </p>
                    </div>
                    <div className="flex gap-2">
                        <Button variant="secondary" size="sm" onClick={downloadCsvTemplate}>
                            ⬇ CSV Template
                        </Button>
                        <Button variant="secondary" size="sm" onClick={downloadXlsxTemplate}>
                            ⬇ XLSX Template
                        </Button>
                    </div>
                </div>
            </div>

            {/* Class / Section / Password */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <FormField label="Class" required>
                    <FormSelect
                        value={classId}
                        onChange={(e) => setClassId(e.target.value)}
                        options={classes.map((c) => ({
                            label: c.class_name || c.name || `#${c.id}`,
                            value: String(c.id),
                        }))}
                        placeholder="Select a class"
                        required
                    />
                </FormField>

                <FormField label="Section">
                    <FormSelect
                        value={sectionId}
                        onChange={(e) => setSectionId(e.target.value)}
                        options={sections.map((s: any) => ({
                            label: s.section_name,
                            value: String(s.id),
                        }))}
                        placeholder={classId ? 'Select section (optional)' : 'Pick a class first'}
                        disabled={!classId}
                    />
                </FormField>

                <FormField
                    label="Default password"
                    help="Applied to all imported students. They can change it on first login."
                >
                    <FormInput
                        value={defaultPassword}
                        onChange={(e) => setDefaultPassword(e.target.value)}
                        placeholder="Admin@123"
                    />
                </FormField>
            </div>

            {/* Dropzone */}
            <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Student data file <MandatoryIndicator />
                    <span className="ml-2 text-xs font-normal text-gray-500 dark:text-gray-400">
                        (.csv, .xls, .xlsx)
                    </span>
                </label>
                <div
                    {...getRootProps()}
                    className={`border-2 border-dashed rounded-lg p-10 text-center cursor-pointer transition-colors ${
                        isDragActive
                            ? 'border-brand-500 bg-blue-50 dark:bg-blue-900/20'
                            : file
                              ? 'border-green-500 bg-green-50 dark:bg-green-900/20'
                              : 'border-gray-300 dark:border-gray-600 hover:border-gray-400'
                    }`}
                >
                    <input {...getInputProps()} />
                    <div className="text-gray-600 dark:text-gray-400">
                        {file ? (
                            <>
                                <p className="font-medium text-green-600 dark:text-green-400 text-lg">
                                    ✓ {file.name}
                                </p>
                                <p className="text-sm mt-1">Drop another file or click to replace</p>
                            </>
                        ) : isDragActive ? (
                            <p className="font-medium text-brand-600 dark:text-blue-400 text-lg">
                                Drop your file here
                            </p>
                        ) : (
                            <>
                                <p className="font-medium text-lg">Drag and drop your file here</p>
                                <p className="text-sm mt-1">or click to select</p>
                            </>
                        )}
                    </div>
                </div>
            </div>

            {/* Action bar */}
            <div className="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
                <Button variant="secondary" onClick={onCancel}>
                    Cancel
                </Button>
                <Button variant="primary" onClick={onNext} disabled={!canGoNext}>
                    Next: Validate →
                </Button>
            </div>
        </div>
    );
};

export default Step1Upload;
