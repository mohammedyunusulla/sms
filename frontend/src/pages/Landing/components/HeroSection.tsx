import { CONTACT } from "../../../config/contact";
import { scrollToSection } from "../landingNav";
import HeroPreview from "./HeroPreview";
import { ArrowRightIcon, CalendarIcon, CheckIcon, SparklesIcon } from "../../../components/common/StrokeIcons";
import Reveal from "./Reveal";

const HIGHLIGHTS = ["Role-based dashboards", "Isolated data per institution", "Mobile app coming soon"];

export default function HeroSection() {
  return (
    <section id="top" className="relative overflow-hidden pb-24 pt-32 sm:pt-40 lg:pb-32">
      {/* Background */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10">
        <div className="landing-grid-bg absolute inset-0" />
        <div className="absolute -top-48 left-1/2 h-[36rem] w-[36rem] -translate-x-[75%] rounded-full bg-brand-400/25 blur-3xl dark:bg-brand-500/20" />
        <div className="absolute -right-40 top-16 h-[28rem] w-[28rem] rounded-full bg-blue-light-300/30 blur-3xl dark:bg-blue-light-500/10" />
        <div className="absolute -left-32 bottom-0 h-[22rem] w-[22rem] rounded-full bg-success-300/20 blur-3xl dark:bg-success-500/10" />
      </div>

      <div className="mx-auto grid max-w-7xl items-center gap-20 px-5 sm:px-8 lg:grid-cols-[1.05fr_1fr] lg:gap-14">
        <div className="text-center lg:text-left">
          <Reveal>
            <span className="inline-flex items-center gap-2 rounded-full border border-brand-200 bg-white/70 py-1 pl-1 pr-3 text-xs font-medium text-brand-700 shadow-sm backdrop-blur dark:border-brand-500/30 dark:bg-brand-500/10 dark:text-brand-200">
              <span className="flex size-5 items-center justify-center rounded-full bg-brand-500 text-white">
                <SparklesIcon className="size-3" strokeWidth={2.25} />
              </span>
              New: AI homework tutor for students
            </span>
          </Reveal>

          <Reveal delay={80}>
            <h1 className="mt-6 text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl lg:text-6xl lg:leading-[1.08] dark:text-white">
              Run your whole institution <span className="landing-gradient-text">from one place.</span>
            </h1>
          </Reveal>

          <Reveal delay={160}>
            <p className="mx-auto mt-6 max-w-xl text-lg leading-relaxed text-gray-600 lg:mx-0 dark:text-gray-400">
              <strong className="font-semibold text-gray-900 dark:text-white">EduSpyre</strong> brings attendance, timetables, exams, fees, homework and campus transport together,
              with a dashboard tailored to every administrator, teacher, parent and student.
            </p>
          </Reveal>

          <Reveal delay={240}>
            <div className="mt-10 flex flex-col items-center gap-3 sm:flex-row sm:justify-center lg:justify-start">
              <a
                href={CONTACT.demoUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="group inline-flex w-full items-center justify-center gap-2 rounded-full bg-brand-500 px-7 py-3.5 text-base font-semibold text-white shadow-xl shadow-brand-500/30 transition hover:bg-brand-600 hover:shadow-brand-500/40 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-500/30 sm:w-auto"
              >
                <CalendarIcon className="size-5" />
                Book a demo
                <ArrowRightIcon className="size-4 transition-transform group-hover:translate-x-1" />
                <span className="sr-only">(opens in a new tab)</span>
              </a>
              <a
                href="#features"
                onClick={(e) => {
                  e.preventDefault();
                  scrollToSection("features");
                }}
                className="inline-flex w-full items-center justify-center gap-2 rounded-full border border-gray-300 bg-white/70 px-7 py-3.5 text-base font-semibold text-gray-800 backdrop-blur transition hover:border-gray-400 hover:bg-white focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-gray-300/50 sm:w-auto dark:border-white/15 dark:bg-white/5 dark:text-white dark:hover:bg-white/10"
              >
                Explore features
              </a>
            </div>
          </Reveal>

          <Reveal delay={320}>
            <ul className="mt-10 flex flex-wrap justify-center gap-x-6 gap-y-3 text-sm text-gray-600 lg:justify-start dark:text-gray-400">
              {HIGHLIGHTS.map((item) => (
                <li key={item} className="flex items-center gap-2">
                  <span className="flex size-5 items-center justify-center rounded-full bg-success-100 text-success-600 dark:bg-success-500/15 dark:text-success-400">
                    <CheckIcon className="size-3.5" strokeWidth={2.5} />
                  </span>
                  {item}
                </li>
              ))}
            </ul>
          </Reveal>
        </div>

        <Reveal delay={200} className="relative">
          <HeroPreview />
        </Reveal>
      </div>
    </section>
  );
}
