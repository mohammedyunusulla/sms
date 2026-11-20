import { useState } from "react";
import type { ReactNode } from "react";
import { Link } from "react-router";
import { ChevronDownIcon } from "../../../components/common/StrokeIcons";
import Reveal from "./Reveal";
import SectionHeading from "./SectionHeading";

const linkClass = "font-medium text-brand-600 underline-offset-4 hover:underline dark:text-brand-400";

const FAQS: { q: string; a: ReactNode }[] = [
  {
    q: "How do I get my login details?",
    a: "Accounts are created by your school's administrator. If you haven't received your username and password, please contact your school office.",
  },
  {
    q: "I forgot my password. What should I do?",
    a: (
      <>
        Use{" "}
        <Link to="/forgot-password" className={linkClass}>
          Forgot password
        </Link>{" "}
        on the login page, or ask your school administrator to reset it for you.
      </>
    ),
  },
  {
    q: "Can parents see where the school bus is?",
    a: "Live map tracking for parents is coming soon in the EduSpyre mobile app. Today, bus staff already check each student in and out of the bus with a QR scan, and the school can review daily boarding reports.",
  },
  {
    q: "Is our school's data kept separate from other schools?",
    a: "Yes. Every school on EduSpyre has its own dedicated database, so records are never mixed between schools. Within a school, each person only sees what their role allows.",
  },
  {
    q: "Can I use EduSpyre on my phone?",
    a: "Yes. EduSpyre works in any modern browser on desktop, tablet or phone. A dedicated EduSpyre mobile app for Android and iOS is coming soon.",
  },
];

export default function FaqSection() {
  const [open, setOpen] = useState<number | null>(0);

  return (
    <section id="faq" className="scroll-mt-20 bg-gray-50 py-24 sm:py-32 dark:bg-white/[0.02]">
      <div className="mx-auto max-w-3xl px-5 sm:px-8">
        <Reveal>
          <SectionHeading eyebrow="FAQ" title="Questions, answered" />
        </Reveal>

        <Reveal delay={100}>
          <ul className="mt-12 space-y-3">
            {FAQS.map((item, i) => {
              const isOpen = open === i;
              const buttonId = `faq-q-${i}`;
              const panelId = `faq-a-${i}`;
              return (
                <li
                  key={item.q}
                  className={`rounded-2xl border bg-white transition-colors dark:bg-gray-900 ${
                    isOpen
                      ? "border-brand-200 shadow-lg shadow-brand-500/5 dark:border-brand-500/30"
                      : "border-gray-200 dark:border-white/10"
                  }`}
                >
                  <h3>
                    <button
                      type="button"
                      id={buttonId}
                      aria-expanded={isOpen}
                      aria-controls={panelId}
                      onClick={() => setOpen(isOpen ? null : i)}
                      className="flex w-full items-center justify-between gap-4 rounded-2xl px-6 py-5 text-left text-base font-semibold text-gray-900 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-500/30 dark:text-white"
                    >
                      {item.q}
                      <span
                        className={`flex size-8 shrink-0 items-center justify-center rounded-full transition ${
                          isOpen
                            ? "rotate-180 bg-brand-500 text-white"
                            : "bg-gray-100 text-gray-500 dark:bg-white/5 dark:text-gray-400"
                        }`}
                      >
                        <ChevronDownIcon className="size-4" strokeWidth={2.25} />
                      </span>
                    </button>
                  </h3>
                  <div
                    id={panelId}
                    role="region"
                    aria-labelledby={buttonId}
                    inert={!isOpen}
                    className={`grid transition-[grid-template-rows] duration-300 ease-out ${
                      isOpen ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
                    }`}
                  >
                    <div className="overflow-hidden">
                      <p className="px-6 pb-6 leading-relaxed text-gray-600 dark:text-gray-400">{item.a}</p>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        </Reveal>
      </div>
    </section>
  );
}
