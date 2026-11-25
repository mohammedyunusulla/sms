/**
 * "What is this page" help, shown by the (i) button beside the page title (components/common/PageHeader.tsx).
 * Keyed by page address. Keep each one short: one line, 2-3 points, one example. No emojis.
 * A function receives the user's role, for pages different roles use differently.
 */
export interface PageHelp {
    lead: string;
    points: string[];
    example: string;
}

type HelpFor = PageHelp | ((role: string | undefined) => PageHelp);

const ADMIN_ROLES = ['INSTITUTION_ADMIN', 'PRINCIPAL'];

const PAGE_HELP: Record<string, HelpFor> = {
    '/calendar': (role) => ({
        lead: 'Holidays, events, exams and leave in one place.',
        points: [
            'Tap a day to see everything on it.',
            'Use the chips at the top to show or hide each type.',
            'Tentative holidays show "?" until the date is confirmed.',
            ...(role && ADMIN_ROLES.includes(role) ? ['Tap a day, then + Holiday or + Event to add one.'] : []),
        ],
        example: 'Tap 14 Dec to see "Annual Day, 10:00, Main hall" and "Unit Test: Maths".',
    }),

    '/leave/my': (role) => {
        if (role === 'PARENT') {
            return {
                lead: "Apply for your child's leave.",
                points: ['Pick the dates, the type and a reason.', 'The class teacher approves or rejects it.', 'You get a notification with the decision.'],
                example: "Riya has a fever. Apply for Mon-Tue as Sick leave, and you're told when it's approved.",
            };
        }
        if (role === 'STUDENT') {
            return {
                lead: 'Apply for your leave.',
                points: ['Pick the dates, the type and a reason.', 'Your class teacher approves or rejects it.', 'You get a notification with the decision.'],
                example: "You have a fever. Apply for Mon-Tue as Sick leave, and you're told when it's approved.",
            };
        }
        return {
            lead: 'Apply for your leave and see your balance.',
            points: [
                'The cards show how many paid days you have left.',
                'Holidays and weekly offs inside a leave are not counted.',
                'Days beyond your balance are unpaid.',
            ],
            example: 'With 2 Casual days left, a 3-day Casual leave has 1 unpaid day.',
        };
    },

    '/leave/requests': {
        lead: 'Approve or reject leave requests.',
        points: [
            'Pending requests are shown first.',
            "Staff requests show the person's balance, and any days that would be unpaid.",
            'The person gets a notification with your decision.',
        ],
        example: 'Ravi asks for 2 days of Sick leave. Approve it, then arrange substitutes for his classes.',
    },

    '/leave/policy': {
        lead: 'Set how many paid leave days staff get each year.',
        points: [
            'Leave a box empty for no limit, or enter 0 for always unpaid.',
            'Holidays and weekly offs are not counted.',
            'Leave beyond the balance can still be approved, as unpaid.',
        ],
        example: 'Casual 12, Sick 10. A teacher who takes 13 Casual days has 1 unpaid day.',
    },

    '/attendance/mark': {
        lead: 'Mark students present, absent, late or on leave.',
        points: [
            'Pick the class, section and date.',
            'Students with approved leave start as "Leave".',
            'Parents of absent students get a notification.',
        ],
        example: 'Mark everyone present, then change Arjun to Absent. His parents are told.',
    },

    '/attendance/staff': {
        lead: 'Mark attendance for teachers and staff.',
        points: [
            'Everyone starts as Present; staff on approved leave start as Leave.',
            'Half day and Absent count towards loss of pay.',
            'You can edit past days, but not future ones.',
        ],
        example: 'Mark Meera as Half day. It shows in her salary for the month.',
    },

    '/attendance/staff-register': {
        lead: 'Monthly attendance of all staff, with totals.',
        points: [
            'Each row is a person; each column is a day.',
            'HO is a holiday, WO a weekly off, UL unpaid leave.',
            'Download or print it as a PDF.',
        ],
        example: 'At month end, print the register and attach it to the salary file.',
    },

    '/finance/fee-collection': {
        lead: 'Collect fees and print receipts.',
        points: [
            "Search for a student to see their fees and balance.",
            'Choose what is being paid and the payment mode.',
            'A receipt is ready right after saving.',
        ],
        example: 'Search "Arjun", pay Term 2 by UPI, and print the receipt.',
    },

    '/finance/defaulters': {
        lead: 'Students whose fees are past the due date.',
        points: ['Filter by class.', "See the overdue amount and the parent's contact.", 'Download the list as a CSV file.'],
        example: 'Filter Class 8, download the list, and call the parents.',
    },

    '/finance/salary-payments': {
        lead: 'Create and pay monthly salaries.',
        points: [
            "Generate salaries for a month from each person's salary setup.",
            "Each row shows that month's attendance.",
            'Apply loss of pay for absences, half days or unpaid leave before paying.',
        ],
        example: 'Ravi was absent 2 days in March. Apply loss of pay, then mark the salary as paid.',
    },

    '/roles': {
        lead: 'Decide what each role can see and do.',
        points: ['Tick the boxes for each role.', 'Changes apply within a minute.', 'The Institution Admin always has full access.'],
        example: 'Tick "Approve Leave" for the Principal, so they can decide all leave requests.',
    },

    '/substitutions': {
        lead: "Cover classes when a teacher can't take them.",
        points: [
            'Lists the periods of teachers on leave, absent, on half day, or busy.',
            'Suggests free teachers, best match first (same subject).',
            'The substitute, students and parents see it in their timetable.',
        ],
        example: 'Ravi is on leave on Monday. His Maths class for 6-B shows here. Anita, a free Maths teacher, is suggested. Assign her, and she and the class are informed.',
    },
};

/** Help for a page address (exact match, ignoring a trailing slash), for this role; undefined if none. */
export const getPageHelp = (pathname: string, role: string | undefined): PageHelp | undefined => {
    const path = pathname.length > 1 ? pathname.replace(/\/+$/, '') : pathname;
    const help = PAGE_HELP[path];
    return typeof help === 'function' ? help(role) : help;
};
