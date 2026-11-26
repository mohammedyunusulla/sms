/**
 * Features the Super Admin switches on per institution.
 * The signed-in user's institution switches arrive with the user (user.features, user.login_roles); a page
 * whose feature is off is hidden from the menu and can't be opened. The server refuses its API calls too
 * (backend app/utils/features.py holds the same list).
 */
import { useAuthStore } from '../stores/authStore';

export type FeatureKey =
    | 'subjects' | 'attendance' | 'staff_attendance' | 'leave' | 'calendar' | 'events' | 'announcements'
    | 'timetable' | 'substitutions' | 'exams' | 'marks' | 'rooms' | 'seating' | 'syllabus' | 'assignments'
    | 'homework' | 'fees' | 'expenses' | 'salary' | 'bus';

// page address -> feature (the longest matching address wins); pages not listed are always on
const PAGE_FEATURES: Array<[string, FeatureKey]> = [
    ['/announcements', 'announcements'],
    ['/timetable', 'timetable'],
    ['/parent/timetable', 'timetable'],
    ['/substitutions', 'substitutions'],
    ['/timetable/substitutions', 'substitutions'],
    ['/attendance', 'attendance'],
    ['/parent/attendance', 'attendance'],
    ['/attendance/staff', 'staff_attendance'],
    ['/attendance/staff-register', 'staff_attendance'],
    ['/leave', 'leave'],
    ['/calendar', 'calendar'],
    ['/holidays', 'calendar'],
    ['/academics/subjects', 'subjects'],
    ['/academics/assign-subjects', 'subjects'],
    ['/academics/my-results', 'marks'],
    ['/academics/marks', 'marks'],
    ['/academics/progress', 'marks'],
    ['/academics/progress-card', 'marks'],
    ['/academics/annual-progress', 'marks'],
    ['/parent/results', 'marks'],
    ['/exams', 'exams'],
    ['/parent/exam-timetable', 'exams'],
    ['/exams/seating', 'seating'],
    ['/rooms', 'rooms'],
    ['/syllabus', 'syllabus'],
    ['/parent/syllabus', 'syllabus'],
    ['/assignments', 'assignments'],
    ['/parent/assignments', 'assignments'],
    ['/homework', 'homework'],
    ['/finance/fee-structure', 'fees'],
    ['/finance/fee-collection', 'fees'],
    ['/finance/defaulters', 'fees'],
    ['/finance/collection-report', 'fees'],
    ['/parent/fees', 'fees'],
    ['/finance/expenses', 'expenses'],
    ['/finance/salary-setup', 'salary'],
    ['/finance/salary-payments', 'salary'],
    ['/bus-scan', 'bus'],
];
const LONGEST_FIRST = [...PAGE_FEATURES].sort((a, b) => b[0].length - a[0].length);
const STAFF_SIDE_ROLES = ['STUDENT', 'PARENT', 'SUPER_ADMIN'];

/** The feature a page belongs to, or undefined when it is always on. */
export const featureForPath = (path: string, role?: string | null): FeatureKey | undefined => {
    const clean = path.length > 1 ? path.replace(/\/+$/, '') : path;
    // "My Attendance" is the student's own attendance, or a staff member's own staff attendance
    if (clean === '/attendance/my') return role && !STAFF_SIDE_ROLES.includes(role) ? 'staff_attendance' : 'attendance';
    return LONGEST_FIRST.find(([prefix]) => clean === prefix || clean.startsWith(`${prefix}/`))?.[1];
};

/**
 * Is this feature on for the signed-in user's institution?
 * No list (Super Admin, or a session from before this change) means nothing is hidden.
 */
export const hasFeature = (features: string[] | undefined | null, feature: FeatureKey): boolean =>
    !Array.isArray(features) || features.includes(feature);

/** True when the page belongs to a feature that is switched off. */
export const isPageSwitchedOff = (path: string, features: string[] | undefined | null, role?: string | null): boolean => {
    const feature = featureForPath(path, role);
    return !!feature && !hasFeature(features, feature);
};

/**
 * For services and other non-component code: is the feature on for the signed-in user's institution?
 * (Reads the stored user, which the store keeps up to date.)
 */
export const featureOn = (feature: FeatureKey): boolean => hasFeature(useAuthStore.getState().user?.features, feature);

/** For components: is the feature on? */
export const useFeature = (feature: FeatureKey): boolean => hasFeature(useAuthStore((s) => s.user?.features), feature);

/**
 * Does a new person of this role get a login (so the form asks for a password)?
 * The Institution Admin always can sign in; other roles follow the institution's sign-in switches.
 */
export const roleGetsLogin = (loginRoles: string[] | undefined | null, role: string): boolean => {
    const code = role.toUpperCase();
    if (code === 'INSTITUTION_ADMIN' || code === 'SUPER_ADMIN') return true;
    return !Array.isArray(loginRoles) || loginRoles.includes(code);
};
export const useRoleGetsLogin = (role: string): boolean => roleGetsLogin(useAuthStore((s) => s.user?.login_roles), role);

export const FEATURE_LABELS: Record<FeatureKey, string> = {
    subjects: 'Subjects', attendance: 'Attendance', staff_attendance: 'Staff Attendance', leave: 'Leave',
    calendar: 'Calendar & Holidays', events: 'Events', announcements: 'Announcements', timetable: 'Timetable',
    substitutions: 'Substitutions', exams: 'Exams', marks: 'Marks & Results', rooms: 'Rooms',
    seating: 'Seating Arrangement', syllabus: 'Syllabus', assignments: 'Assignments', homework: 'Homework AI',
    fees: 'Fees', expenses: 'Expenses', salary: 'Salary', bus: 'Bus Management',
};
