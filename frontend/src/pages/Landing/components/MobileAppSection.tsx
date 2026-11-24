import type { ComponentType, ReactNode } from "react";
import { usePrefersReducedMotion } from "../landingNav";
import {
  BuildingIcon,
  BusIcon,
  CalendarIcon,
  CheckIcon,
  ClipboardCheckIcon,
  GraduationCapIcon,
  HomeIcon,
  MapPinIcon,
  PencilIcon,
  QrCodeIcon,
  SmartphoneIcon,
  WalletIcon,
} from "../../../components/common/StrokeIcons";
import type { IconProps } from "../../../components/common/StrokeIcons";
import Reveal from "./Reveal";
import SectionHeading from "./SectionHeading";

interface MobileFeature {
  role: string;
  icon: ComponentType<IconProps>;
  title: string;
  body: string;
  tone: string;
}

const MOBILE_FEATURES: MobileFeature[] = [
  {
    role: "Parents",
    icon: MapPinIcon,
    title: "Live bus map",
    body: "Watch your child's bus move on the map in real time, switch between children, and keep up with timetables, assignments and fee instalments.",
    tone: "bg-success-50 text-success-600 dark:bg-success-500/15 dark:text-success-400",
  },
  {
    role: "Bus staff",
    icon: QrCodeIcon,
    title: "Background GPS & QR check-ins",
    body: "Share the bus's location even with the screen off, check students in and out with a QR scan or manual entry, and review a daily trip report.",
    tone: "bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300",
  },
  {
    role: "Teachers",
    icon: PencilIcon,
    title: "Attendance & assignments on the go",
    body: "Mark attendance from the classroom, spot students who need attention with Attendance Watch, and set assignments with text or a hand-drawn sketch.",
    tone: "bg-warning-50 text-warning-600 dark:bg-warning-500/15 dark:text-warning-400",
  },
  {
    role: "Students",
    icon: GraduationCapIcon,
    title: "The day at a glance",
    body: "Check the timetable, upcoming assignments and syllabus progress from anywhere.",
    tone: "bg-theme-purple-500/10 text-theme-purple-500 dark:bg-theme-purple-500/20",
  },
  {
    role: "Administrators",
    icon: BuildingIcon,
    title: "The admin office in your pocket",
    body: "People, classes, timetables, exams, progress cards, fees, expenses and salaries, all available on mobile.",
    tone: "bg-blue-light-50 text-blue-light-600 dark:bg-blue-light-500/15 dark:text-blue-light-400",
  },
];

function PhoneFrame({ children, dark = false }: { children: ReactNode; dark?: boolean }) {
  return (
    <div className="w-[250px] rounded-[2.6rem] bg-gray-900 p-2.5 shadow-2xl shadow-brand-900/25 ring-1 ring-white/10">
      <div
        className={`relative h-[510px] overflow-hidden rounded-[2.1rem] ${
          dark ? "bg-gray-950" : "bg-white dark:bg-gray-900"
        }`}
      >
        <div className="absolute left-1/2 top-2 z-20 h-5 w-20 -translate-x-1/2 rounded-full bg-gray-900" />
        <div
          className={`flex items-center justify-between px-6 pt-2.5 text-[10px] font-semibold ${
            dark ? "text-white" : "text-gray-900 dark:text-white"
          }`}
        >
          <span>8:12</span>
          <span className="flex items-center gap-1">
            <span className="h-2 w-3.5 rounded-[3px] border border-current p-px">
              <span className="block h-full w-2/3 rounded-[1px] bg-current" />
            </span>
          </span>
        </div>
        {children}
      </div>
    </div>
  );
}

const PHONE_ROUTE = "M40 262 C 40 200, 120 214, 120 160 S 200 104, 200 44";

const PARENT_TABS = [
  { icon: HomeIcon, label: "Home" },
  { icon: BusIcon, label: "Bus", active: true },
  { icon: CalendarIcon, label: "Timetable" },
  { icon: WalletIcon, label: "Fees" },
  { icon: ClipboardCheckIcon, label: "Assignments" },
];

