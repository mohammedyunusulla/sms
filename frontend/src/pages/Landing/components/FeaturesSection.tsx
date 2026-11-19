import type { ComponentType } from "react";
import { usePrefersReducedMotion } from "../landingNav";
import {
  AwardIcon,
  BookOpenIcon,
  BusIcon,
  CalendarIcon,
  ClipboardCheckIcon,
  FileTextIcon,
  IdCardIcon,
  MegaphoneIcon,
  SparklesIcon,
  WalletIcon,
} from "../../../components/common/StrokeIcons";
import type { IconProps } from "../../../components/common/StrokeIcons";
import Reveal from "./Reveal";
import SectionHeading from "./SectionHeading";

const TONES = {
  brand: "bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300",
  success: "bg-success-50 text-success-600 dark:bg-success-500/15 dark:text-success-400",
  warning: "bg-warning-50 text-warning-600 dark:bg-warning-500/15 dark:text-warning-400",
  purple: "bg-theme-purple-500/10 text-theme-purple-500 dark:bg-theme-purple-500/20",
  blue: "bg-blue-light-50 text-blue-light-600 dark:bg-blue-light-500/15 dark:text-blue-light-400",
  pink: "bg-theme-pink-500/10 text-theme-pink-500 dark:bg-theme-pink-500/20",
  orange: "bg-orange-50 text-orange-600 dark:bg-orange-500/15 dark:text-orange-400",
  error: "bg-error-50 text-error-600 dark:bg-error-500/15 dark:text-error-400",
} as const;

interface Feature {
  icon: ComponentType<IconProps>;
  title: string;
  body: string;
  tone: keyof typeof TONES;
}

const ATTENDANCE: Feature = {
  icon: ClipboardCheckIcon,
  title: "Attendance",
  body: "Mark a whole class in seconds and review attendance reports whenever you need them.",
  tone: "success",
};
const TIMETABLES: Feature = {
  icon: CalendarIcon,
  title: "Timetables",
  body: "Build class timetables, assign teachers to subjects and share schedules with students and parents.",
  tone: "brand",
};
const EXAMS: Feature = {
  icon: FileTextIcon,
  title: "Exams & seating",
  body: "Plan exam timetables, arrange seating room by room and publish invigilator duties.",
  tone: "warning",
};
const MARKS: Feature = {
  icon: AwardIcon,
  title: "Marks & progress cards",
  body: "Enter marks once and print progress cards and annual reports for every student.",
  tone: "purple",
};
const REST: Feature[] = [
  {
    icon: WalletIcon,
    title: "Fees & expenses",
    body: "Set up fee structures, record collections and keep school expenses in check.",
    tone: "blue",
  },
  {
    icon: BookOpenIcon,
    title: "Syllabus tracking",
    body: "Break subjects into topics and subtopics and see how far each class has progressed.",
    tone: "pink",
  },
  {
    icon: MegaphoneIcon,
    title: "Announcements",
    body: "Share notices and updates with your whole school community instantly.",
    tone: "orange",
  },
  {
    icon: IdCardIcon,
    title: "Certificates & ID cards",
    body: "Generate student certificates and QR-coded ID cards, ready to print.",
    tone: "error",
  },
];

