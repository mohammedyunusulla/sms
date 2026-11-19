/**
 * Subject Form Page
 * Create a new subject or edit an existing one (/academics/subjects/new, /academics/subjects/:id/edit)
 */

import { FC, useEffect, useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';
import toast from 'react-hot-toast';
import { useNavigate, useParams, useSearchParams } from 'react-router';
import {
    Button,
    EmptyState,
    FormField,
    FormInput,
    FormSelect,
    FormTextarea,
    LoadingSpinner,
    PageHeader
} from '../../components';
import { academicsService } from '../../services/modules/academicsService';
import { classService } from '../../services/modules/classService';

interface SubjectFormData {
    subject_name: string;
    subject_code: string;
    class_id: string;
    credits: string;
    description: string;
}

const EMPTY: SubjectFormData = { subject_name: '', subject_code: '', class_id: '', credits: '1', description: '' };

const SubjectForm: FC = () => {
    const navigate = useNavigate();
    const { id } = useParams<{ id: string }>();
    const [searchParams] = useSearchParams();
    const isEditMode = !!id;

    const [formData, setFormData] = useState<SubjectFormData>({ ...EMPTY, class_id: searchParams.get('classId') || '' });
    const [classes, setClasses] = useState<{ id: number | string; class_name: string }[]>([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const load = async () => {
            try {
                const classList = await classService.list();
                setClasses(classList || []);
                if (isEditMode && id) {
                    const subject = await academicsService.getSubjectById(id);
                    setFormData({
                        subject_name: subject.subject_name || '',
                        subject_code: subject.subject_code || '',
                        class_id: String(subject.class_id ?? ''),
                        credits: String(subject.credits ?? 1),
                        description: subject.description || '',
                    });
                }
            } catch (err) {
                const message = (err as { message?: string })?.message || 'Failed to load subject';
                setError(message);
                toast.error(message);
            } finally {
                setLoading(false);
            }
        };
        load();
    }, [id, isEditMode]);

    const handleChange = (e: ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
        const { name, value } = e.target;
        setFormData((prev) => ({ ...prev, [name]: value }));
    };

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        if (!formData.subject_name.trim() || !formData.subject_code.trim() || !formData.class_id) {
            toast.error('Subject name, code and class are required');
            return;
        }
        const payload = {
            subject_name: formData.subject_name.trim(),
            subject_code: formData.subject_code.trim(),
            class_id: Number(formData.class_id),
            credits: Number(formData.credits) || 1,
            description: formData.description.trim(),
        };
        setSaving(true);
        try {
            if (isEditMode && id) {
                await academicsService.updateSubject(id, payload);
                toast.success('Subject updated successfully');
            } else {
                await academicsService.createSubject(payload);
                toast.success('Subject created successfully');
            }
            navigate('/academics/subjects');
        } catch (err) {
            toast.error((err as { message?: string })?.message || 'Failed to save subject');
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return <LoadingSpinner fullHeight message={isEditMode ? 'Loading subject...' : 'Loading...'} />;
    }

    if (error) {
        return <EmptyState title="Error" description={error} />;
    }

    return (
        <form onSubmit={handleSubmit} className="space-y-6">
            <PageHeader
                title={isEditMode ? 'Edit Subject' : 'Create New Subject'}
                subtitle="Fill in the details below"
                breadcrumbs={[
                    { label: 'Dashboard', href: '/dashboard' },
                    { label: 'Subjects', href: '/academics/subjects' },
                    { label: isEditMode ? 'Edit' : 'New', href: '#' },
                ]}
            />

            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700 space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <FormField label="Subject Name" required>
                        <FormInput name="subject_name" value={formData.subject_name} onChange={handleChange} placeholder="e.g., Mathematics" required />
                    </FormField>
                    <FormField label="Subject Code" required>
                        <FormInput name="subject_code" value={formData.subject_code} onChange={handleChange} placeholder="e.g., MATH5" required />
                    </FormField>
                    <FormField label="Class" required>
                        <FormSelect
                            name="class_id"
                            value={formData.class_id}
                            onChange={handleChange}
                            options={classes.map((cls) => ({ label: cls.class_name || `Class ${cls.id}`, value: String(cls.id) }))}
                            placeholder="Select a class"
                        />
                    </FormField>
                    <FormField label="Credits">
                        <FormInput name="credits" type="number" min={1} value={formData.credits} onChange={handleChange} />
                    </FormField>
                </div>
                <FormField label="Description">
                    <FormTextarea name="description" value={formData.description} onChange={handleChange} rows={3} placeholder="Optional" />
                </FormField>
                <div className="flex items-center gap-3">
                    <Button type="button" variant="secondary" onClick={() => navigate('/academics/subjects')}>
                        Cancel
                    </Button>
                    <Button type="submit" variant="primary" disabled={saving}>
                        {saving ? 'Saving...' : isEditMode ? 'Save Changes' : 'Create Subject'}
                    </Button>
                </div>
            </div>
        </form>
    );
};

export default SubjectForm;
