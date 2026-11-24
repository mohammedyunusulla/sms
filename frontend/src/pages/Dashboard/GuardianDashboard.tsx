/**
 * Guardian Dashboard
 * Parent dashboard built only on real data for the parent's linked children:
 * attendance (this academic year), fee balance, today's timetable and recent announcements.
 */

import { FC, useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router';
import { PageHeader, Button } from '../../components';
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

// ---------- stat card: same design as the teacher / student dashboards
// (white card, tinted rounded icon tile with an outline icon, label above the value)
const STAT_TONES = {
    blue: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400',
    green: 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400',
    orange: 'bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400',
    purple: 'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400',
} as const;

const STAT_ICONS = {
    children: 'M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z',
    attendance: 'M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
    fees: 'M21 12a2.25 2.25 0 00-2.25-2.25H15a3 3 0 11-6 0H5.25A2.25 2.25 0 003 12m18 0v6a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 18v-6m18 0V9M3 12V9m18 0a2.25 2.25 0 00-2.25-2.25H5.25A2.25 2.25 0 003 9m18 0V6a2.25 2.25 0 00-2.25-2.25H5.25A2.25 2.25 0 003 6v3',
    announcements: 'M10.34 15.84c-.688-.06-1.386-.09-2.09-.09H7.5a4.5 4.5 0 110-9h.75c.704 0 1.402-.03 2.09-.09m0 9.18c.253.962.584 1.892.985 2.783.247.55.06 1.21-.463 1.511l-.657.38c-.551.318-1.26.117-1.527-.461a20.845 20.845 0 01-1.44-4.282m3.102.069a18.03 18.03 0 01-.59-4.59c0-1.586.205-3.124.59-4.59m0 9.18a23.848 23.848 0 018.835 2.535M10.34 6.66a23.847 23.847 0 008.835-2.535m0 0A23.74 23.74 0 0018.795 3m.38 1.125a23.91 23.91 0 011.014 5.395m-1.014 8.855c-.118.38-.245.754-.38 1.125m.38-1.125a23.91 23.91 0 001.014-5.395m0-3.46c.495.413.811 1.035.811 1.73 0 .695-.316 1.317-.811 1.73m0-3.46a24.347 24.347 0 010 3.46',
} as const;

const ParentStat: FC<{
    label: string;
    value?: string | number;
    icon: keyof typeof STAT_ICONS;
    tone: keyof typeof STAT_TONES;
    loading?: boolean;
}> = ({ label, value, icon, tone, loading = false }) => (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-3">
            <div className={`w-12 h-12 shrink-0 rounded-xl flex items-center justify-center ${STAT_TONES[tone]}`}>
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" d={STAT_ICONS[icon]} />
                </svg>
            </div>
            <div className="min-w-0">
                <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
                {loading ? (
                    <div className="h-7 w-16 bg-gray-200 dark:bg-gray-700 rounded animate-pulse mt-1"></div>
                ) : (
                    <p className="text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
                )}
            </div>
        </div>
    </div>
);

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
                institution_user_id: user.institution_user_id,
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
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    <ParentStat label="Children" icon="children" tone="blue" loading />
                    <ParentStat label="Average Attendance (this year)" icon="attendance" tone="green" loading />
                    <ParentStat label="Pending Fees" icon="fees" tone="orange" loading />
                    <ParentStat label="Announcements (last 7 days)" icon="announcements" tone="purple" loading />
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
                        Your account isn't linked to a student. Please contact the institution's office.
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
                    The institution hasn't set a current academic year yet, so attendance, fees and announcements can't be shown.
                </div>
            )}

            {/* Key statistics */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <ParentStat label="Children" value={children.length} icon="children" tone="blue" />
                <ParentStat
                    label="Average Attendance (this year)"
                    value={summary.avgAttendance === null ? 'Not marked yet' : `${summary.avgAttendance}%`}
                    icon="attendance"
                    tone="green"
                    loading={statsLoading}
                />
                <ParentStat
                    label="Pending Fees"
                    value={summary.totalBalance === null ? '—' : formatMoney(summary.totalBalance)}
                    icon="fees"
                    tone="orange"
                    loading={statsLoading}
                />
                <ParentStat
                    label="Announcements (last 7 days)"
                    value={summary.recentAnnouncements}
                    icon="announcements"
                    tone="purple"
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