function FeatureCard({ icon: Icon, title, body, tone }: Feature) {
  return (
    <div className="group h-full rounded-3xl border border-gray-200 bg-white p-6 transition duration-300 hover:-translate-y-1 hover:border-brand-200 hover:shadow-xl hover:shadow-brand-500/5 dark:border-white/10 dark:bg-white/[0.03] dark:hover:border-brand-500/30">
      <span
        className={`inline-flex size-12 items-center justify-center rounded-2xl transition-transform duration-300 group-hover:scale-110 ${TONES[tone]}`}
      >
        <Icon className="size-6" />
      </span>
      <h3 className="mt-5 text-lg font-semibold text-gray-900 dark:text-white">{title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-gray-600 dark:text-gray-400">{body}</p>
    </div>
  );
}

function HomeworkTile() {
  return (
    <div className="relative flex h-full flex-col overflow-hidden rounded-3xl bg-gradient-to-br from-brand-950 via-brand-900 to-brand-700 p-7 text-white sm:p-8">
      <div aria-hidden="true" className="landing-grid-bg-light absolute inset-0" />
      <div aria-hidden="true" className="absolute -right-16 -top-16 size-56 rounded-full bg-blue-light-400/25 blur-3xl" />
      <div className="relative grid flex-1 gap-8 md:grid-cols-2 md:items-center">
        <div>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-brand-100 ring-1 ring-white/15">
            <SparklesIcon className="size-3.5 text-blue-light-300" /> AI-powered
          </span>
          <h3 className="mt-4 text-2xl font-semibold tracking-tight">Homework with a built-in AI tutor</h3>
          <p className="mt-3 text-sm leading-relaxed text-brand-100/90">
            When students get stuck they receive Socratic hints, never the answer, so they still do the
            thinking. Submissions are graded with AI, and teachers get per-assignment analytics plus stickers to
            reward effort.
          </p>
        </div>

        <div aria-hidden="true" className="space-y-3">
          <div className="ml-auto max-w-[85%] rounded-2xl rounded-br-md bg-white px-4 py-3 text-sm text-gray-800 shadow-lg">
            How do I find the area of this triangle?
          </div>
          <div className="max-w-[90%] rounded-2xl rounded-bl-md bg-white/10 px-4 py-3 text-sm text-white ring-1 ring-white/15 backdrop-blur">
            <p className="mb-1 flex items-center gap-1.5 text-xs font-semibold text-blue-light-300">
              <SparklesIcon className="size-3.5" /> Hint
            </p>
            How do you find the area of a rectangle? How might a triangle relate to a rectangle with the same
            base and height?
          </div>
          <div className="flex max-w-[60%] gap-1.5 rounded-2xl rounded-bl-md bg-white/5 px-4 py-3 ring-1 ring-white/10">
            <span className="landing-shimmer h-2 flex-1 rounded-full" />
            <span className="landing-shimmer h-2 w-1/3 rounded-full" />
          </div>
        </div>
      </div>
    </div>
  );
}

const ROUTE = "M24 120 C 70 120, 80 52, 140 58 S 210 118, 296 34";

function BusTile() {
  const reducedMotion = usePrefersReducedMotion();

  return (
    <div className="relative flex h-full flex-col overflow-hidden rounded-3xl border border-gray-200 bg-white p-7 sm:p-8 dark:border-white/10 dark:bg-white/[0.03]">
      <div className="grid flex-1 gap-8 md:grid-cols-2 md:items-center">
        <div>
          <span className="inline-flex size-12 items-center justify-center rounded-2xl bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300">
            <BusIcon className="size-6" />
          </span>
          <h3 className="mt-5 text-2xl font-semibold tracking-tight text-gray-900 dark:text-white">
            Safer school transport
          </h3>
          <p className="mt-3 text-sm leading-relaxed text-gray-600 dark:text-gray-400">
            Bus staff record every boarding and drop-off with a quick QR scan, with daily reports for the school.
            Live map tracking for parents is coming soon in the Edusphere mobile app.
          </p>
          <ul className="mt-5 flex flex-wrap gap-2">
            <li className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700 dark:bg-white/5 dark:text-gray-300">
              QR boarding scans
            </li>
            <li className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700 dark:bg-white/5 dark:text-gray-300">
              Trip reports
            </li>
            <li className="rounded-full bg-warning-50 px-3 py-1 text-xs font-semibold text-warning-700 dark:bg-warning-500/10 dark:text-warning-400">
              Live map · Coming soon
            </li>
          </ul>
        </div>

        <div aria-hidden="true" className="relative overflow-hidden rounded-2xl bg-gray-50 ring-1 ring-gray-100 dark:bg-gray-900 dark:ring-white/5">
          <svg viewBox="0 0 320 150" className="block h-auto w-full">
            <g strokeLinecap="round" strokeWidth={6} className="stroke-gray-200/80 dark:stroke-white/[0.06]">
              <path d="M0 38 H320" />
              <path d="M0 106 H320" />
              <path d="M92 0 V150" />
              <path d="M232 0 V150" />
            </g>
            <path d={ROUTE} fill="none" strokeWidth={4} strokeLinecap="round" className="stroke-brand-200 dark:stroke-brand-500/30" />
            <path d={ROUTE} fill="none" strokeWidth={4} strokeLinecap="round" className="landing-route stroke-brand-500" />

            {/* Stops */}
            <circle cx="24" cy="120" r="6" className="fill-white stroke-brand-500" strokeWidth={3} />
            <circle cx="140" cy="58" r="5" className="fill-white stroke-brand-400" strokeWidth={3} />
            <text x="24" y="143" textAnchor="middle" className="fill-gray-500 text-[9px] font-medium dark:fill-gray-400">
              Home stop
            </text>

            {/* School */}
            <circle cx="296" cy="34" r="12" className="fill-success-500/20" />
            <circle cx="296" cy="34" r="7" className="fill-success-500" />
            <text x="296" y="62" textAnchor="middle" className="fill-gray-500 text-[9px] font-medium dark:fill-gray-400">
              School
            </text>

            {/* Bus */}
            <g transform={reducedMotion ? "translate(140 58)" : undefined}>
              <circle r="13" className="fill-brand-500/20" />
              <circle r="8" className="fill-brand-500 stroke-white dark:stroke-gray-900" strokeWidth={3} />
              {!reducedMotion && (
                <animateMotion dur="7s" repeatCount="indefinite" path={ROUTE} />
              )}
            </g>
          </svg>

          <div className="absolute left-3 top-3 flex items-center gap-1.5 rounded-full bg-white/90 px-2.5 py-1 text-[11px] font-medium text-gray-700 shadow-sm dark:bg-gray-800/90 dark:text-gray-200">
            <span className="relative flex size-2">
              <span className="absolute inline-flex size-full rounded-full bg-success-400 opacity-75 motion-safe:animate-ping" />
              <span className="relative inline-flex size-2 rounded-full bg-success-500" />
            </span>
            Live map preview
          </div>
        </div>
      </div>
    </div>
  );
}

export default function FeaturesSection() {
  return (
    <section id="features" className="scroll-mt-20 py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <Reveal>
          <SectionHeading
            eyebrow="Features"
            title={
              <>
                Everything your school runs on, <span className="landing-gradient-text">in one platform</span>
              </>
            }
            description="Replace scattered spreadsheets, paper registers and group chats with connected modules that share the same students, classes and academic year."
          />
        </Reveal>

        <div className="mt-16 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Reveal className="sm:col-span-2">
            <HomeworkTile />
          </Reveal>
          <Reveal delay={80}>
            <FeatureCard {...ATTENDANCE} />
          </Reveal>
          <Reveal delay={160}>
            <FeatureCard {...TIMETABLES} />
          </Reveal>

          <Reveal>
            <FeatureCard {...EXAMS} />
          </Reveal>
          <Reveal delay={80}>
            <FeatureCard {...MARKS} />
          </Reveal>
          <Reveal delay={160} className="sm:col-span-2">
            <BusTile />
          </Reveal>

          {REST.map((feature, i) => (
            <Reveal key={feature.title} delay={i * 80}>
              <FeatureCard {...feature} />
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
