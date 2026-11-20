/**
 * Central Permission Configuration
 * Single source of truth for all permission keys, route mappings, and sidebar mappings.
 */

// ──────────────────────────────────────────────
// Permission Enum — all granular permission keys
// ──────────────────────────────────────────────
export enum Permission {
  // User Management
  VIEW_USERS = 'view_users',
  MANAGE_USERS = 'manage_users',
  DELETE_USERS = 'delete_users',

  // Teachers
  VIEW_TEACHERS = 'view_teachers',
  MANAGE_TEACHERS = 'manage_teachers',
  DELETE_TEACHERS = 'delete_teachers',

  // Students
  VIEW_STUDENTS = 'view_students',
  MANAGE_STUDENTS = 'manage_students',
  DELETE_STUDENTS = 'delete_students',

  // Roles
  MANAGE_ROLES = 'manage_roles',

  // Classes
  VIEW_CLASSES = 'view_classes',
  MANAGE_CLASSES = 'manage_classes',

  // Attendance
  VIEW_ATTENDANCE = 'view_attendance',
  MANAGE_ATTENDANCE = 'manage_attendance',

  // Announcements
  VIEW_ANNOUNCEMENTS = 'view_announcements',
  MANAGE_ANNOUNCEMENTS = 'manage_announcements',

  // Timetable
  VIEW_TIMETABLE = 'view_timetable',
  MANAGE_TIMETABLE = 'manage_timetable',
  /** Student-facing: view own daily timetable */
  VIEW_MY_TIMETABLE = 'view_my_timetable',

  // Exams
  VIEW_EXAMS = 'view_exams',
  MANAGE_EXAMS = 'manage_exams',

  // Marks / Academics
  VIEW_MARKS = 'view_marks',
  MANAGE_MARKS = 'manage_marks',

  // Fees
  VIEW_FEES = 'view_fees',
  MANAGE_FEES = 'manage_fees',

  // Expenses
  VIEW_EXPENSES = 'view_expenses',
  MANAGE_EXPENSES = 'manage_expenses',

  // Syllabus
  VIEW_SYLLABUS_AND_PROGRESS = 'view_syllabus_and_progress',
  MANAGE_SYLLABUS = 'manage_syllabus',

  // Assignments
  VIEW_ASSIGNMENTS = 'view_assignments',
  MANAGE_ASSIGNMENTS = 'manage_assignments',
  /** Parent-facing: view assignments for the parent's linked children */
  VIEW_CHILD_ASSIGNMENTS = 'view_child_assignments',
  /** Parent-facing: view timetable for the parent's linked children */
  VIEW_CHILD_TIMETABLE = 'view_child_timetable',
  /** Parent-facing: view fee summary for the parent's linked children */
  VIEW_CHILD_FEES = 'view_child_fees',
  /** Parent-facing: view syllabus progress for the parent's linked children */
  VIEW_CHILD_SYLLABUS = 'view_child_syllabus',

  // Bus Scan
  VIEW_BUS_SCAN = 'view_bus_scan',
  MANAGE_BUS_SCAN = 'manage_bus_scan',
  // added with server-side permission checks (QA A15)
  MANAGE_ACADEMIC_YEARS = 'manage_academic_years',
  MANAGE_ROOMS = 'manage_rooms',
  MANAGE_SALARIES = 'manage_salaries',
  MANAGE_FEE_SETTINGS = 'manage_fee_settings',
}

// ──────────────────────────────────────────────
// Route → Permission Map
// ──────────────────────────────────────────────
/**
 * Pages a role never sees, even when its permissions would show them, because the server doesn't serve
 * that role there. A Clerk (fee counter) has view_students / view_classes but no access to parents or rooms.
 */
export const ROLE_HIDDEN_PATHS: Record<string, string[]> = {
  CLERK: ['/parents', '/rooms'],
};

/** True if this path (or a page under it, e.g. /parents/new) is hidden for the role. */
export const isPathHiddenForRole = (role: string | undefined | null, path: string): boolean =>
  !!role && (ROLE_HIDDEN_PATHS[role] || []).some((p) => path === p || path.startsWith(`${p}/`));

export interface RoutePermissionConfig {
  permission?: Permission;
  /** Access granted if user has ANY of these permissions (OR logic) */
  anyPermission?: Permission[];
  superAdminOnly?: boolean;
}

