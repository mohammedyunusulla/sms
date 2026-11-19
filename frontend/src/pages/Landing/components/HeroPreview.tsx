import {
  BarChartIcon,
  BookOpenIcon,
  BusIcon,
  CalendarIcon,
  CheckIcon,
  ClipboardCheckIcon,
  GraduationCapIcon,
  QrCodeIcon,
  SparklesIcon,
  WalletIcon,
} from "./icons";

const KPIS = [
  { label: "Attendance today", value: "96.4%", note: "+1.2% this week", tone: "text-success-600 dark:text-success-400" },
  { label: "Fees collected", value: "₹4.8L", note: "82% of term", tone: "text-brand-600 dark:text-brand-300" },
  { label: "Students", value: "1,248", note: "+36 this term", tone: "text-blue-light-600 dark:text-blue-light-400" },
];

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const BARS = [72, 86, 64, 94, 80, 58];

const SCHEDULE = [
  { subject: "Mathematics", meta: "P1 · 8-A · 09:00", color: "bg-brand-500" },
  { subject: "Science lab", meta: "P2 · 9-B · 09:45", color: "bg-success-500" },
  { subject: "English", meta: "P3 · 7-C · 10:30", color: "bg-warning-400" },
];

const SIDEBAR = [BarChartIcon, ClipboardCheckIcon, CalendarIcon, BookOpenIcon, WalletIcon, BusIcon];