/** Parent app: live bus map screen. */
function ParentBusScreen() {
  const reducedMotion = usePrefersReducedMotion();
  return (
    <PhoneFrame>
      <div className="flex items-center justify-between px-4 pt-6">
        <div>
          <p className="text-[10px] text-gray-500 dark:text-gray-400">Class 4-B</p>
          <p className="text-[15px] font-semibold text-gray-900 dark:text-white">Your bus</p>
        </div>
        <span className="flex items-center gap-1 rounded-full bg-success-50 px-2 py-0.5 text-[10px] font-semibold text-success-700 dark:bg-success-500/15 dark:text-success-400">
          <span className="size-1.5 rounded-full bg-success-500" /> Live
        </span>
      </div>

      <div className="relative mx-3 mt-3 h-[300px] overflow-hidden rounded-2xl bg-gray-50 dark:bg-gray-800/60">
        <svg viewBox="0 0 240 300" className="block h-full w-full" preserveAspectRatio="xMidYMid slice">
          <rect x="172" y="206" width="62" height="74" rx="12" className="fill-success-100 dark:fill-success-500/10" />
          <g strokeLinecap="round" strokeWidth={10} className="stroke-white dark:stroke-white/[0.06]">
            <path d="M0 82 H240" />
            <path d="M0 200 H240" />
            <path d="M82 0 V300" />
            <path d="M166 0 V300" />
          </g>
          <path d={PHONE_ROUTE} fill="none" strokeWidth={5} strokeLinecap="round" className="stroke-brand-200 dark:stroke-brand-500/30" />
          <path d={PHONE_ROUTE} fill="none" strokeWidth={5} strokeLinecap="round" className="landing-route stroke-brand-500" />
          <circle cx="40" cy="262" r="6" className="fill-white stroke-brand-500" strokeWidth={3} />
          <circle cx="120" cy="160" r="5" className="fill-white stroke-brand-400" strokeWidth={3} />
          <circle cx="200" cy="44" r="13" className="fill-success-500/20" />
          <circle cx="200" cy="44" r="7" className="fill-success-500" />
          <g transform={reducedMotion ? "translate(120 160)" : undefined}>
            <circle r="15" className="fill-brand-500/20" />
            <circle r="9" className="fill-brand-500 stroke-white dark:stroke-gray-900" strokeWidth={3} />
            {!reducedMotion && <animateMotion dur="8s" repeatCount="indefinite" path={PHONE_ROUTE} />}
          </g>
        </svg>
      </div>

      <div className="relative mx-3 -mt-8 flex items-center gap-3 rounded-2xl bg-white p-3 shadow-lg ring-1 ring-gray-100 dark:bg-gray-800 dark:ring-white/5">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-brand-500 text-white">
          <BusIcon className="size-5" />
        </span>
        <div className="min-w-0">
          <p className="text-[11px] font-semibold text-gray-900 dark:text-white">Bus 12 · On the way</p>
          <p className="text-[10px] text-gray-500 dark:text-gray-400">Location updated just now</p>
        </div>
      </div>

      <div className="absolute inset-x-0 bottom-0 flex justify-around border-t border-gray-100 bg-white px-2 pb-4 pt-2 dark:border-white/5 dark:bg-gray-900">
        {PARENT_TABS.map(({ icon: Icon, label, active }) => (
          <span
            key={label}
            className={`flex flex-col items-center gap-0.5 text-[8px] font-medium ${
              active ? "text-brand-600 dark:text-brand-300" : "text-gray-400"
            }`}
          >
            <Icon className="size-4" />
            {label}
          </span>
        ))}
      </div>
    </PhoneFrame>
  );
}

// 7×7 decorative QR-like pattern (finder squares in three corners).
const QR_PATTERN =
  "1110111" + "1010101" + "1110011" + "0101100" + "1110110" + "1010011" + "1110101";

/** Bus staff app: QR check-in / check-out screen. */
function BusStaffScanScreen() {
  return (
    <PhoneFrame dark>
      <div className="px-4 pt-6">
        <p className="text-[15px] font-semibold text-white">Bus Scan</p>
        <p className="text-[10px] text-gray-400">Scan or search to record</p>
      </div>

      <div className="relative mx-3 mt-4 flex h-[250px] items-center justify-center overflow-hidden rounded-2xl bg-gradient-to-b from-gray-800 to-gray-900">
        <div className="relative size-[140px]">
          {/* Faux QR code */}
          <div className="absolute inset-4 grid grid-cols-7 grid-rows-7 gap-[3px] opacity-60">
            {QR_PATTERN.split("").map((cell, i) => (
              <span key={i} className={`rounded-[1px] ${cell === "1" ? "bg-white" : ""}`} />
            ))}
          </div>
          {/* Frame corners */}
          <span className="absolute left-0 top-0 size-6 rounded-tl-lg border-l-[3px] border-t-[3px] border-brand-400" />
          <span className="absolute right-0 top-0 size-6 rounded-tr-lg border-r-[3px] border-t-[3px] border-brand-400" />
          <span className="absolute bottom-0 left-0 size-6 rounded-bl-lg border-b-[3px] border-l-[3px] border-brand-400" />
          <span className="absolute bottom-0 right-0 size-6 rounded-br-lg border-b-[3px] border-r-[3px] border-brand-400" />
          <span className="landing-scanline absolute inset-x-2 top-2 h-0.5 rounded-full bg-brand-400 shadow-[0_0_12px_2px_rgba(117,146,255,0.8)]" />
        </div>
        <p className="absolute bottom-3 text-[10px] text-gray-400">Align the QR code within the frame</p>
      </div>

      <div className="mx-3 mt-4 grid grid-cols-2 gap-2">
        <span className="rounded-xl bg-brand-500 py-2.5 text-center text-[11px] font-semibold text-white">Check In</span>
        <span className="rounded-xl bg-orange-500 py-2.5 text-center text-[11px] font-semibold text-white">Check Out</span>
      </div>
      <span className="mx-3 mt-2 block rounded-xl border border-white/15 py-2.5 text-center text-[11px] font-semibold text-gray-300">
        Manual Entry
      </span>

      <div className="mx-3 mt-4 flex items-center gap-2 rounded-xl bg-success-500/15 px-3 py-2 text-[10px] font-medium text-success-400 ring-1 ring-success-500/30">
        <CheckIcon className="size-3.5" strokeWidth={2.5} /> Check-in recorded · 7:42 AM
      </div>
    </PhoneFrame>
  );
}

