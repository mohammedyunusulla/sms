/**
 * Exam results for students (their own) and parents (the child picked in the header dropdown).
 * Only exams whose results the school has published are shown (enforced by the backend).
 */
import { FC } from 'react';
import { PageHeader } from '../../components';
import { useAuthStore } from '../../stores/authStore';
import { useParentStore } from '../../stores/parentStore';
import { AnnualResultsView } from './AnnualProgressReport';

export const MyResults: FC = () => {
    const user = useAuthStore((s) => s.user);
    return (
        <div className="space-y-6">
            <PageHeader
                title="My Results"
                subtitle="Your marks and report cards for each exam"
                breadcrumbs={[{ label: 'Dashboard', href: '/dashboard' }, { label: 'My Results', href: '#' }]}
            />
            {user?.role === 'STUDENT' && user.school_user_id
                ? <AnnualResultsView studentId={String(user.school_user_id)} forFamily />
                : <p className="text-sm text-gray-500 dark:text-gray-400">This page is for student accounts.</p>}
        </div>
    );
};

export const ParentResults: FC = () => {
    const selectedChild = useParentStore((s) => s.selectedChild);
    const childrenLoaded = useParentStore((s) => s.loaded);
    const childrenLoading = useParentStore((s) => s.loading);
    const childName = selectedChild?.full_name || selectedChild?.first_name || '';
    return (
        <div className="space-y-6">
            <PageHeader
                title="My Child's Results"
                subtitle={selectedChild ? `${childName}'s marks and report cards` : 'Pick a child from the header dropdown to view their results'}
                breadcrumbs={[{ label: 'Dashboard', href: '/dashboard' }, { label: "My Child's Results", href: '#' }]}
            />
            {!selectedChild ? (
                <div className="rounded-lg border border-gray-200 bg-white p-8 text-center dark:border-gray-700 dark:bg-gray-800">
                    <p className="text-gray-500 dark:text-gray-400">
                        {childrenLoading ? 'Loading your children…' : childrenLoaded ? 'No children linked to your account yet.' : 'Select a child from the dropdown in the header to begin.'}
                    </p>
                </div>
            ) : (
                <AnnualResultsView key={selectedChild.student_id} studentId={String(selectedChild.student_id)} forFamily />
            )}
        </div>
    );
};