/** Decorative, illustrative product preview for the hero. */
export default function HeroPreview() {
  return (
    <div
      role="img"
      aria-label="Illustration of the Edusphere dashboard showing attendance, fee collection and today's timetable"
      className="relative mx-auto w-full max-w-xl lg:max-w-none"
    >
      {/* Glow */}
      <div
        aria-hidden="true"
        className="absolute -inset-6 rounded-[2.5rem] bg-gradient-to-tr from-brand-500/25 via-blue-light-400/10 to-success-400/25 blur-2xl"
      />

      {/* App window */}
      <div
        aria-hidden="true"
        className="relative overflow-hidden rounded-2xl border border-gray-200/80 bg-white shadow-2xl shadow-brand-900/10 dark:border-white/10 dark:bg-gray-900 dark:shadow-black/40"
      >
        <div className="flex items-center gap-2 border-b border-gray-100 px-4 py-3 dark:border-white/5">
          <span className="size-2.5 rounded-full bg-error-400" />
          <span className="size-2.5 rounded-full bg-warning-400" />
          <span className="size-2.5 rounded-full bg-success-400" />
          <div className="ml-3 flex-1 truncate rounded-md bg-gray-100 px-3 py-1 text-[11px] text-gray-500 dark:bg-white/5 dark:text-gray-400">
            edusphere · school dashboard
          </div>
        </div>

        <div className="flex">
          {/* Mini sidebar */}
          <div className="hidden w-14 flex-col items-center gap-2.5 border-r border-gray-100 py-4 sm:flex dark:border-white/5">
            <span className="mb-1 flex size-8 items-center justify-center rounded-lg bg-gradient-to-br from-brand-500 to-success-500 text-white">
              <GraduationCapIcon className="size-4.5" />
            </span>
            {SIDEBAR.map((Icon, i) => (
              <span
                key={i}
                className={`flex size-9 items-center justify-center rounded-lg ${
                  i === 0
                    ? "bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300"
                    : "text-gray-400 dark:text-gray-500"
                }`}
              >
                <Icon className="size-[18px]" />
              </span>
            ))}
          </div>

          {/* Main */}
          <div className="min-w-0 flex-1 p-4 sm:p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[11px] text-gray-500 dark:text-gray-400">Good morning</p>
                <p className="text-sm font-semibold text-gray-900 dark:text-white">School overview</p>
              </div>
              <span className="rounded-full bg-brand-50 px-2.5 py-1 text-[10px] font-medium text-brand-600 dark:bg-brand-500/15 dark:text-brand-300">
                AY 2026–27
              </span>
            </div>

            <div className="mt-4 grid grid-cols-3 gap-2.5">
              {KPIS.map((k) => (
                <div key={k.label} className="rounded-xl border border-gray-100 p-2.5 sm:p-3 dark:border-white/5">
                  <p className="truncate text-[10px] text-gray-500 dark:text-gray-400">{k.label}</p>
                  <p className="mt-1 text-sm font-semibold text-gray-900 sm:text-base dark:text-white">{k.value}</p>
                  <p className={`truncate text-[10px] font-medium ${k.tone}`}>{k.note}</p>
                </div>
              ))}
            </div>

            <div className="mt-2.5 grid grid-cols-5 gap-2.5">
              <div className="col-span-3 rounded-xl border border-gray-100 p-3 dark:border-white/5">
                <div className="flex items-center justify-between">
                  <p className="text-[11px] font-medium text-gray-700 dark:text-gray-300">Weekly attendance</p>
                  <span className="text-[10px] font-medium text-success-600 dark:text-success-400">+2.1%</span>
                </div>
                <div className="mt-3 flex h-24 items-end gap-1.5 sm:gap-2">
                  {BARS.map((h, i) => (
                    <div key={DAYS[i]} className="flex h-full flex-1 flex-col items-center justify-end gap-1">
                      <div
                        className="landing-bar w-full rounded-md bg-gradient-to-t from-brand-500 to-blue-light-400"
                        style={{ height: `${h}%`, animationDelay: `${300 + i * 90}ms` }}
                      />
                      <span className="text-[9px] text-gray-400">{DAYS[i]}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="col-span-2 rounded-xl border border-gray-100 p-3 dark:border-white/5">
                <p className="text-[11px] font-medium text-gray-700 dark:text-gray-300">Today</p>
                <ul className="mt-2.5 space-y-2.5">
                  {SCHEDULE.map((s) => (
                    <li key={s.subject} className="flex items-center gap-2">
                      <span className={`h-7 w-1 shrink-0 rounded-full ${s.color}`} />
                      <div className="min-w-0">
                        <p className="truncate text-[10px] font-medium text-gray-800 dark:text-gray-200">{s.subject}</p>
                        <p className="truncate text-[9px] text-gray-400">{s.meta}</p>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Floating: attendance */}
      <div
        aria-hidden="true"
        className="landing-float-delayed absolute -bottom-6 -left-2 w-56 rounded-2xl border border-gray-200/80 bg-white/90 p-3 shadow-xl shadow-gray-900/10 backdrop-blur sm:-left-10 dark:border-white/10 dark:bg-gray-900/90"
      >
        <div className="flex items-center gap-3">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-success-50 text-success-600 dark:bg-success-500/15 dark:text-success-400">
            <ClipboardCheckIcon className="size-5" />
          </span>
          <div className="min-w-0">
            <p className="text-xs font-semibold text-gray-900 dark:text-white">Attendance marked</p>
            <p className="truncate text-[11px] text-gray-500 dark:text-gray-400">Class 8-B · 32 / 34 present</p>
          </div>
        </div>
      </div>

      {/* Floating: bus QR check-in (available on the web today) */}
      <div
        aria-hidden="true"
        className="landing-float absolute -right-2 -top-7 w-56 rounded-2xl border border-gray-200/80 bg-white/90 p-3 shadow-xl shadow-gray-900/10 backdrop-blur sm:-right-8 dark:border-white/10 dark:bg-gray-900/90"
      >
        <div className="flex items-center gap-3">
          <span className="relative flex size-9 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300">
            <QrCodeIcon className="size-5" />
            <span className="absolute -right-0.5 -top-0.5 flex size-2.5">
              <span className="absolute inline-flex size-full rounded-full bg-success-400 opacity-75 motion-safe:animate-ping" />
              <span className="relative inline-flex size-2.5 rounded-full bg-success-500" />
            </span>
          </span>
          <div className="min-w-0">
            <p className="text-xs font-semibold text-gray-900 dark:text-white">Boarded Bus 12</p>
            <p className="flex items-center gap-1 truncate text-[11px] text-gray-500 dark:text-gray-400">
              <CheckIcon className="size-3 text-success-500" strokeWidth={2.5} /> QR check-in · 7:42 AM
            </p>
          </div>
        </div>
      </div>

      {/* Floating: AI tutor */}
      <div
        aria-hidden="true"
        className="landing-float absolute -bottom-10 right-6 hidden w-60 rounded-2xl border border-brand-400/30 bg-brand-950/95 p-3 shadow-xl shadow-brand-900/30 backdrop-blur sm:block"
        style={{ animationDelay: "0.8s" }}
      >
        <div className="flex items-center gap-2 text-[11px] font-semibold text-brand-200">
          <SparklesIcon className="size-4 text-blue-light-300" /> AI tutor hint
        </div>
        <p className="mt-1.5 text-[11px] leading-relaxed text-white/90">
          What's the smallest number that both 3 and 4 divide into?
        </p>
      </div>
    </div>
  );
}
