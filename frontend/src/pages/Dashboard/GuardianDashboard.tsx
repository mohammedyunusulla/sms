/**
 * Guardian Dashboard
 * Parent dashboard built only on real data for the parent's linked children:
 * attendance (this academic year), fee balance, today's timetable and recent announcements.
 */

import { FC, useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router';
import { PageHeader, Button } from '../../components';
import StatCard from '../../components/dashboard/StatCard';
import QuickActionButton from '../../components/dashboard/QuickActionButton';
import { useAuthStore } from '../../stores/authStore';
import { useParentStore, ParentChild } from '../../stores/parentStore';
import { attendanceService } from '../../services/modules/attendanceService';
import { financeService } from '../../services/modules/financeService';
import { announcementService } from '../../services/modules/announcementService';
import dashboardService, { StudentTimetablePeriod } from '../../services/dashboardService';

interface ChildStats {
    attendance: number | null; // % this academic year, null = no attendance marked yet
    attendanceError?: boolean;
    balance: number | null;
    feeError?: boolean;
}

interface Announcement {
    id: number;
    title: string;
    description?: string;
    publish_date?: string;
    created_at?: string;
    priority?: string;
}

const todayIso = () => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

const formatMoney = (amount: number) => `₹${amount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

const childName = (child: ParentChild) => child.full_name || `${child.first_name} ${child.last_name ?? ''}`.trim();

const classLabel = (child: ParentChild) =>
    child.class_name ? `${child.class_name}${child.section_name ? ` – ${child.section_name}` : ''}` : 'Class not assigned';

const GuardianDashboard: FC = () => {
    const navigate = useNavigate();
    const user = useAuthStore((s) => s.user);
    const academicYear = useAuthStore((s) => s.user?.current_academic_year);
    const academicYearVersion = useAuthStore((s) => s.academicYearVersion);
    const { children, loaded: childrenLoaded, loading: childrenLoading, selectedChild, selectChild } = useParentStore();

    const [stats, setStats] = useState<Record<number, ChildStats>>({});
    const [statsLoading, setStatsLoading] = useState(false);
    const [timetable, setTimetable] = useState<StudentTimetablePeriod[]>([]);
    const [timetableState, setTimetableState] = useState<'idle' | 'loading' | 'error'>('idle');
    const [announcements, setAnnouncements] = useState<Announcement[]>([]);
    const [announcementsState, setAnnouncementsState] = useState<'idle' | 'loading' | 'error'>('idle');

    const academicYearId = academicYear?.id;
    const skid = user?.skid;

    // Attendance + fee balance per child (each call independent: one failure doesn't blank the page)
    const loadChildStats = useCallback(async () => {
        if (!academicYearId || children.length === 0) return;
        setStatsLoading(true);
        const start = academicYear?.start_date ? String(academicYear.start_date).slice(0, 10) : undefined;
        const end = todayIso();
        const entries = await Promise.all(
            children.map(async (child): Promise<[number, ChildStats]> => {
                const [attendance, fees] = await Promise.allSettled([
                    attendanceService.getStudentAttendance(child.student_id, start, end),
                    financeService.getStudentFeeSummary(child.student_id, academicYearId),
                ]);
                const statistics = attendance.status === 'fulfilled' ? attendance.value?.statistics : undefined;
                // financeService returns either the summary itself or { data: summary }
                const feeValue = fees.status === 'fulfilled'
                    ? (fees.value as { data?: { balance?: number }; balance?: number } | undefined)
                    : undefined;
                const feeData = feeValue?.data ?? feeValue;
                return [child.student_id, {
                    attendance: statistics && statistics.total_days > 0 ? statistics.attendance_percentage : null,
                    attendanceError: attendance.status === 'rejected',
                    balance: feeData && typeof feeData.balance === 'number' ? feeData.balance : null,
                    feeError: fees.status === 'rejected',
                }];
            })
        );
        setStats(Object.fromEntries(entries));
        setStatsLoading(false);
    }, [children, academicYearId, academicYear?.start_date]);

    const loadTimetable = useCallback(async () => {
        if (!skid || !selectedChild) return;
        setTimetableState('loading');
        try {
            const periods = await dashboardService.getStudentDayTimetable(skid, selectedChild.student_id, todayIso());
            setTimetable([...periods].sort((a, b) => a.period_number - b.period_number));
            setTimetableState('idle');
        } catch {
            setTimetable([]);
            setTimetableState('error');
        }
    }, [skid, selectedChild]);

    const loadAnnouncements = useCallback(async () => {
        if (!academicYearId || !user) return;
        setAnnouncementsState('loading');
        try {
            // academic year + role/user filters are what the backend list endpoint reads
            const params = {
                page: 1,
                limit: 5,
                academic_year_id: String(academicYearId),
                user_role: 'PARENT',
                school_user_id: user.school_user_id,
            };
            const response = await announcementService.list(params as Parameters<typeof announcementService.list>[0]);
            setAnnouncements((response.data as unknown as Announcement[]) || []);
            setAnnouncementsState('idle');
        } catch {
            setAnnouncements([]);
            setAnnouncementsState('error');
        }
    }, [academicYearId, user]);

    useEffect(() => { loadChildStats(); }, [loadChildStats, academicYearVersion]);
    useEffect(() => { loadTimetable(); }, [loadTimetable]);
    useEffect(() => { loadAnnouncements(); }, [loadAnnouncements, academicYearVersion]);

    const refreshAll = () => { loadChildStats(); loadTimetable(); loadAnnouncements(); };

    // Summary numbers from the per-child stats
    const summary = useMemo(() => {
        const values = Object.values(stats);
        const attendanceValues = values.map((s) => s.attendance).filter((v): v is number => v !== null);
        const balances = values.map((s) => s.balance).filter((v): v is number => v !== null);
        const weekAgo = Date.now() - 7 * 24 * 3600 * 1000;
        return {
            avgAttendance: attendanceValues.length ? Math.round(attendanceValues.reduce((a, b) => a + b, 0) / attendanceValues.length) : null,
            totalBalance: balances.length ? balances.reduce((a, b) => a + b, 0) : null,
            recentAnnouncements: announcements.filter((a) => {
                const when = Date.parse(a.publish_date || a.created_at || '');
                return !Number.isNaN(when) && when >= weekAgo;
            }).length,
        };
    }, [stats, announcements]);

    const quickActions = [
        { icon: '📝', label: 'Assignments', path: '/parent/assignments', variant: 'primary' as const },
        { icon: '📅', label: 'Timetable', path: '/parent/timetable', variant: 'success' as const },
        { icon: '💰', label: 'Fees', path: '/parent/fees', variant: 'warning' as const },
        { icon: '📚', label: 'Syllabus', path: '/parent/syllabus', variant: 'info' as const },
    ];

    // ---------- empty states
    if (!childrenLoaded || childrenLoading) {
        return (
            <div className="space-y-6">
                <PageHeader title="Guardian Dashboard" subtitle="Your children's attendance, fees and schedule" />
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    {[0, 1, 2, 3].map((i) => <StatCard key={i} title="Loading" value="" loading />)}
                </div>
            </div>
        );
    }

    if (children.length === 0) {
        return (
            <div className="space-y-6">
                <PageHeader title="Guardian Dashboard" subtitle="Your children's attendance, fees and schedule" />
                <div className="p-8 text-center bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                    <p className="text-4xl mb-3">👨‍👩‍👧</p>
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-white">No children linked yet</h2>
                    <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                        Your account isn't linked to a student. Please contact the school office.
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <PageHeader
                title="Guardian Dashboard"
                subtitle={`Your children's attendance, fees and schedule${academicYear?.year_name ? ` — ${academicYear.year_name}` : ''}`}
                actions={<Button variant="secondary" onClick={refreshAll}>Refresh</Button>}
            />

            {!academicYearId && (
                <div className="p-4 rounded-lg border border-yellow-200 bg-yellow-50 text-yellow-800 dark:border-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-300">
                    The school hasn't set a current academic year yet, so attendance, fees and announcements can't be shown.
                </div>
            )}

            {/* Key statistics */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <StatCard title="Children" value={children.length} icon="👨‍👩‍👧‍👦" color="blue" />
                <StatCard
                    title="Average Attendance (this year)"
                    value={summary.avgAttendance === null ? 'Not marked yet' : `${summary.avgAttendance}%`}
                    icon="✅"
                    color="green"
                    loading={statsLoading}
                />
                <StatCard
                    title="Pending Fees"
                    value={summary.totalBalance === null ? '—' : formatMoney(summary.totalBalance)}
                    icon="💰"
                    color="yellow"
                    loading={statsLoading}
                />
                <StatCard
                    title="Announcements (last 7 days)"
                    value={summary.recentAnnouncements}
                    icon="📢"
                    color="purple"
                    loading={announcementsState === 'loading'}
                />
            </div>

            {/* Children */}
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Your Children</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {children.map((child) => {
                        const s = stats[child.student_id];
                        const attendance = s?.attendance ?? null;
                        return (
                            <div
                                key={child.student_id}
                                data-testid="child-card"
                                className="p-4 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border border-blue-200 dark:border-blue-800 rounded-lg"
                            >
                                <div className="mb-3">
                                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{childName(child)}</h3>
                                    <p className="text-sm text-gray-600 dark:text-gray-400">
                                        {classLabel(child)}{child.roll_no ? ` · Roll no. ${child.roll_no}` : ''}
                                    </p>
                                </div>
                                <div className="space-y-3">
                                    <div>
                                        <div className="flex items-center justify-between">
                                            <span className="text-sm text-gray-700 dark:text-gray-300">Attendance</span>
                                            <span className="font-semibold text-gray-900 dark:text-white" data-testid="child-attendance">
                                                {statsLoading && !s ? '…' : s?.attendanceError ? 'Unavailable' : attendance === null ? 'Not marked yet' : `${attendance}%`}
                                            </span>
                                        </div>
                                        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 mt-1">
                                            <div className="h-2 bg-green-500 rounded-full" style={{ width: `${attendance ?? 0}%` }} />
                                        </div>
                                    </div>
                                    <div className="flex items-center justify-between">
                                        <span className="text-sm text-gray-700 dark:text-gray-300">Fee balance</span>
                                        <span className="font-semibold text-gray-900 dark:text-white" data-testid="child-balance">
                                            {statsLoading && !s ? '…' : s?.feeError ? 'Unavailable' : s?.balance === null || s?.balance === undefined ? '—' : formatMoney(s.balance)}
                                        </span>
                                    </div>
                                </div>
                                <div className="grid grid-cols-2 gap-2 mt-4">
                                    <Button variant="secondary" size="sm" onClick={() => { selectChild(child); navigate('/parent/timetable'); }}>
                                        Timetable
                                    </Button>
                                    <Button variant="primary" size="sm" onClick={() => { selectChild(child); navigate('/parent/fees'); }}>
                                        Fees
                                    </Button>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Today's schedule */}
                <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
                    <div className="flex items-center justify-between gap-3 mb-4">
                        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Today's Schedule</h2>
                        {children.length > 1 && (
                            <select
                                aria-label="Choose child"
                                value={selectedChild?.student_id ?? ''}
                                onChange={(e) => {
                                    const next = children.find((c) => String(c.student_id) === e.target.value);
                                    if (next) selectChild(next);
                                }}
                                className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                            >
                                {children.map((c) => <option key={c.student_id} value={c.student_id}>{childName(c)}</option>)}
                            </select>
                        )}
                    </div>
                    {timetableState === 'loading' ? (
                        <p className="text-sm text-gray-500 dark:text-gray-400">Loading…</p>
                    ) : timetableState === 'error' ? (
                        <p className="text-sm text-red-600 dark:text-red-400">Couldn't load today's timetable.</p>
                    ) : timetable.length === 0 ? (
                        <p className="text-sm text-gray-500 dark:text-gray-400">No classes scheduled today.</p>
                    ) : (
                        <ul className="divide-y divide-gray-100 dark:divide-gray-700" data-testid="today-schedule">
                            {timetable.map((period) => (
                                <li key={`${period.period_number}-${period.start_time}`} className="py-2 flex items-center justify-between gap-3">
                                    <div>
                                        <p className="font-medium text-gray-900 dark:text-white">{period.subject_name}</p>
                                        <p className="text-xs text-gray-500 dark:text-gray-400">{period.teacher_name}{period.room ? ` · Room ${period.room}` : ''}</p>
                                    </div>
                                    <span className="text-sm text-gray-600 dark:text-gray-300 whitespace-nowrap">
                                        {period.start_time}–{period.end_time}
                                    </span>
                                </li>
                            ))}
                        </ul>
                    )}
                </div>

                {/* Recent announcements */}
                <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Recent Announcements</h2>
                    {announcementsState === 'loading' ? (
                        <p className="text-sm text-gray-500 dark:text-gray-400">Loading…</p>
                    ) : announcementsState === 'error' ? (
                        <p className="text-sm text-red-600 dark:text-red-400">Couldn't load announcements.</p>
                    ) : announcements.length === 0 ? (
                        <p className="text-sm text-gray-500 dark:text-gray-400">No announcements yet.</p>
                    ) : (
                        <ul className="space-y-3" data-testid="announcements">
                            {announcements.slice(0, 5).map((a) => (
                                <li key={a.id} className="p-3 rounded-lg bg-gray-50 dark:bg-gray-700/50">
                                    <div className="flex items-start justify-between gap-2">
                                        <p className="font-medium text-gray-900 dark:text-white">{a.title}</p>
                                        <span className="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
                                            {new Date(a.publish_date || a.created_at || '').toLocaleDateString()}
                                        </span>
                                    </div>
                                    {a.description && <p className="mt-1 text-sm text-gray-600 dark:text-gray-300 line-clamp-2">{a.description}</p>}
                                </li>
                            ))}
                        </ul>
                    )}
                </div>
            </div>

            {/* Quick actions: only pages that exist */}
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Quick Actions</h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {quickActions.map((action) => (
                        <QuickActionButton
                            key={action.path}
                            icon={action.icon}
                            label={action.label}
                            variant={action.variant}
                            onClick={() => navigate(action.path)}
                        />
                    ))}
                </div>
            </div>
        </div>
    );
};

export default GuardianDashboard;
