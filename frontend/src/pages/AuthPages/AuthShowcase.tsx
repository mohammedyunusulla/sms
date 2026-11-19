import { Link } from "react-router";
import {
  CheckIcon,
  DatabaseIcon,
  QrCodeIcon,
  SparklesIcon,
  UsersIcon,
} from "../../components/common/StrokeIcons";

const STATS = [
  { label: "Attendance today", value: "96%", bar: "bg-success-400" },
  { label: "Fees collected", value: "82%", bar: "bg-blue-light-400" },
  { label: "Syllabus covered", value: "64%", bar: "bg-brand-300" },
];

const HIGHLIGHTS = [
  { icon: UsersIcon, label: "Role-based dashboards" },
  { icon: DatabaseIcon, label: "Isolated data per school" },
  { icon: SparklesIcon, label: "AI homework tutor" },
];

/**
 * Brand panel shown beside the auth forms on large screens (left side).
 * Sticky so it stays in view while longer forms (sign up) scroll.
 */
export default function AuthShowcase() {
  return (
    <aside
      aria-label="About Edusphere"
      className="relative hidden overflow-hidden bg-gradient-to-br from-brand-600 via-brand-800 to-brand-950 lg:sticky lg:top-0 lg:flex lg:h-screen lg:w-1/2 lg:self-start xl:w-[54%] dark:from-brand-800 dark:via-brand-950 dark:to-gray-950"
    >
      {/* Background */}
      <div aria-hidden="true" className="auth-grid absolute inset-0" />
      <div aria-hidden="true" className="absolute -right-32 -top-32 size-[28rem] rounded-full bg-blue-light-400/25 blur-3xl" />
      <div aria-hidden="true" className="absolute -bottom-40 -left-32 size-[28rem] rounded-full bg-success-400/20 blur-3xl" />

      <div className="relative z-1 flex w-full flex-col p-10 xl:p-14">
        <Link
          to="/"
          className="self-start rounded-lg focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-white/30"
        >
          <img
            src="/images/logo/edusphere-dark-clean.png"
            alt="Edusphere home"
            width={331}
            height={96}
            className="h-11 w-auto"
          />
        </Link>

        <div className="my-auto py-10">
          <span className="inline-flex items-center rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-brand-100 ring-1 ring-white/15">
            Smart Education Management System
          </span>
          <p className="mt-5 max-w-lg text-4xl font-bold leading-tight tracking-tight text-white xl:text-5xl xl:leading-[1.1]">
            Your whole school,{" "}
            <span className="bg-gradient-to-r from-blue-light-300 to-success-300 bg-clip-text text-transparent">
              one login away.
            </span>
          </p>
          <p className="mt-4 max-w-md text-base leading-relaxed text-brand-100/90">
            Attendance, timetables, exams, fees and homework, together in one secure place for your whole school
            community.
          </p>

          {/* Illustrative product card (hidden on short screens so the panel never overflows) */}
          <div aria-hidden="true" className="relative mt-14 hidden max-w-md [@media(min-height:820px)]:block">
            <div className="rounded-3xl bg-white/10 p-5 shadow-2xl shadow-brand-950/40 ring-1 ring-white/15 backdrop-blur-md">
              <div>
                <p className="text-xs text-brand-100/80">Good morning</p>
                <p className="font-semibold text-white">School overview</p>
              </div>
              <ul className="mt-5 space-y-4">
                {STATS.map((s, i) => (
                  <li key={s.label}>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-brand-100">{s.label}</span>
                      <span className="font-semibold text-white">{s.value}</span>
                    </div>
                    <div className="mt-2 h-2 overflow-hidden rounded-full bg-white/10">
                      <div
                        className={`auth-bar h-full rounded-full ${s.bar}`}
                        style={{ width: s.value, animationDelay: `${300 + i * 150}ms` }}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            </div>

            <div className="auth-float absolute -right-6 -top-12 w-60 rounded-2xl bg-white p-3.5 shadow-xl shadow-brand-950/30 dark:bg-gray-900">
              <p className="flex items-center gap-1.5 text-xs font-semibold text-brand-600 dark:text-brand-300">
                <SparklesIcon className="size-4" /> AI tutor hint
              </p>
              <p className="mt-1 text-xs leading-relaxed text-gray-600 dark:text-gray-300">
                Could you split the shape into two triangles first?
              </p>
            </div>

            <div className="auth-float-delayed absolute -bottom-16 -left-6 flex items-center gap-3 rounded-2xl bg-white p-3 pr-4 shadow-xl shadow-brand-950/30 dark:bg-gray-900">
              <span className="flex size-9 items-center justify-center rounded-xl bg-success-50 text-success-600 dark:bg-success-500/15 dark:text-success-400">
                <QrCodeIcon className="size-5" />
              </span>
              <div>
                <p className="text-xs font-semibold text-gray-900 dark:text-white">Boarded Bus 12</p>
                <p className="flex items-center gap-1 text-[11px] text-gray-500 dark:text-gray-400">
                  <CheckIcon className="size-3 text-success-500" strokeWidth={2.5} /> QR check-in · 7:42 AM
                </p>
              </div>
            </div>
          </div>
        </div>

        <ul className="flex flex-wrap gap-x-6 gap-y-3 border-t border-white/10 pt-6 text-sm text-brand-100">
          {HIGHLIGHTS.map(({ icon: Icon, label }) => (
            <li key={label} className="flex items-center gap-2">
              <span className="flex size-7 items-center justify-center rounded-lg bg-white/10 ring-1 ring-white/15">
                <Icon className="size-4" />
              </span>
              {label}
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}
