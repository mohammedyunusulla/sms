import { useRef, useState } from "react";
import type { ComponentType, KeyboardEvent } from "react";
import {
  AwardIcon,
  BookOpenIcon,
  BuildingIcon,
  BusIcon,
  CalendarIcon,
  CheckIcon,
  ClipboardCheckIcon,
  GraduationCapIcon,
  MapPinIcon,
  PresentationIcon,
  QrCodeIcon,
  SparklesIcon,
  StarIcon,
  UsersIcon,
  WalletIcon,
} from "../../../components/common/StrokeIcons";
import type { IconProps } from "../../../components/common/StrokeIcons";
import Reveal from "./Reveal";
import SectionHeading from "./SectionHeading";

type Tone = "brand" | "success" | "warning" | "purple";

const BADGE: Record<Tone, string> = {
  brand: "bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300",
  success: "bg-success-50 text-success-700 dark:bg-success-500/15 dark:text-success-400",
  warning: "bg-warning-50 text-warning-700 dark:bg-warning-500/15 dark:text-warning-400",
  purple: "bg-theme-purple-500/10 text-theme-purple-500 dark:bg-theme-purple-500/20",
};

interface PreviewRow {
  icon: ComponentType<IconProps>;
  title: string;
  meta: string;
  badge: string;
  tone: Tone;
}

interface Role {
  id: string;
  label: string;
  icon: ComponentType<IconProps>;
  headline: string;
  description: string;
  points: string[];
  previewTitle: string;
  rows: PreviewRow[];
}

const ROLES: Role[] = [
  {
    id: "administrators",
    label: "Administrators",
    icon: BuildingIcon,
    headline: "Full control over school operations",
    description:
      "School admins and principals run admissions, classes, staff, fees and academic years from a single dashboard.",
    points: [
      "Add teachers, students and parents one by one or in bulk",
      "Build timetables and plan exams with seating arrangements",
      "Track fee collection and school expenses",
      "Control exactly what every role can see and do",
    ],
    previewTitle: "School overview",
    rows: [
      { icon: WalletIcon, title: "Fee collection · Term 2", meta: "₹4.8L of ₹5.9L collected", badge: "82%", tone: "brand" },
      { icon: ClipboardCheckIcon, title: "Attendance today", meta: "1,203 of 1,248 present", badge: "96%", tone: "success" },
      { icon: CalendarIcon, title: "Exam seating · Room 4", meta: "Mid-term · 40 seats", badge: "Ready", tone: "warning" },
    ],
  },
  {
    id: "teachers",
    label: "Teachers",
    icon: PresentationIcon,
    headline: "Less paperwork, more teaching",
    description: "Teachers see their classes, periods and pending work the moment they log in.",
    points: [
      "Mark attendance for a class in seconds",
      "Spot students who need attention with Attendance Watch",
      "Track syllabus coverage topic by topic",
      "Set assignments with text or a hand-drawn sketch, and review AI-assisted grading",
    ],
    previewTitle: "Your day",
    rows: [
      { icon: ClipboardCheckIcon, title: "Mark attendance", meta: "Class 8-B · Period 1", badge: "Due 9:10", tone: "warning" },
      { icon: AwardIcon, title: "Unit test 2 marks", meta: "Mathematics · 8-A", badge: "18 / 34", tone: "brand" },
      { icon: BookOpenIcon, title: "Syllabus · Fractions", meta: "Topic 4 of 6", badge: "67%", tone: "success" },
    ],
  },
  {
    id: "parents",
    label: "Parents",
    icon: UsersIcon,
    headline: "Stay close to your child's school day",
    description:
      "Everything about your children in one place, on the web today and in the EduSpyre mobile app soon.",
    points: [
      "Follow the school bus live on a map (mobile app, coming soon)",
      "Switch between your children in one tap",
      "See timetables, assignments and syllabus progress",
      "Check fee details, instalments and payment history",
    ],
    previewTitle: "Today",
    rows: [
      { icon: BusIcon, title: "Bus 12", meta: "On the way to school", badge: "Live", tone: "success" },
      { icon: ClipboardCheckIcon, title: "Attendance", meta: "Marked present · 9:05 AM", badge: "Present", tone: "success" },
      { icon: AwardIcon, title: "Progress card", meta: "Term 1 results published", badge: "New", tone: "brand" },
    ],
  },
  {
    id: "students",
    label: "Students",
    icon: GraduationCapIcon,
    headline: "Everything for the school day",
    description: "Students always know what's next and get help exactly when they need it.",
    points: [
      "Personal timetable and exam schedule",
      "Homework with an AI tutor that guides instead of giving answers",
      "Marks and progress at a glance",
      "Instant AI feedback on submitted homework",
    ],
    previewTitle: "Up next",
    rows: [
      { icon: SparklesIcon, title: "Homework · Geometry", meta: "Due tomorrow", badge: "AI tutor", tone: "purple" },
      { icon: CalendarIcon, title: "Next period", meta: "Science lab · 10:30", badge: "Room 4", tone: "brand" },
      { icon: StarIcon, title: "Homework feedback", meta: "Geometry · graded", badge: "92%", tone: "warning" },
    ],
  },
  {
    id: "bus-staff",
    label: "Bus staff",
    icon: BusIcon,
    headline: "Simple tools for every trip",
    description: "Bus staff keep the school and parents informed without any extra paperwork.",
    points: [
      "Check students in and out with a QR scan",
      "Review a daily report of every check-in and check-out",
      "Share the bus's live location from the mobile app (coming soon)",
    ],
    previewTitle: "Morning route",
    rows: [
      { icon: MapPinIcon, title: "Location sharing", meta: "Visible to parents", badge: "Live", tone: "success" },
      { icon: QrCodeIcon, title: "Boarded", meta: "28 of 31 students", badge: "QR", tone: "brand" },
      { icon: BusIcon, title: "Next stop", meta: "Stop 5 of 9", badge: "Next", tone: "warning" },
    ],
  },
];

