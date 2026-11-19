import type { ComponentType } from "react";
import { CONTACT } from "../../../config/contact";
import { ExternalLinkIcon, LinkedInIcon, MailIcon, MapPinIcon } from "../../../components/common/StrokeIcons";
import type { IconProps } from "../../../components/common/StrokeIcons";
import Reveal from "./Reveal";
import SectionHeading from "./SectionHeading";

interface ContactItem {
  icon: ComponentType<IconProps>;
  label: string;
  value: string;
  href?: string;
  external?: boolean;
}

const ITEMS: ContactItem[] = [
  { icon: MailIcon, label: "Email", value: CONTACT.email, href: `mailto:${CONTACT.email}` },
  { icon: LinkedInIcon, label: "LinkedIn", value: CONTACT.linkedinLabel, href: CONTACT.linkedinUrl, external: true },
  { icon: MapPinIcon, label: "Location", value: CONTACT.location },
];

export default function ContactSection() {
  return (
    <section id="contact" className="scroll-mt-20 py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="grid items-center gap-12 lg:grid-cols-[1fr_1.3fr] lg:gap-16">
          <Reveal>
            <SectionHeading
              align="left"
              eyebrow="Contact"
              title={
                <>
                  Want Edusphere for <span className="landing-gradient-text">your school?</span>
                </>
              }
              description="Talk to the Klopterz team about bringing Edusphere to your school, or ask us anything about the platform."
            />
            <a
              href={CONTACT.contactPageUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="group mt-8 inline-flex items-center gap-2 rounded-full bg-brand-500 px-7 py-3.5 text-base font-semibold text-white shadow-xl shadow-brand-500/30 transition hover:bg-brand-600 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-500/30"
            >
              Contact us
              <ExternalLinkIcon className="size-4 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
              <span className="sr-only">(opens in a new tab)</span>
            </a>
          </Reveal>

          <ul className="grid gap-4">
            {ITEMS.map((item, i) => {
              const content = (
                <>
                  <span className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-brand-50 text-brand-600 transition-transform duration-300 group-hover:scale-110 dark:bg-brand-500/15 dark:text-brand-300">
                    <item.icon className="size-6" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-medium text-gray-500 dark:text-gray-400">{item.label}</span>
                    <span className="mt-0.5 block break-words font-semibold text-gray-900 dark:text-white">
                      {item.value}
                    </span>
                  </span>
                  {item.external && (
                    <ExternalLinkIcon className="size-4 shrink-0 text-gray-400 transition-colors group-hover:text-brand-500" />
                  )}
                </>
              );
              const cardClass =
                "group flex h-full items-center gap-5 rounded-3xl border border-gray-200 bg-white p-5 transition duration-300 sm:p-6 dark:border-white/10 dark:bg-white/[0.03]";
              return (
                <li key={item.label}>
                  <Reveal delay={i * 90} className="h-full">
                    {item.href ? (
                      <a
                        href={item.href}
                        {...(item.external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
                        className={`${cardClass} hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-xl hover:shadow-brand-500/5 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-500/30 dark:hover:border-brand-500/30`}
                      >
                        {content}
                        {item.external && <span className="sr-only">(opens in a new tab)</span>}
                      </a>
                    ) : (
                      <div className={cardClass}>{content}</div>
                    )}
                  </Reveal>
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </section>
  );
}
