/**
 * Exam timetable for parents: the child picked in the header dropdown (QA D22).
 * The server only returns a parent's own children's timetables.
 */
import { FC } from 'react';
import { PageHeader } from '../../components';
import { useParentStore } from '../../stores/parentStore';
import StudentExamTimetable from './StudentExamTimetable';

const ParentExamTimetable: FC = () => {
    const selectedChild = useParentStore((s) => s.selectedChild);
    const childrenLoaded = useParentStore((s) => s.loaded);
    const childrenLoading = useParentStore((s) => s.loading);
    const childName = selectedChild?.full_name || selectedChild?.first_name || '';

    if (!selectedChild) {
        return (
            <div className="space-y-6">
                <PageHeader
                    title="My Child's Exam Timetable"
                    subtitle="Pick a child from the header dropdown to view their exam timetable"
                    breadcrumbs={[{ label: 'Dashboard', href: '/dashboard' }, { label: "My Child's Exam Timetable", href: '#' }]}
                />
                <div className="rounded-lg border border-gray-200 bg-white p-8 text-center dark:border-gray-700 dark:bg-gray-800">
                    <p className="text-gray-500 dark:text-gray-400">
                        {childrenLoading ? 'Loading your children…' : childrenLoaded ? 'No children linked to your account yet.' : 'Select a child from the dropdown in the header to begin.'}
                    </p>
                </div>
            </div>
        );
    }
    return (
        <StudentExamTimetable
            key={selectedChild.student_id}
            studentId={selectedChild.student_id}
            title="My Child's Exam Timetable"
            subtitle={`${childName}'s exam schedule with room and seat details`}
        />
    );
};

export default ParentExamTimetable;
