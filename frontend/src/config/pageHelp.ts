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
    '/institutions/:id/features': {
        lead: 'Choose what this institution gets.',
        points: [
            'Switch on only the features it needs; the rest stay hidden for its users.',
            'Switching a feature on also switches on what it needs.',
            'Who can sign in: people of a role that is off are added without a login.',
        ],
        example: 'Switch on Timetable: Subjects comes on with it.',
    },

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

    // ---------------------------------------------------------------- round 2
    '/timetable': {
        lead: 'Weekly class timetables.',
        points: [
            'Create one for each class and section.',
            'Teacher clashes are checked automatically.',
            'Publish it so teachers, students and parents can see it.',
        ],
        example: "Make 6-B's timetable for Semester 1, publish it, and the class sees it in My Timetable.",
    },

    '/exams': {
        lead: 'The exam types your institution holds.',
        points: [
            'Add types like Unit Test, Midterm and Final.',
            'Set subjects and maximum marks per class in Subject Configuration.',
            'These are used in the exam timetable, marks and report cards.',
        ],
        example: 'Add "Unit Test 1", then set Maths out of 25 for Grade 8.',
    },

    '/exams/timetable': {
        lead: 'Dates and times for each exam paper.',
        points: ['Schedule each subject for a class.', "Students and parents see their class's papers on the Calendar."],
        example: 'Maths on 7 Dec, 9:00-11:00, for Grade 8.',
    },

    '/exams/seating': {
        lead: 'Who sits where during exams.',
        points: ["Pick a room, date and classes.", "Seats are filled from the room's layout.", 'Add an invigilator and print the plan.'],
        example: 'Fill Hall A with Grade 8 and Grade 9 for the 7 Dec paper.',
    },

    '/academics/marks/entry': {
        lead: 'Enter exam marks for a class.',
        points: [
            'Pick the exam, class and subject.',
            'Type the marks for each student.',
            'Students and parents see them only after results are published.',
        ],
        example: 'Enter Unit Test 1 Maths marks for 8-A.',
    },

    '/academics/progress/class': {
        lead: 'How a class and each student are doing.',
        points: ['Averages per subject and exam.', "Open a student's progress card.", 'Print report cards.'],
        example: "See that 8-B's Science average dropped after the Midterm.",
    },

    '/finance/fee-structure': {
        lead: 'The fees for each class.',
        points: ['Add fee items like Tuition and Transport.', 'Split them into installments with due dates.', 'Fee Collection and Defaulters use these.'],
        example: 'Grade 8: Tuition 30,000 in 3 installments.',
    },

    '/finance/expenses': {
        lead: "Track the institution's spending.",
        points: ['Add an expense with its category, amount and date.', 'Salaries paid appear here automatically.'],
        example: 'Add "Electricity bill, 12,400, Nov".',
    },

    '/finance/salary-setup': {
        lead: "Each staff member's monthly salary.",
        points: ['Basic pay plus allowances, minus deductions.', 'Salary Payments are created from this every month.'],
        example: 'Ravi: Basic 30,000 + HRA 5,000 - PF 1,800.',
    },

    '/announcements': (role) => (role === 'STUDENT' || role === 'PARENT'
        ? {
            lead: 'News from your institution.',
            points: ['The latest is shown first.', 'You also get a notification.'],
            example: '"Sports Day on 20 Dec."',
        }
        : {
            lead: 'Share news with students, parents or staff.',
            points: ['Choose who sees it: everyone, a class, or only staff.', 'A notification is sent when it is published.'],
            example: '"School closed tomorrow due to rain", sent to everyone.',
        }),

    '/assignments': {
        lead: 'Give work to a class and review it.',
        points: ['Create an assignment for a section.', 'Students submit their work.', 'Review it and give feedback.'],
        example: '"Write an essay on rivers" for 6-B, due Friday.',
    },

    '/assignments/my-assignments': {
        lead: 'Work from your teachers.',
        points: ['See what is due and when.', 'Submit your work here.', "See your teacher's feedback."],
        example: 'Submit "Essay on rivers" before Friday.',
    },

    '/homework/teacher': {
        lead: 'Set daily homework and see how each class did.',
        points: [
            "Create Homework: pick the date (today by default), class and subject; that day's homework is listed below.",
            'Students see only the title until they press Start; the AI grades their uploaded work.',
            'Analytics: pick a date and a homework to see results, time taken and flags.',
        ],
        example: 'Set "Fractions practice" for 8-A today; tomorrow check who finished and their marks.',
    },

    '/homework/student': {
        lead: 'Do your homework and see your results.',
        points: [
            "Today's Homework: press Start to see the questions; the timer starts then.",
            'Ask for a hint if you are stuck, then photograph your work; the AI grades it.',
            "Past Homeworks: pick a date to see that day's homework and your result.",
        ],
        example: 'Start the Maths homework, ask for a hint on sum 3, then photograph your pages.',
    },

    // the menu opens /homework, which shows the teacher or student page by role
    '/homework': (role) => {
        const r = (role || '').toUpperCase();
        const page = PAGE_HELP[r === 'STUDENT' || r === 'LEARNER' ? '/homework/student' : '/homework/teacher'];
        return typeof page === 'function' ? page(role) : page;
    },

    '/syllabus': {
        lead: 'Plan lessons and track progress.',
        points: [
            'Break each subject into lessons, topics and subtopics.',
            'Teachers mark what has been covered.',
            'See how far each class has got.',
        ],
        example: 'Grade 8 Science is 60% done by November.',
    },

    '/bus-scan': {
        lead: 'Who got on and off the bus.',
        points: [
            "Scan each student's QR code when they board or get off.",
            'See who is on the bus right now.',
            'Past scans are in the Tracking Report.',
        ],
        example: "Scan Arjun's ID card at 7:40, and he shows as on the bus.",
    },

    '/bus-scan/report': {
        lead: 'Past bus boarding and drop-off records.',
        points: ['Filter by date and student.', 'See when each student got on and off.'],
        example: 'Check when Arjun got off the bus last Tuesday.',
    },

    '/classes': {
        lead: 'Classes and their sections.',
        points: [
            'Add a class, like Grade 8, with sections A and B.',
            'Set a class teacher for each section.',
            'The class teacher approves student leave for that section.',
        ],
        example: 'Grade 8 with sections A and B; Anita is class teacher of 8-A.',
    },

    '/rooms': {
        lead: 'Rooms, labs and halls.',
        points: ['Add rooms with their seating layout.', 'They are used for exam seating.'],
        example: 'Hall A, 8 rows of 6 seats.',
    },

    '/students': {
        lead: 'Add and manage students.',
        points: ['Add a student with their class and section.', 'Link parents.', 'Print ID cards and certificates.'],
        example: 'Add Arjun to 8-A and link his father.',
    },

    '/teachers': {
        lead: 'Add and manage teachers.',
        points: ['Add a teacher.', 'Assign their subjects and classes.'],
        example: 'Add Anita and assign Maths for Grade 8.',
    },

    '/parents': {
        lead: 'Parents and their children.',
        points: ['Link a parent to one or more children.', "Parents sign in to see their children's details."],
        example: 'Link Rajesh to Arjun and Riya.',
    },

    '/users': {
        lead: 'Everyone who can sign in.',
        points: ['Create accounts and give each a role.', 'Turn access on or off.'],
        example: 'Add a clerk for the fee counter.',
    },
};

/** Help for a page address (exact match, ignoring a trailing slash), for this role; undefined if none. */
export const getPageHelp = (pathname: string, role: string | undefined): PageHelp | undefined => {
    const path = pathname.length > 1 ? pathname.replace(/\/+$/, '') : pathname;
    const key = path === '/bus-scan/scan' ? '/bus-scan' : path.replace(/^\/institutions\/\d+\/features$/, '/institutions/:id/features');
    const help = PAGE_HELP[key];
    return typeof help === 'function' ? help(role) : help;
};
