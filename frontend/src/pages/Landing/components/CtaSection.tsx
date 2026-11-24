import { Link } from "react-router";
import { CONTACT } from "../../../config/contact";
import { useLoginCta } from "../landingNav";
import { ArrowRightIcon, CalendarIcon } from "../../../components/common/StrokeIcons";
import Reveal from "./Reveal";

export default function CtaSection() {
  const cta = useLoginCta();

  return (
    <section className="px-5 pb-24 sm:px-8 sm:pb-32">
      <Reveal className="mx-auto max-w-6xl">
        <div className="relative overflow-hidden rounded-[2rem] bg-gradient-to-br from-brand-600 via-brand-700 to-brand-950 px-6 py-16 text-center shadow-2xl shadow-brand-700/20 sm:px-16 sm:py-20">
          <div aria-hidden="true" className="landing-grid-bg-light absolute inset-0" />
          <div aria-hidden="true" className="absolute -right-24 -top-24 size-80 rounded-full bg-blue-light-400/30 blur-3xl" />
          <div aria-hidden="true" className="absolute -bottom-28 -left-24 size-80 rounded-full bg-success-400/25 blur-3xl" />

          <h2 className="relative mx-auto max-w-2xl text-3xl font-bold tracking-tight text-white sm:text-5xl sm:leading-tight">
            See EduSpyre in action.
          </h2>
          <p className="relative mx-auto mt-5 max-w-xl text-lg text-brand-100">
            Book a demo with the Klopterz team and see how EduSpyre fits the way your institution works.
          </p>
          <div className="relative mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <a
              href={CONTACT.demoUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="group inline-flex w-full items-center justify-center gap-2 rounded-full bg-white px-8 py-4 text-base font-semibold text-brand-700 shadow-xl shadow-brand-950/30 transition hover:bg-brand-50 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-white/40 sm:w-auto"
            >
              <CalendarIcon className="size-5" />
              Book a demo
              <ArrowRightIcon className="size-4 transition-transform group-hover:translate-x-1" />
              <span className="sr-only">(opens in a new tab)</span>
            </a>
            <Link
              to={cta.to}
              className="inline-flex w-full items-center justify-center rounded-full border border-white/25 px-8 py-4 text-base font-semibold text-white transition hover:bg-white/10 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-white/30 sm:w-auto"
            >
              {cta.isAuthenticated ? cta.label : "Already a user? Log in"}
            </Link>
          </div>
        </div>
      </Reveal>
    </section>
  );
}
