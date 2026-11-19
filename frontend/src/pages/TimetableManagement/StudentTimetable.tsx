import { FC } from 'react';
import { PageHeader } from '../../components';
import { useAuthStore } from '../../stores/authStore';
import DailyTimetableView from './DailyTimetableView';

const StudentTimetable: FC = () => {
    const user = useAuthStore((s) => s.user);
    const academicYear = useAuthStore((s) => s.user?.current_academic_year);

    return (
        <div className="space-y-6">
            <PageHeader
                title="My Timetable"
                subtitle={
                    academicYear?.year_name
                        ? `Your daily schedule — ${academicYear.year_name}`
                        : 'Your daily schedule'
                }
                breadcrumbs={[
                    { label: 'Dashboard', href: '/dashboard' },
                    { label: 'My Timetable', href: '#' },
                ]}
            />

            <DailyTimetableView studentId={user?.school_user_id} />
        </div>
    );
};

export default StudentTimetable;
