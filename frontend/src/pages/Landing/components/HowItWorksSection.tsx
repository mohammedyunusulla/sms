import { BuildingIcon, DatabaseIcon, LockIcon, LogInIcon, ShieldCheckIcon, UploadIcon } from "../../../components/common/StrokeIcons";
import Reveal from "./Reveal";
import SectionHeading from "./SectionHeading";

const STEPS = [
  {
    icon: BuildingIcon,
    title: "Your institution is set up",
    body: "Your institution is registered on EduSpyre and gets its own dedicated, isolated workspace and database.",
  },
  {
    icon: UploadIcon,
    title: "Bring everyone in",
    body: "Administrators add classes, teachers, students and parents, one at a time or in bulk from a spreadsheet.",
  },
  {
    icon: LogInIcon,
    title: "Everyone logs in",
    body: "Each person signs in with their own account and lands on a dashboard made for their role.",
  },
];

const SECURITY = [
  {
    icon: DatabaseIcon,
    title: "Isolated by design",
    body: "Every institution's records live in their own database and are never mixed with another institution's.",
  },
  {
    icon: ShieldCheckIcon,
    title: "Role-based access",
    body: "People only see the pages and data their role permits, down to individual screens.",
  },
  {
    icon: LockIcon,
    title: "Protected sign-ins",
    body: "Sessions can be revoked instantly, and repeated failed logins temporarily lock the account.",
  },
];

export default function HowItWorksSection() {
  return (
    <section id="how-it-works" className="scroll-mt-20 py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <Reveal>
          <SectionHeading
            eyebrow="How it works"
            title="Up and running in three steps"
            description="No servers to manage and no complicated setup. Use EduSpyre in any browser, with a mobile app coming soon."
          />
        </Reveal>

        <div className="relative mt-16">
          {/* Connector line behind the step icons (desktop only) */}
          <div
            aria-hidden="true"
            className="absolute left-[16.66%] right-[16.66%] top-10 hidden border-t-2 border-dashed border-brand-200 md:block dark:border-brand-500/25"
          />
          <ol className="relative grid gap-12 md:grid-cols-3 md:gap-8">
            {STEPS.map((step, i) => (
              <li key={step.title}>
                <Reveal delay={i * 120} className="flex h-full flex-col items-center px-4 text-center">
                  <span className="relative flex size-20 items-center justify-center rounded-3xl border border-brand-100 bg-white shadow-lg shadow-brand-500/10 dark:border-brand-500/20 dark:bg-gray-900">
                    <step.icon className="size-8 text-brand-500 dark:text-brand-300" />
                    <span className="absolute -right-2 -top-2 flex size-7 items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-success-500 text-xs font-bold text-white shadow">
                      {i + 1}
                    </span>
                  </span>
                  <h3 className="mt-6 text-lg font-semibold text-gray-900 dark:text-white">{step.title}</h3>
                  <p className="mt-2 max-w-xs text-sm leading-relaxed text-gray-600 dark:text-gray-400">{step.body}</p>
                </Reveal>
              </li>
            ))}
          </ol>
        </div>

        <Reveal delay={100}>
          <div className="relative mt-20 overflow-hidden rounded-[2rem] bg-gray-900 px-6 py-12 sm:px-12 dark:bg-white/[0.04] dark:ring-1 dark:ring-white/10">
            <div aria-hidden="true" className="landing-grid-bg-light absolute inset-0" />
            <div aria-hidden="true" className="absolute -left-20 -top-24 size-72 rounded-full bg-brand-500/30 blur-3xl" />
            <div className="relative grid gap-10 lg:grid-cols-[1fr_2fr] lg:items-center">
              <SectionHeading
                align="left"
                inverted
                eyebrow="Security & privacy"
                title="Your institution's data stays your institution's"
              />
              <ul className="grid gap-6 sm:grid-cols-3">
                {SECURITY.map((item) => (
                  <li key={item.title}>
                    <span className="flex size-11 items-center justify-center rounded-xl bg-white/10 text-white ring-1 ring-white/15">
                      <item.icon className="size-5" />
                    </span>
                    <h3 className="mt-4 font-semibold text-white">{item.title}</h3>
                    <p className="mt-1.5 text-sm leading-relaxed text-gray-400">{item.body}</p>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
