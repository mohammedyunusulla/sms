import { FC, useCallback, useEffect, useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import { Skeleton } from '../../components';
import { timetableService } from '../../services/modules/timetableService';
import dashboardService from '../../services/dashboardService';
import { getInstitutionId } from '../../services/api/client';

export interface Period {
    id?: number | string;
    subject_name?: string;
    teacher_name?: string;
    start_time?: string;
    end_time?: string;
    room_number?: string;
    [key: string]: any;
}

interface DailyTimetableViewProps {
    /** Backend "student_user_id" — for parents this is selectedChild.student_id; for students this is user.institution_user_id */
    studentId?: number | undefined;
    /** For a teacher: their own institution_user_id. Shows the classes they teach that day instead of a section's day. */
    teacherId?: number | undefined;
}

const DAY_NAMES_SHORT = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

function formatDate(date: Date): string {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
}

function getWeekDays(referenceDate: Date): Date[] {
    const day = referenceDate.getDay();
    const monday = new Date(referenceDate);
    monday.setDate(referenceDate.getDate() - ((day === 0 ? 7 : day) - 1));
    const days: Date[] = [];
    for (let i = 0; i < 6; i++) {
        const d = new Date(monday);
        d.setDate(monday.getDate() + i);
        days.push(d);
    }
    return days;
}

function parseTimeToMinutes(timeStr?: string): number | null {
    if (!timeStr) return null;
    const parts = timeStr.split(':');
    return parseInt(parts[0], 10) * 60 + parseInt(parts[1], 10);
}

function formatTimeDisplay(timeStr?: string): string {
    if (!timeStr) return '';
    const [h, m] = timeStr.split(':');
    const hour = parseInt(h, 10);
    const ampm = hour >= 12 ? 'PM' : 'AM';
    const h12 = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
    return `${String(h12).padStart(2, '0')}:${m} ${ampm}`;
}

type PeriodStatus = 'completed' | 'ongoing' | 'next' | 'upcoming';

function getStatusForToday(start?: string, end?: string): Exclude<PeriodStatus, 'next'> {
    const now = new Date();
    const nowMinutes = now.getHours() * 60 + now.getMinutes();
    const s = parseTimeToMinutes(start);
    const e = parseTimeToMinutes(end);
    if (s === null || e === null) return 'upcoming';
    if (nowMinutes >= e) return 'completed';
    if (nowMinutes >= s && nowMinutes < e) return 'ongoing';
    return 'upcoming';
}

function isSameDay(a: Date, b: Date): boolean {
    return (
        a.getDate() === b.getDate() &&
        a.getMonth() === b.getMonth() &&
        a.getFullYear() === b.getFullYear()
    );
}

function isPastDate(date: Date): boolean {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const d = new Date(date);
    d.setHours(0, 0, 0, 0);
    return d < today;
}

const statusStyles: Record<PeriodStatus, { dot: string; badge: string; badgeText: string; label: string }> = {
    completed: {
        dot: 'bg-green-500 border-white text-white',
        badge: 'bg-green-100 dark:bg-green-900/30',
        badgeText: 'text-green-700 dark:text-green-400',
        label: 'Completed',
    },
    ongoing: {
        dot: 'bg-indigo-600 border-white text-white animate-pulse',
        badge: 'bg-indigo-100 dark:bg-indigo-900/30',
        badgeText: 'text-indigo-700 dark:text-indigo-400',
        label: 'Now',
    },
    next: {
        dot: 'bg-white border-indigo-400 text-indigo-600',
        badge: 'bg-indigo-50 dark:bg-indigo-900/20',
        badgeText: 'text-indigo-700 dark:text-indigo-300',
        label: 'Next Up',
    },
    upcoming: {
        dot: 'bg-white border-gray-300 dark:border-gray-600',
        badge: 'bg-gray-100 dark:bg-gray-700',
        badgeText: 'text-gray-600 dark:text-gray-300',
        label: 'Upcoming',
    },
};

const DailyTimetableView: FC<DailyTimetableViewProps> = ({ studentId, teacherId }) => {
    const [selectedDate, setSelectedDate] = useState(new Date());
    const [periods, setPeriods] = useState<Period[]>([]);
    const [loading, setLoading] = useState(false);

    const weekDays = useMemo(
        () => getWeekDays(selectedDate),
        // eslint-disable-next-line react-hooks/exhaustive-deps
        [selectedDate.getFullYear(), selectedDate.getMonth(), selectedDate.getDate()]
    );

    const fetchTimetable = useCallback(async () => {
        if (!studentId && !teacherId) {
            setPeriods([]);
            return;
        }
        setLoading(true);
        try {
            const dateStr = formatDate(selectedDate);
            if (teacherId) {
                // A teacher's own day: the classes they teach (the page used to call the student view with the
                // teacher's id, which always failed)
                const rows = await dashboardService.getTeacherDayTimetable(getInstitutionId() || '', teacherId, dateStr);
                setPeriods((rows || []).map((r) => ({
                    ...r,
                    class_label: [r.class_name, r.section_name && `Section ${r.section_name}`].filter(Boolean).join(' · '),
                    room_number: r.room,
                })));
            } else {
                const data = await timetableService.getStudentDailyTimetable(studentId!, dateStr);
                // the API sends `room`; the card reads room_number (so rooms were never shown)
                setPeriods(Array.isArray(data) ? data.map((p) => ({ ...p, room_number: p.room_number ?? p.room })) : []);
            }
        } catch (err: any) {
            toast.error(err?.message || 'Failed to load timetable');
            setPeriods([]);
        } finally {
            setLoading(false);
        }
    }, [studentId, teacherId, selectedDate]);

    useEffect(() => {
        fetchTimetable();
    }, [fetchTimetable]);

    const today = new Date();
    const isTodaySelected = isSameDay(selectedDate, today);
    const isPast = isPastDate(selectedDate);

    const firstNextUpIndex = useMemo(() => {
        if (!isTodaySelected) return -1;
        for (let i = 0; i < periods.length; i++) {
            if (getStatusForToday(periods[i].start_time, periods[i].end_time) === 'upcoming') return i;
        }
        return -1;
    }, [periods, isTodaySelected]);

    return (
        <div className="space-y-6">
            {/* Week day strip */}
            <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
                <div className="grid grid-cols-6 gap-2">
                    {weekDays.map((day) => {
                        const isSelected = isSameDay(day, selectedDate);
                        const isTodayDay = isSameDay(day, today);
                        return (
                            <button
                                key={day.toISOString()}
                                onClick={() => setSelectedDate(new Date(day))}
                                className={`flex flex-col items-center justify-center py-3 rounded-xl transition-all ${
                                    isSelected
                                        ? 'bg-indigo-600 text-white shadow-md shadow-indigo-200 dark:shadow-indigo-900/30'
                                        : 'bg-gray-50 dark:bg-gray-700/40 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                                }`}
                            >
                                <span className={`text-xs font-semibold ${isSelected ? 'text-white/80' : 'text-gray-500 dark:text-gray-400'}`}>
                                    {DAY_NAMES_SHORT[day.getDay()]}
                                </span>
                                <span className={`text-xl font-bold mt-0.5 ${isSelected ? 'text-white' : 'text-gray-800 dark:text-white'}`}>
                                    {day.getDate()}
                                </span>
                                {isTodayDay && (
                                    <span
                                        className={`w-1.5 h-1.5 rounded-full mt-1 ${
                                            isSelected ? 'bg-white' : 'bg-indigo-600 dark:bg-indigo-400'
                                        }`}
                                    />
                                )}
                            </button>
                        );
                    })}
                </div>
            </div>

            {/* Timeline */}
            {loading ? (
                <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
                    <div className="relative ml-3 pl-8 border-l-2 border-gray-200 dark:border-gray-700">
                        {Array.from({ length: 4 }).map((_, i) => (
                            <div key={i} className="relative pb-6 last:pb-0">
                                <div className="absolute -left-[42px] top-1.5 w-5 h-5 rounded-full border-[3px] border-white dark:border-gray-800 bg-gray-200 dark:bg-gray-700" />
                                <div className="rounded-xl p-4 border border-gray-200 dark:border-gray-700">
                                    <div className="flex items-start justify-between gap-3">
                                        <div className="flex-1">
                                            <Skeleton className="h-4 w-20 rounded-full mb-2" />
                                            <Skeleton className="h-5 w-40 mb-2" />
                                            <Skeleton className="h-3 w-28" />
                                        </div>
                                        <Skeleton className="h-3 w-24" />
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            ) : periods.length === 0 ? (
                <div className="bg-white dark:bg-gray-800 p-8 rounded-lg border border-gray-200 dark:border-gray-700 text-center">
                    <p className="text-gray-500 dark:text-gray-400">No classes scheduled for this day.</p>
                </div>
            ) : (
                <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
                    <div className="relative ml-3 pl-8 border-l-2 border-gray-200 dark:border-gray-700">
                        {periods.map((period, index) => {
                            let status: PeriodStatus;
                            if (isPast) {
                                status = 'completed';
                            } else if (isTodaySelected) {
                                const s = getStatusForToday(period.start_time, period.end_time);
                                status = s === 'upcoming' && index === firstNextUpIndex ? 'next' : s;
                            } else {
                                status = 'upcoming';
                            }

                            const styles = statusStyles[status];
                            const isOngoing = status === 'ongoing';

                            return (
                                <div key={period.id ?? index} className="relative pb-6 last:pb-0">
                                    <div
                                        className={`absolute -left-[42px] top-1.5 w-5 h-5 rounded-full border-[3px] flex items-center justify-center text-[10px] font-bold ${styles.dot}`}
                                    >
                                        {status === 'completed' && '✓'}
                                    </div>

                                    <div
                                        className={`rounded-xl p-4 border transition-shadow ${
                                            isOngoing
                                                ? 'bg-indigo-600 text-white border-indigo-700 shadow-md shadow-indigo-200 dark:shadow-indigo-900/40'
                                                : status === 'completed'
                                                ? 'bg-gray-50 dark:bg-gray-700/30 border-gray-200 dark:border-gray-700 opacity-70'
                                                : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700'
                                        }`}
                                    >
                                        <div className="flex items-start justify-between gap-3 flex-wrap">
                                            <div className="min-w-0">
                                                <div className="mb-1">
                                                    <span
                                                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                                                            isOngoing
                                                                ? 'bg-white/20 text-white'
                                                                : `${styles.badge} ${styles.badgeText}`
                                                        }`}
                                                    >
                                                        {isOngoing && (
                                                            <span className="w-1.5 h-1.5 bg-white rounded-full mr-1.5" />
                                                        )}
                                                        {styles.label}
                                                    </span>
                                                </div>
                                                <h4
                                                    className={`text-base font-bold ${
                                                        isOngoing ? 'text-white' : 'text-gray-900 dark:text-white'
                                                    }`}
                                                >
                                                    {period.subject_name || 'Untitled period'}
                                                </h4>
                                                {period.class_label && (
                                                    <p
                                                        className={`text-xs mt-0.5 ${
                                                            isOngoing ? 'text-white/80' : 'text-gray-500 dark:text-gray-400'
                                                        }`}
                                                    >
                                                        🏫 {period.class_label}
                                                    </p>
                                                )}
                                                {period.teacher_name && !period.substitute_name && (
                                                    <p
                                                        className={`text-xs mt-0.5 ${
                                                            isOngoing ? 'text-white/80' : 'text-gray-500 dark:text-gray-400'
                                                        }`}
                                                    >
                                                        👤 {period.teacher_name}
                                                    </p>
                                                )}
                                                {/* substitutions: the student's substitute, the teacher's cover duty, or who covers the teacher */}
                                                {period.substitute_name && (
                                                    <p data-testid="substitute-line" className={`text-xs mt-0.5 font-medium ${isOngoing ? 'text-white' : 'text-amber-700 dark:text-amber-400'}`}>
                                                        🔁 Substitute: {period.substitute_name}
                                                    </p>
                                                )}
                                                {period.is_substitution && (
                                                    <p data-testid="substitute-line" className={`text-xs mt-0.5 font-medium ${isOngoing ? 'text-white' : 'text-amber-700 dark:text-amber-400'}`}>
                                                        🔁 Substitution · for {period.substitute_for}
                                                    </p>
                                                )}
                                                {period.covered_by && (
                                                    <p data-testid="substitute-line" className={`text-xs mt-0.5 ${isOngoing ? 'text-white/80' : 'text-gray-500 dark:text-gray-400'}`}>
                                                        Covered by {period.covered_by}
                                                    </p>
                                                )}
                                            </div>
                                            <div
                                                className={`text-xs font-medium whitespace-nowrap ${
                                                    isOngoing ? 'text-white/90' : 'text-gray-600 dark:text-gray-300'
                                                }`}
                                            >
                                                ⏱ {formatTimeDisplay(period.start_time)} – {formatTimeDisplay(period.end_time)}
                                            </div>
                                        </div>
                                        {period.room_number && (
                                            <p
                                                className={`text-xs mt-2 ${
                                                    isOngoing ? 'text-white/80' : 'text-gray-500 dark:text-gray-400'
                                                }`}
                                            >
                                                Room {period.room_number}
                                            </p>
                                        )}
                                    </div>
                                </div>
                            );
                        })}

                        <div className="relative">
                            <div className="absolute -left-[39px] top-1 w-3 h-3 rounded-full bg-gray-300 dark:bg-gray-600" />
                            <p className="text-sm text-gray-400 dark:text-gray-500 italic pl-1">
                                No further classes scheduled.
                            </p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default DailyTimetableView;

// Helpers exported for callers (e.g. dashboards) that want consistent formatting
export { formatDate, formatTimeDisplay, parseTimeToMinutes };