/**
 * Maps route paths to required permissions.
 * Routes not listed here are accessible to any authenticated user.
 * `superAdminOnly: true` means only SUPER_ADMIN can access (School Management).
 */
export const ROUTE_PERMISSION_MAP: Record<string, RoutePermissionConfig> = {
  // School Management — super admin only
  '/schools': { superAdminOnly: true },
  '/schools/new': { superAdminOnly: true },
  '/schools/:id/edit': { superAdminOnly: true },
  '/schools/:id': { superAdminOnly: true },
  '/school-admins': { superAdminOnly: true },
  '/system-admins': { superAdminOnly: true },

  // User Management
  '/users': { permission: Permission.VIEW_USERS },
  '/users/new': { permission: Permission.MANAGE_USERS },
  '/users/:id/edit': { permission: Permission.MANAGE_USERS },
  '/users/:id': { permission: Permission.VIEW_USERS },

  // Teachers
  '/teachers': { permission: Permission.VIEW_TEACHERS },
  '/teachers/new': { permission: Permission.MANAGE_TEACHERS },
  '/teachers/:id/edit': { permission: Permission.MANAGE_TEACHERS },

  // Students
  '/students': { permission: Permission.VIEW_STUDENTS },
  '/students/new': { permission: Permission.MANAGE_STUDENTS },
  '/students/:id/edit': { permission: Permission.MANAGE_STUDENTS },

  // Parents
  '/parents': { permission: Permission.VIEW_STUDENTS },
  '/parents/new': { permission: Permission.MANAGE_STUDENTS },
  '/parents/:id/edit': { permission: Permission.MANAGE_STUDENTS },

  // Roles & Permissions
  '/roles': { permission: Permission.MANAGE_ROLES },
  '/roles/new': { permission: Permission.MANAGE_ROLES },
  '/roles/:id/edit': { permission: Permission.MANAGE_ROLES },

  // Class Management
  '/classes': { permission: Permission.VIEW_CLASSES },
  '/classes/new': { permission: Permission.MANAGE_CLASSES },
  '/classes/:id/edit': { permission: Permission.MANAGE_CLASSES },
  '/classes/:id': { permission: Permission.VIEW_CLASSES },

  // Room Management
  '/rooms': { permission: Permission.VIEW_CLASSES },
  '/rooms/new': { permission: Permission.MANAGE_ROOMS },
  '/rooms/:id/edit': { permission: Permission.MANAGE_ROOMS },

  // Attendance
  '/attendance/mark': { permission: Permission.MANAGE_ATTENDANCE },
  '/attendance/report': { permission: Permission.VIEW_ATTENDANCE },

  // Announcements
  '/announcements': { permission: Permission.VIEW_ANNOUNCEMENTS },
  '/announcements/new': { permission: Permission.MANAGE_ANNOUNCEMENTS },
  '/announcements/:id/edit': { permission: Permission.MANAGE_ANNOUNCEMENTS },

  // Timetable
  '/timetable': { permission: Permission.VIEW_TIMETABLE },
  '/timetable/new': { permission: Permission.MANAGE_TIMETABLE },
  '/timetable/:id': { permission: Permission.VIEW_TIMETABLE },
  '/timetable/:id/edit': { permission: Permission.MANAGE_TIMETABLE },
  '/timetable/my-timetable': { permission: Permission.VIEW_MY_TIMETABLE },

  // Exam Management
  '/exams': { permission: Permission.VIEW_EXAMS },
  '/exams/new': { permission: Permission.MANAGE_EXAMS },
  '/exams/:id/edit': { permission: Permission.MANAGE_EXAMS },
  '/exams/:id': { permission: Permission.VIEW_EXAMS },
  '/exams/configs': { permission: Permission.MANAGE_EXAMS },
  '/exams/timetable': { permission: Permission.MANAGE_EXAMS },
  '/exams/seating': { permission: Permission.MANAGE_EXAMS },
  '/exams/my-timetable': { permission: Permission.VIEW_EXAMS },
  '/exams/invigilator-schedule': { permission: Permission.MANAGE_EXAMS },

  // Academics
  '/academics/subjects': { permission: Permission.VIEW_CLASSES },
  '/academics/subjects/new': { permission: Permission.MANAGE_CLASSES },
  '/academics/subjects/:id/edit': { permission: Permission.MANAGE_CLASSES },
  '/academics/assign-subjects': { permission: Permission.MANAGE_TEACHERS },
  '/academics/marks/entry': { permission: Permission.MANAGE_MARKS },
  '/academics/progress/class': { permission: Permission.VIEW_MARKS },
  '/academics/progress-card/:studentId/:examId': { permission: Permission.VIEW_MARKS },

  // Finance
  '/finance/fee-structure': { permission: Permission.VIEW_FEES },
  '/finance/fee-structure/create': { permission: Permission.MANAGE_FEE_SETTINGS },
  '/finance/fee-structure/edit/:classId': { permission: Permission.MANAGE_FEE_SETTINGS },
  '/finance/fee-collection': { permission: Permission.MANAGE_FEES },
  '/finance/expenses': { permission: Permission.VIEW_EXPENSES },
  // Salaries are staff expenses, not fee collection (a fee clerk with manage_fees must not see them)
  '/finance/salary-setup': { permission: Permission.MANAGE_SALARIES },
  '/finance/salary-payments': { permission: Permission.MANAGE_SALARIES },
  '/finance/defaulters': { permission: Permission.MANAGE_FEES },
  '/finance/collection-report': { permission: Permission.MANAGE_FEES },

  // Assignments
  '/assignments': { permission: Permission.MANAGE_ASSIGNMENTS },
  '/assignments/:id/review': { permission: Permission.MANAGE_ASSIGNMENTS },
  '/assignments/my-assignments': { permission: Permission.VIEW_ASSIGNMENTS },
  '/parent/assignments': { permission: Permission.VIEW_CHILD_ASSIGNMENTS },
  '/parent/timetable': { permission: Permission.VIEW_CHILD_TIMETABLE },
  '/parent/fees': { permission: Permission.VIEW_CHILD_FEES },
  '/parent/syllabus': { permission: Permission.VIEW_CHILD_SYLLABUS },
  '/parent/syllabus/:id': { permission: Permission.VIEW_CHILD_SYLLABUS },
  '/homework': { anyPermission: [Permission.MANAGE_ASSIGNMENTS, Permission.VIEW_ASSIGNMENTS] },
  '/homework/teacher': { permission: Permission.MANAGE_ASSIGNMENTS },
  '/homework/student': { permission: Permission.VIEW_ASSIGNMENTS },

  // Bus Scan
  '/bus-scan': { permission: Permission.MANAGE_BUS_SCAN },
  '/bus-scan/scan': { permission: Permission.MANAGE_BUS_SCAN },
  '/bus-scan/report': { permission: Permission.VIEW_BUS_SCAN },

  // Syllabus
  '/syllabus': { permission: Permission.MANAGE_SYLLABUS },
  '/syllabus/analytics': { permission: Permission.MANAGE_SYLLABUS },
  '/syllabus/my-progress': { permission: Permission.VIEW_SYLLABUS_AND_PROGRESS },
  '/syllabus/my-progress/:id': { permission: Permission.VIEW_SYLLABUS_AND_PROGRESS },
  '/syllabus/:id': { permission: Permission.VIEW_SYLLABUS_AND_PROGRESS },
};

