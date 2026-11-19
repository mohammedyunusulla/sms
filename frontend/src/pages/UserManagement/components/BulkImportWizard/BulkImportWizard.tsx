/**
 * BulkImportWizard
 * Four-step wizard: Upload → Validate → Confirm → Result.
 */
import { FC, useEffect, useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import { useNavigate } from 'react-router';
import { Stepper } from '../../../../components';
import { classService } from '../../../../services/modules/classService';
import { studentService } from '../../../../services/modules/studentService';
import { validateAll } from '../../../../utils/studentImportValidator';
import Step1Upload from './Step1Upload';
import Step2Validate from './Step2Validate';
import Step3Confirm from './Step3Confirm';
import Step4Result from './Step4Result';
import { IBulkResult, ILocalClass, STEPS } from './types';

const BulkImportWizard: FC = () => {
    const navigate = useNavigate();

    const [step, setStep] = useState<number>(0);

    // Data state
    const [classes, setClasses] = useState<ILocalClass[]>([]);
    const [sections, setSections] = useState<any[]>([]);
    const [classId, setClassId] = useState('');
    const [sectionId, setSectionId] = useState('');
    const [defaultPassword, setDefaultPassword] = useState('Admin@123');
    const [file, setFile] = useState<File | null>(null);
    const [rows, setRows] = useState<Record<string, any>[]>([]);
    const [result, setResult] = useState<IBulkResult | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Initial classes fetch
    useEffect(() => {
        (async () => {
            try {
                const list = await classService.list();
                setClasses(Array.isArray(list) ? list : []);
            } catch {
                toast.error('Failed to load classes');
            }
        })();
    }, []);

    // Sections fetch when class changes
    useEffect(() => {
        if (!classId) {
            setSections([]);
            setSectionId('');
            return;
        }
        (async () => {
            try {
                const data = await classService.getSections(classId);
                setSections(Array.isArray(data) ? data : []);
                setSectionId('');
            } catch {
                toast.error('Failed to load sections');
                setSections([]);
            }
        })();
    }, [classId]);

    const validations = useMemo(() => validateAll(rows), [rows]);

    const canGoFromStep1 = !!file && rows.length > 0 && !!classId;
    const errorCount = validations.filter((v) => v.status === 'error').length;

    const handleImport = async () => {
        setIsSubmitting(true);
        try {
            const studentsData = rows.map((r: any) => ({
                username: r.username || '',
                first_name: r.first_name || '',
                last_name: r.last_name || '',
                email: r.email || '',
                phone: r.phone || '',
                gender: r.gender || '',
                date_of_birth: r.date_of_birth || '',
                address: r.address || '',
                roll_no: r.roll_no || '',
                admission_date: r.admission_date || '',
                class_id: classId,
                section_id: sectionId || '',
                has_login: true,
                is_active: true,
            }));

            const res: IBulkResult = await studentService.bulkCreate(studentsData, defaultPassword);
            setResult(res);
            setStep(3);

            if (res.failed === 0) {
                toast.success(`All ${res.successful} students imported`);
            } else if (res.successful === 0) {
                toast.error(`Import failed for all ${res.failed} rows`);
            } else {
                toast(`${res.successful} succeeded, ${res.failed} failed`, { icon: '⚠️' });
            }
        } catch (err: any) {
            toast.error(err?.message || 'Import failed');
        } finally {
            setIsSubmitting(false);
        }
    };

    const resetForMore = () => {
        setFile(null);
        setRows([]);
        setResult(null);
        setStep(0);
    };

    return (
        <div className="space-y-8">
            <Stepper steps={[...STEPS]} activeStep={step} />

            <div>
                {step === 0 && (
                    <Step1Upload
                        file={file}
                        onFileParsed={(f, parsedRows) => {
                            setFile(f);
                            setRows(parsedRows);
                        }}
                        classes={classes}
                        classId={classId}
                        setClassId={setClassId}
                        sections={sections}
                        sectionId={sectionId}
                        setSectionId={setSectionId}
                        defaultPassword={defaultPassword}
                        setDefaultPassword={setDefaultPassword}
                        canGoNext={canGoFromStep1}
                        onNext={() => setStep(1)}
                        onCancel={() => navigate('/students')}
                    />
                )}
                {step === 1 && (
                    <Step2Validate
                        rows={rows}
                        validations={validations}
                        onBack={() => setStep(0)}
                        onNext={() => setStep(2)}
                    />
                )}
                {step === 2 && (
                    <Step3Confirm
                        rowsCount={rows.length}
                        classes={classes}
                        classId={classId}
                        sections={sections}
                        sectionId={sectionId}
                        defaultPassword={defaultPassword}
                        isSubmitting={isSubmitting}
                        onBack={() => setStep(1)}
                        onConfirm={handleImport}
                    />
                )}
                {step === 3 && result && (
                    <Step4Result
                        result={result}
                        onImportMore={resetForMore}
                        onDone={() => navigate('/students')}
                    />
                )}
            </div>

            {/* Block Step 2 → 3 transition if errors remain */}
            {step === 1 && errorCount > 0 && (
                <p className="text-xs text-gray-500 dark:text-gray-400 text-right">
                    {errorCount} row{errorCount === 1 ? '' : 's'} need fixing before continuing.
                </p>
            )}
        </div>
    );
};

export default BulkImportWizard;
