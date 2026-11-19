import { Link } from "react-router";
import { NAV_LINKS, scrollToSection, scrollToTop, useLoginCta } from "../landingNav";
import { CONTACT } from "../contactInfo";
import { ArrowUpIcon, GlobeIcon, LinkedInIcon, MailIcon, MapPinIcon } from "./icons";
import Logo from "./Logo";

const linkClass =
  "text-gray-600 transition-colors hover:text-gray-900 dark:text-gray-400 dark:hover:text-white";

export default function LandingFooter() {
  const cta = useLoginCta();
  const year = new Date().getFullYear();

  return (
    <footer className="border-t border-gray-200 bg-white dark:border-white/10 dark:bg-gray-950">
      <div className="mx-auto max-w-7xl px-5 py-14 sm:px-8">
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-[1.6fr_1fr_1fr_1.3fr]">
          <div>
            <Logo className="h-10" />
            <p className="mt-4 max-w-sm text-sm leading-relaxed text-gray-600 dark:text-gray-400">
              Smart Education Management System, connecting administrators, teachers, parents and students on one
              platform.
            </p>
          </div>

          <nav aria-label="Footer">
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Explore</h2>
            <ul className="mt-4 space-y-3 text-sm">
              {NAV_LINKS.map((link) => (
                <li key={link.id}>
                  <a
                    href={`#${link.id}`}
                    onClick={(e) => {
                      e.preventDefault();
                      scrollToSection(link.id);
                    }}
                    className={linkClass}
                  >
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </nav>

          <div>
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Account</h2>
            <ul className="mt-4 space-y-3 text-sm">
              <li>
                <Link to={cta.to} className={linkClass}>
                  {cta.label}
                </Link>
              </li>
              {!cta.isAuthenticated && (
                <li>
                  <Link to="/forgot-password" className={linkClass}>
                    Forgot password
                  </Link>
                </li>
              )}
            </ul>
          </div>

          <div>
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Contact</h2>
            <ul className="mt-4 space-y-3 text-sm">
              <li>
                <a href={`mailto:${CONTACT.email}`} className={`inline-flex items-center gap-2 ${linkClass}`}>
                  <MailIcon className="size-4 shrink-0" /> {CONTACT.email}
                </a>
              </li>
              <li>
                <a
                  href={CONTACT.linkedinUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`inline-flex items-center gap-2 ${linkClass}`}
                >
                  <LinkedInIcon className="size-4 shrink-0" /> LinkedIn
                  <span className="sr-only">(opens in a new tab)</span>
                </a>
              </li>
              <li className="inline-flex items-center gap-2 text-gray-600 dark:text-gray-400">
                <MapPinIcon className="size-4 shrink-0" /> {CONTACT.location}
              </li>
              <li>
                <a
                  href={CONTACT.contactPageUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`inline-flex items-center gap-2 ${linkClass}`}
                >
                  <GlobeIcon className="size-4 shrink-0" /> klopterz.com/contact
                  <span className="sr-only">(opens in a new tab)</span>
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-12 flex flex-col gap-4 border-t border-gray-200 pt-8 text-sm text-gray-500 sm:flex-row sm:items-center sm:justify-between dark:border-white/10 dark:text-gray-400">
          <p>© {year} Edusphere. All rights reserved.</p>
          <button
            type="button"
            onClick={scrollToTop}
            className="inline-flex items-center gap-1.5 self-start rounded-full px-3 py-1.5 font-medium transition hover:bg-gray-100 hover:text-gray-900 sm:self-auto dark:hover:bg-white/5 dark:hover:text-white"
          >
            <ArrowUpIcon className="size-4" /> Back to top
          </button>
        </div>
      </div>
    </footer>
  );
}