// ──────────────────────────────────────────────
// Sidebar → Permission Map
// ──────────────────────────────────────────────
export interface SidebarGroupPermissionConfig {
  /** Group is visible if user has ANY of these permissions */
  groupPermissions: Permission[];
  /** If true, group is only visible to SUPER_ADMIN (overrides groupPermissions) */
  superAdminOnly?: boolean;
  /** Maps sub-item paths to the permission required to show that item */
  itemPermissions: Record<string, Permission>;
  /** Paths to hide for full-access roles (SCHOOL_ADMIN) — e.g. role-specific personal views */
  excludeFromFullAccess?: string[];
  /** Hide a path if the user HAS a given permission (inverse check).
   *  Use case: hide "My Assignments" from users who have manage_assignments. */
  excludeIfHasPermission?: Record<string, Permission>;
  /** Shown to exactly these roles, without a permission (e.g. a student's own attendance) */
  roles?: string[];
}

export const SIDEBAR_PERMISSION_MAP: Record<string, SidebarGroupPermissionConfig> = {
  'School Management': {
    groupPermissions: [],
    superAdminOnly: true,
    itemPermissions: {
      '/schools': Permission.VIEW_USERS, // placeholder — superAdminOnly overrides
      '/schools/new': Permission.MANAGE_USERS,
      '/school-admins': Permission.VIEW_USERS,
      '/system-admins': Permission.VIEW_USERS,
    },
  },
  'User Management': {
    groupPermissions: [
      Permission.VIEW_USERS,
      Permission.VIEW_TEACHERS,
      Permission.VIEW_STUDENTS,
      Permission.MANAGE_ROLES,
    ],
    itemPermissions: {
      '/users': Permission.VIEW_USERS,
      '/users/new': Permission.MANAGE_USERS,
      '/teachers': Permission.VIEW_TEACHERS,
      '/students': Permission.VIEW_STUDENTS,
      '/parents': Permission.VIEW_STUDENTS,
      '/roles': Permission.MANAGE_ROLES,
    },
  },
  'Class Management': {
    groupPermissions: [Permission.VIEW_CLASSES],
    itemPermissions: {
      '/classes': Permission.VIEW_CLASSES,
      '/classes/new': Permission.MANAGE_CLASSES,
      '/rooms': Permission.VIEW_CLASSES,
    },
  },
  'Attendance': {
    groupPermissions: [Permission.VIEW_ATTENDANCE, Permission.MANAGE_ATTENDANCE],
    itemPermissions: {
      '/attendance/mark': Permission.MANAGE_ATTENDANCE,
      '/attendance/report': Permission.VIEW_ATTENDANCE,
    },
  },
  'Announcements': {
    groupPermissions: [Permission.VIEW_ANNOUNCEMENTS],
    itemPermissions: {
      '/announcements': Permission.VIEW_ANNOUNCEMENTS,
      '/announcements/new': Permission.MANAGE_ANNOUNCEMENTS,
    },
  },
  'Timetable': {
    groupPermissions: [Permission.VIEW_TIMETABLE],
    itemPermissions: {
      '/timetable': Permission.VIEW_TIMETABLE,
    },
    excludeIfHasPermission: {
      '/timetable': Permission.VIEW_MY_TIMETABLE,
    },
  },
  // Own / child attendance: every student and parent (no permission, by choice)
  'My Attendance': { groupPermissions: [], itemPermissions: {}, roles: ['STUDENT'] },
  "My Child's Attendance": { groupPermissions: [], itemPermissions: {}, roles: ['PARENT'] },
  // Published exam results: every student and parent (no permission, by choice)
  'My Results': { groupPermissions: [], itemPermissions: {}, roles: ['STUDENT'] },
  "My Child's Results": { groupPermissions: [], itemPermissions: {}, roles: ['PARENT'] },
  'My Timetable': {
    groupPermissions: [Permission.VIEW_MY_TIMETABLE],
    itemPermissions: {
      '/timetable/my-timetable': Permission.VIEW_MY_TIMETABLE,
    },
    excludeFromFullAccess: ['/timetable/my-timetable'],
  },
  'Exam Management': {
    groupPermissions: [Permission.MANAGE_EXAMS],
    itemPermissions: {
      '/exams': Permission.VIEW_EXAMS,
      '/exams/new': Permission.MANAGE_EXAMS,
      '/exams/configs': Permission.MANAGE_EXAMS,
      '/exams/timetable': Permission.MANAGE_EXAMS,
      '/exams/seating': Permission.MANAGE_EXAMS,
    },
  },
  'My Exam Timetable': {
    groupPermissions: [Permission.VIEW_EXAMS],
    itemPermissions: {
      '/exams/my-timetable': Permission.VIEW_EXAMS,
    },
    excludeIfHasPermission: {
      '/exams/my-timetable': Permission.MANAGE_EXAMS,
    },
    excludeFromFullAccess: ['/exams/my-timetable'],
  },
  'My Invigilator Schedule': {
    groupPermissions: [Permission.MANAGE_EXAMS],
    itemPermissions: {
      '/exams/invigilator-schedule': Permission.MANAGE_EXAMS,
    },
    excludeFromFullAccess: ['/exams/invigilator-schedule'],
  },
  'Academics Management': {
    groupPermissions: [Permission.VIEW_EXAMS, Permission.VIEW_MARKS, Permission.MANAGE_MARKS, Permission.MANAGE_TEACHERS],
    itemPermissions: {
      '/academics/subjects': Permission.VIEW_CLASSES,
      '/academics/assign-subjects': Permission.MANAGE_TEACHERS,
      '/academics/marks/entry': Permission.MANAGE_MARKS,
      '/academics/progress/class': Permission.VIEW_MARKS,
    },
  },
  'Assignments': {
    groupPermissions: [Permission.MANAGE_ASSIGNMENTS],
    itemPermissions: {
      '/assignments': Permission.MANAGE_ASSIGNMENTS,
    },
  },
  'My Assignments': {
    groupPermissions: [Permission.VIEW_ASSIGNMENTS],
    itemPermissions: {
      '/assignments/my-assignments': Permission.VIEW_ASSIGNMENTS,
    },
    excludeFromFullAccess: ['/assignments/my-assignments'],
    excludeIfHasPermission: {
      // Hide for users who have manage_assignments (teachers/admins).
      '/assignments/my-assignments': Permission.MANAGE_ASSIGNMENTS,
    },
  },
  "My Child's Assignments": {
    groupPermissions: [Permission.VIEW_CHILD_ASSIGNMENTS],
    itemPermissions: {
      '/parent/assignments': Permission.VIEW_CHILD_ASSIGNMENTS,
    },
    excludeFromFullAccess: ['/parent/assignments'],
  },
  "My Child's Timetable": {
    groupPermissions: [Permission.VIEW_CHILD_TIMETABLE],
    itemPermissions: {
      '/parent/timetable': Permission.VIEW_CHILD_TIMETABLE,
    },
    excludeFromFullAccess: ['/parent/timetable'],
  },
  "My Child's Fees": {
    groupPermissions: [Permission.VIEW_CHILD_FEES],
    itemPermissions: {
      '/parent/fees': Permission.VIEW_CHILD_FEES,
    },
    excludeFromFullAccess: ['/parent/fees'],
  },
  "My Child's Syllabus": {
    groupPermissions: [Permission.VIEW_CHILD_SYLLABUS],
    itemPermissions: {
      '/parent/syllabus': Permission.VIEW_CHILD_SYLLABUS,
    },
    excludeFromFullAccess: ['/parent/syllabus'],
  },
  'Homework AI': {
    groupPermissions: [Permission.MANAGE_ASSIGNMENTS, Permission.VIEW_ASSIGNMENTS],
    itemPermissions: {
      '/homework': Permission.VIEW_ASSIGNMENTS,
    },
  },
  'Syllabus Management': {
    groupPermissions: [Permission.MANAGE_SYLLABUS, Permission.VIEW_SYLLABUS_AND_PROGRESS],
    itemPermissions: {
      '/syllabus': Permission.MANAGE_SYLLABUS,
      '/syllabus/analytics': Permission.MANAGE_SYLLABUS,
      '/syllabus/my-progress': Permission.VIEW_SYLLABUS_AND_PROGRESS,
    },
    excludeFromFullAccess: ['/syllabus/my-progress'],
  },
  'Bus Management': {
    groupPermissions: [Permission.VIEW_BUS_SCAN, Permission.MANAGE_BUS_SCAN],
    itemPermissions: {
      '/bus-scan': Permission.MANAGE_BUS_SCAN,
      '/bus-scan/scan': Permission.MANAGE_BUS_SCAN,
      '/bus-scan/report': Permission.VIEW_BUS_SCAN,
    },
  },
  'Finance Management': {
    groupPermissions: [Permission.VIEW_FEES, Permission.VIEW_EXPENSES, Permission.MANAGE_SALARIES],
    itemPermissions: {
      '/finance/fee-structure': Permission.VIEW_FEES,
      '/finance/fee-collection': Permission.MANAGE_FEES,
      '/finance/expenses': Permission.VIEW_EXPENSES,
      '/finance/salary-setup': Permission.MANAGE_SALARIES,
      '/finance/salary-payments': Permission.MANAGE_SALARIES,
      '/finance/defaulters': Permission.MANAGE_FEES,
      '/finance/collection-report': Permission.MANAGE_FEES,
    },
  },
};