export default function RolesSection() {
  const [active, setActive] = useState(0);
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const role = ROLES[active];

  const focusTab = (index: number) => {
    const next = (index + ROLES.length) % ROLES.length;
    setActive(next);
    tabRefs.current[next]?.focus();
  };

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "ArrowRight") focusTab(active + 1);
    else if (e.key === "ArrowLeft") focusTab(active - 1);
    else if (e.key === "Home") focusTab(0);
    else if (e.key === "End") focusTab(ROLES.length - 1);
    else return;
    e.preventDefault();
  };

  return (
    <section id="roles" className="scroll-mt-20 bg-gray-50 py-24 sm:py-32 dark:bg-white/[0.02]">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <Reveal>
          <SectionHeading
            eyebrow="Who it's for"
            title="One platform, a tailored experience for everyone"
            description="Each person signs in to a dashboard built around their role, so they see only what matters to them."
          />
        </Reveal>

        <Reveal delay={100}>
          <div className="mt-12 flex justify-center">
            <div
              role="tablist"
              aria-label="EduSpyre users"
              onKeyDown={onKeyDown}
              className="flex max-w-full gap-1 overflow-x-auto rounded-full border border-gray-200 bg-white p-1.5 shadow-sm [scrollbar-width:none] dark:border-white/10 dark:bg-gray-900"
            >
              {ROLES.map((r, i) => {
                const selected = i === active;
                const Icon = r.icon;
                return (
                  <button
                    key={r.id}
                    ref={(el) => {
                      tabRefs.current[i] = el;
                    }}
                    type="button"
                    role="tab"
                    id={`role-tab-${r.id}`}
                    aria-selected={selected}
                    aria-controls={`role-panel-${r.id}`}
                    tabIndex={selected ? 0 : -1}
                    onClick={() => setActive(i)}
                    className={`flex shrink-0 items-center gap-2 whitespace-nowrap rounded-full px-4 py-2.5 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-500/30 ${
                      selected
                        ? "bg-brand-500 text-white shadow-md shadow-brand-500/25"
                        : "text-gray-600 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-300 dark:hover:bg-white/5 dark:hover:text-white"
                    }`}
                  >
                    <Icon className="size-4" />
                    {r.label}
                  </button>
                );
              })}
            </div>
          </div>
        </Reveal>

        <div
          key={role.id}
          role="tabpanel"
          id={`role-panel-${role.id}`}
          aria-labelledby={`role-tab-${role.id}`}
          className="landing-fade-in mt-12 grid items-center gap-10 lg:grid-cols-2 lg:gap-16"
        >
          <div>
            <h3 className="text-2xl font-semibold tracking-tight text-gray-900 sm:text-3xl dark:text-white">
              {role.headline}
            </h3>
            <p className="mt-4 text-lg leading-relaxed text-gray-600 dark:text-gray-400">{role.description}</p>
            <ul className="mt-8 space-y-4">
              {role.points.map((point) => (
                <li key={point} className="flex items-start gap-3">
                  <span className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full bg-brand-500 text-white">
                    <CheckIcon className="size-3.5" strokeWidth={2.5} />
                  </span>
                  <span className="text-gray-700 dark:text-gray-300">{point}</span>
                </li>
              ))}
            </ul>
          </div>

          <div aria-hidden="true" className="relative">
            <div className="absolute -inset-4 rounded-[2rem] bg-gradient-to-br from-brand-500/15 via-transparent to-success-400/15 blur-xl" />
            <div className="relative rounded-3xl border border-gray-200 bg-white p-6 shadow-xl shadow-gray-900/5 sm:p-7 dark:border-white/10 dark:bg-gray-900 dark:shadow-black/30">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="flex size-10 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-success-500 text-white">
                    <role.icon className="size-5" />
                  </span>
                  <div>
                    <p className="text-xs text-gray-500 dark:text-gray-400">{role.label}</p>
                    <p className="font-semibold text-gray-900 dark:text-white">{role.previewTitle}</p>
                  </div>
                </div>
                <span className="flex gap-1">
                  <span className="size-1.5 rounded-full bg-gray-300 dark:bg-gray-600" />
                  <span className="size-1.5 rounded-full bg-gray-300 dark:bg-gray-600" />
                  <span className="size-1.5 rounded-full bg-gray-300 dark:bg-gray-600" />
                </span>
              </div>
              <ul className="mt-6 space-y-3">
                {role.rows.map((row) => (
                  <li
                    key={row.title}
                    className="flex items-center gap-4 rounded-2xl border border-gray-100 bg-gray-50/60 p-4 dark:border-white/5 dark:bg-white/[0.03]"
                  >
                    <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-white text-gray-600 shadow-sm ring-1 ring-gray-100 dark:bg-gray-800 dark:text-gray-300 dark:ring-white/5">
                      <row.icon className="size-5" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-gray-900 dark:text-white">{row.title}</p>
                      <p className="truncate text-xs text-gray-500 dark:text-gray-400">{row.meta}</p>
                    </div>
                    <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold ${BADGE[row.tone]}`}>
                      {row.badge}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
