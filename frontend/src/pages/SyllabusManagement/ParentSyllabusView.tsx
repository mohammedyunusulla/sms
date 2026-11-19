import { FC, useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import toast from 'react-hot-toast';
import { PageHeader, PageSkeleton, EmptyState } from '../../components';
import { syllabusService } from '../../services/modules/syllabusService';
import { IStudentSyllabusEntry } from '../../types';
import { useAuthStore } from '../../stores/authStore';
import { useParentStore } from '../../stores/parentStore';

const BookIcon = () => (
    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
    </svg>
);

const ParentSyllabusView: FC = () => {
    const navigate = useNavigate();
    const academicYear = useAuthStore((s) => s.user?.current_academic_year);
    const academicYearVersion = useAuthStore((s) => s.academicYearVersion);
    const selectedChild = useParentStore((s) => s.selectedChild);
    const childrenLoaded = useParentStore((s) => s.loaded);
    const childrenLoading = useParentStore((s) => s.loading);

    const [entries, setEntries] = useState<IStudentSyllabusEntry[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const studentId = selectedChild?.student_id;
    const academicYearId = academicYear?.id;
    const childName = selectedChild?.full_name || selectedChild?.first_name || '';

    useEffect(() => {
        if (!studentId || !academicYearId) {
            setEntries([]);
            return;
        }
        let cancelled = false;
        setLoading(true);
        setError(null);

        syllabusService
            .fetchStudentSyllabusView(String(academicYearId), String(studentId))
            .then((data) => {
                if (!cancelled) setEntries(data || []);
            })
            .catch((err: any) => {
                if (cancelled) return;
                const msg = err?.message || 'Failed to fetch syllabus progress';
                setError(msg);
                toast.error(msg);
                setEntries([]);
            })
            .finally(() => {
                if (!cancelled) setLoading(false);
            });

        return () => {
            cancelled = true;
        };
    }, [studentId, academicYearId, academicYearVersion]);

    const breadcrumbs = [
        { label: 'Dashboard', href: '/dashboard' },
        { label: "My Child's Syllabus" },
    ];

    return (
        <div className="p-3">
            <PageHeader
                title="My Child's Syllabus"
                subtitle={
                    selectedChild
                        ? `${childName}'s syllabus progress${academicYear?.year_name ? ` — ${academicYear.year_name}` : ''}`
                        : 'Pick a child from the header dropdown to view their syllabus'
                }
                breadcrumbs={breadcrumbs}
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
                <PageSkeleton header={false} infoCards={6} infoCardCols="grid-cols-1 sm:grid-cols-2 lg:grid-cols-3" panels={0} />
            ) : error ? (
                <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg">
                    {error}
                </div>
            ) : entries.length === 0 ? (
                <EmptyState
                    icon={<BookIcon />}
                    title="No syllabus found"
                    description={`No syllabus progress is available for ${childName}'s subjects yet.`}
                />
            ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                    {entries.map((entry, index) => (
                        <div
                            key={`${entry.syllabus.id}-${entry.teacher_id}-${index}`}
                            onClick={() =>
                                navigate(`/parent/syllabus/${entry.syllabus.id}?teacherId=${entry.teacher_id}`)
                            }
                            className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden hover:shadow-md transition-shadow cursor-pointer"
                        >
                            {/* Card Header */}
                            <div className="p-5 border-b border-gray-100 dark:border-gray-700">
                                <div className="flex items-center gap-2 mb-1">
                                    <span className="text-xs font-medium text-brand-600 dark:text-blue-400 uppercase tracking-wide">
                                        {entry.subject_name}
                                    </span>
                                </div>
                                <h3 className="text-lg font-semibold text-gray-900 dark:text-white truncate">
                                    {entry.syllabus.title}
                                </h3>
                            </div>

                            {/* Card Body */}
                            <div className="p-5">
                                <div className="flex items-center gap-2 mb-2">
                                    <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                                    </svg>
                                    <span className="text-sm text-gray-600 dark:text-gray-400">
                                        {entry.teacher_name}
                                    </span>
                                </div>
                            </div>

                            {/* Card Footer */}
                            <div className="px-5 py-3 bg-gray-50 dark:bg-gray-900/50 border-t border-gray-100 dark:border-gray-700">
                                <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                                    <span>Academic Year:</span>
                                    <span className="font-medium text-gray-700 dark:text-gray-300">
                                        {entry.syllabus.academic_year_name || 'N/A'}
                                    </span>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default ParentSyllabusView;