export default function MobileAppSection() {
  return (
    <section
      id="mobile-app"
      className="scroll-mt-20 overflow-hidden bg-gradient-to-b from-white via-brand-25 to-white py-24 sm:py-32 dark:from-gray-950 dark:via-brand-950/40 dark:to-gray-950"
    >
      <div className="mx-auto grid max-w-7xl items-center gap-16 px-5 sm:px-8 lg:grid-cols-2 lg:gap-12">
        {/* Copy (first in reading order; shown on the right on desktop) */}
        <div className="lg:order-last">
          <Reveal>
            <span className="mb-5 inline-flex items-center gap-2 rounded-full border border-warning-200 bg-warning-50 px-3 py-1 text-xs font-semibold text-warning-700 dark:border-warning-500/30 dark:bg-warning-500/10 dark:text-warning-400">
              <span className="relative flex size-2">
                <span className="absolute inline-flex size-full rounded-full bg-warning-400 opacity-75 motion-safe:animate-ping" />
                <span className="relative inline-flex size-2 rounded-full bg-warning-500" />
              </span>
              Coming soon
            </span>
            <SectionHeading
              align="left"
              eyebrow="Mobile app"
              title={
                <>
                  The whole institution, <span className="landing-gradient-text">in your pocket</span>
                </>
              }
              description="The EduSpyre app for Android and iOS is on its way. It brings every role's essentials to their phone, from a live bus map for parents to QR check-ins for bus staff."
            />
          </Reveal>

          <ul className="mt-10 space-y-5">
            {MOBILE_FEATURES.map((f, i) => (
              <li key={f.title}>
                <Reveal delay={i * 70} className="flex gap-4">
                  <span className={`flex size-11 shrink-0 items-center justify-center rounded-xl ${f.tone}`}>
                    <f.icon className="size-5" />
                  </span>
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                      {f.role}
                    </p>
                    <h3 className="mt-0.5 font-semibold text-gray-900 dark:text-white">{f.title}</h3>
                    <p className="mt-1 text-sm leading-relaxed text-gray-600 dark:text-gray-400">{f.body}</p>
                  </div>
                </Reveal>
              </li>
            ))}
          </ul>
        </div>

        {/* Phones */}
        <Reveal delay={150}>
          <div
            role="img"
            aria-label="Preview of the upcoming EduSpyre mobile app: a parent's live bus map and the bus staff QR check-in screen"
            className="relative mx-auto flex w-full max-w-[540px] justify-center sm:h-[620px]"
          >
            <div
              aria-hidden="true"
              className="absolute left-1/2 top-1/2 size-[26rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-gradient-to-tr from-brand-400/30 via-blue-light-300/20 to-success-300/30 blur-3xl"
            />
            <div aria-hidden="true" className="absolute left-0 top-20 hidden -rotate-6 sm:block">
              <div className="landing-float-delayed">
                <BusStaffScanScreen />
              </div>
            </div>
            <div aria-hidden="true" className="relative z-10 sm:absolute sm:right-0 sm:top-0 sm:rotate-3">
              <div className="landing-float">
                <ParentBusScreen />
              </div>
            </div>
            <div
              aria-hidden="true"
              className="absolute -bottom-4 left-1/2 z-20 flex -translate-x-1/2 items-center gap-2 whitespace-nowrap rounded-full border border-gray-200 bg-white/90 px-4 py-2 text-xs font-semibold text-gray-700 shadow-lg backdrop-blur sm:bottom-0 sm:left-auto sm:right-12 sm:translate-x-0 dark:border-white/10 dark:bg-gray-900/90 dark:text-gray-200"
            >
              <SmartphoneIcon className="size-4 text-brand-500" /> Coming soon to Android & iOS
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
