import { useEffect, useState } from "react";
import type { MouseEvent } from "react";
import { Link } from "react-router";
import { NAV_LINKS, scrollToSection, scrollToTop, useLoginCta } from "../landingNav";
import { ArrowRightIcon, CloseIcon, MenuIcon } from "../../../components/common/StrokeIcons";
import Logo from "../../../components/common/BrandLogo";
import InstallAppButton from "../../../components/pwa/InstallAppButton";

function NavBadge({ children }: { children: string }) {
  return (
    <span className="rounded-full bg-warning-100 px-1.5 py-px text-[10px] font-semibold uppercase tracking-wide text-warning-700 dark:bg-warning-500/15 dark:text-warning-400">
      {children}
    </span>
  );
}

export default function LandingNavbar() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const cta = useLoginCta();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const goTo = (id: string) => (e: MouseEvent) => {
    e.preventDefault();
    setOpen(false);
    scrollToSection(id);
  };

  const solid = scrolled || open;

  return (
    <header
      className={`fixed inset-x-0 top-0 z-50 border-b transition-all duration-300 ${
        solid
          ? "border-gray-200/70 bg-white/80 backdrop-blur-xl dark:border-white/10 dark:bg-gray-950/80"
          : "border-transparent bg-transparent"
      }`}
    >
      <nav
        aria-label="Main"
        className="mx-auto flex h-18 max-w-7xl items-center justify-between gap-4 px-5 sm:px-8"
      >
        <a
          href="#top"
          onClick={(e) => {
            e.preventDefault();
            setOpen(false);
            scrollToTop();
          }}
          className="flex shrink-0 items-center rounded-lg focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-500/30"
          aria-label="EduSpyre home"
        >
          <Logo />
        </a>

        <ul className="hidden items-center gap-1 lg:flex">
          {NAV_LINKS.map((link) => (
            <li key={link.id}>
              <a
                href={`#${link.id}`}
                onClick={goTo(link.id)}
                className="inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-100 hover:text-gray-900 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-500/30 dark:text-gray-300 dark:hover:bg-white/5 dark:hover:text-white"
              >
                {link.label}
                {link.badge && <NavBadge>{link.badge}</NavBadge>}
              </a>
            </li>
          ))}
        </ul>

        <div className="flex items-center gap-2 sm:gap-3">
          {/* only shown where the browser can install it, and not inside the installed app.
              Under 380px wide there's no room next to "Log in": it moves into the mobile menu below. */}
          <InstallAppButton variant="landing" className="max-[379px]:hidden" />
          <Link
            to={cta.to}
            className="group inline-flex items-center gap-1.5 rounded-full bg-brand-500 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-brand-500/25 transition hover:bg-brand-600 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-500/30 sm:px-5"
          >
            {cta.shortLabel}
            <ArrowRightIcon className="size-4 transition-transform group-hover:translate-x-0.5" />
          </Link>
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            aria-controls="landing-mobile-menu"
            aria-label={open ? "Close menu" : "Open menu"}
            className="flex size-11 items-center justify-center rounded-full border border-gray-200 bg-white text-gray-700 transition hover:bg-gray-100 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-500/30 lg:hidden dark:border-gray-800 dark:bg-gray-900 dark:text-gray-300 dark:hover:bg-gray-800"
          >
            {open ? <CloseIcon className="size-5" /> : <MenuIcon className="size-5" />}
          </button>
        </div>
      </nav>

      {/* Mobile menu */}
      <div
        id="landing-mobile-menu"
        inert={!open}
        className={`overflow-hidden transition-[max-height,opacity] duration-300 lg:hidden ${
          open ? "max-h-[28rem] opacity-100" : "max-h-0 opacity-0"
        }`}
      >
        <ul className="space-y-1 px-5 pb-5 pt-1">
          {NAV_LINKS.map((link) => (
            <li key={link.id}>
              <a
                href={`#${link.id}`}
                onClick={goTo(link.id)}
                className="flex items-center gap-2 rounded-xl px-4 py-3 text-base font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-white/5"
              >
                {link.label}
                {link.badge && <NavBadge>{link.badge}</NavBadge>}
              </a>
            </li>
          ))}
          <li className="min-[380px]:hidden">
            <InstallAppButton variant="menu" />
          </li>
        </ul>
      </div>
    </header>
  );
}
