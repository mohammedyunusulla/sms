import { FC } from 'react';
import { PageHeader } from '../../components';
import { useAuthStore } from '../../stores/authStore';
import { useParentStore } from '../../stores/parentStore';
import DailyTimetableView from './DailyTimetableView';

const ParentTimetable: FC = () => {
    const academicYear = useAuthStore((s) => s.user?.current_academic_year);
    const selectedChild = useParentStore((s) => s.selectedChild);
    const childrenLoaded = useParentStore((s) => s.loaded);
    const childrenLoading = useParentStore((s) => s.loading);

    const childName = selectedChild?.full_name || selectedChild?.first_name || '';

    return (
        <div className="space-y-6">
            <PageHeader
                title="My Child's Timetable"
                subtitle={
                    selectedChild
                        ? `${childName}'s schedule${academicYear?.year_name ? ` — ${academicYear.year_name}` : ''}`
                        : 'Pick a child from the header dropdown to view their timetable'
                }
                breadcrumbs={[
                    { label: 'Dashboard', href: '/dashboard' },
                    { label: "My Child's Timetable", href: '#' },
                ]}
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
            ) : (
                <DailyTimetableView studentId={selectedChild.student_id} />
            )}
        </div>
    );
};

export default ParentTimetable;
