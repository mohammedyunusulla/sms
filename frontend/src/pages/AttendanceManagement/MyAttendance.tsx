/**
 * Attendance for students (their own) and parents (the child picked in the header dropdown).
 */
import { FC } from 'react';
import { PageHeader } from '../../components';
import { useAuthStore } from '../../stores/authStore';
import { useParentStore } from '../../stores/parentStore';
import StudentAttendanceView from './StudentAttendanceView';

export const MyAttendance: FC = () => {
    const user = useAuthStore((s) => s.user);
    return (
        <div className="space-y-6">
            <PageHeader
                title="My Attendance"
                subtitle="Your attendance month by month"
                breadcrumbs={[{ label: 'Dashboard', href: '/dashboard' }, { label: 'My Attendance', href: '#' }]}
            />
            {user?.role === 'STUDENT' && user.school_user_id
                ? <StudentAttendanceView studentId={user.school_user_id} />
                : <p className="text-sm text-gray-500 dark:text-gray-400">This page is for student accounts.</p>}
        </div>
    );
};

export const ParentAttendance: FC = () => {
    const selectedChild = useParentStore((s) => s.selectedChild);
    const childrenLoaded = useParentStore((s) => s.loaded);
    const childrenLoading = useParentStore((s) => s.loading);
    const childName = selectedChild?.full_name || selectedChild?.first_name || '';
    return (
        <div className="space-y-6">
            <PageHeader
                title="My Child's Attendance"
                subtitle={selectedChild ? `${childName}'s attendance month by month` : 'Pick a child from the header dropdown to view their attendance'}
                breadcrumbs={[{ label: 'Dashboard', href: '/dashboard' }, { label: "My Child's Attendance", href: '#' }]}
            />
            {!selectedChild ? (
                <div className="rounded-lg border border-gray-200 bg-white p-8 text-center dark:border-gray-700 dark:bg-gray-800">
                    <p className="text-gray-500 dark:text-gray-400">
                        {childrenLoading ? 'Loading your children…' : childrenLoaded ? 'No children linked to your account yet.' : 'Select a child from the dropdown in the header to begin.'}
                    </p>
                </div>
            ) : (
                <StudentAttendanceView key={selectedChild.student_id} studentId={Number(selectedChild.student_id)} />
            )}
        </div>
    );
};
