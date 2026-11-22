import "./auth.css";
import React from "react";
import { Link } from "react-router";
import { ArrowLeftIcon, LockIcon } from "../../components/common/StrokeIcons";
import AuthShowcase from "./AuthShowcase";

/**
 * Shared shell for sign in, sign up and forgot password.
 * The form column comes first in the DOM (reading/tab order) but is shown on
 * the right on large screens via `lg:flex-row-reverse`; the brand showcase
 * panel sits on the left. Below `lg` the panel is hidden and each form shows
 * <AuthMobileLogo /> above its heading. Heights use `dvh` so phones don't
 * scroll because of the browser's address bar.
 */
export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const year = new Date().getFullYear();

  return (
    <div className="relative min-h-dvh bg-white lg:flex lg:flex-row-reverse dark:bg-gray-950">
      <div className="relative flex min-h-dvh flex-1 flex-col">
        {/* Soft brand tint behind the top of the form column */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-x-0 top-0 h-80 bg-gradient-to-b from-brand-50/80 to-transparent dark:from-brand-500/[0.07]"
        />

        <header className="relative z-10 flex min-h-12 items-center px-5 py-3 short:py-2 sm:px-10 sm:py-5">
          <Link
            to="/"
            className="group -ml-2 inline-flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-sm font-medium text-gray-500 transition-colors hover:text-gray-800 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-500/20 dark:text-gray-400 dark:hover:text-white"
          >
            <ArrowLeftIcon className="size-4 transition-transform group-hover:-translate-x-0.5" />
            Back to home
          </Link>
        </header>

        <main className="relative z-1 flex flex-1 flex-col">{children}</main>

        {/* Single line on every width; on very narrow phones only the copyright shows */}
        <footer className="relative z-1 flex items-center justify-between gap-3 whitespace-nowrap px-5 py-3 short:py-2.5 text-[11px] text-gray-400 max-[359px]:justify-center sm:px-10 sm:py-6 sm:text-xs dark:text-gray-500">
          <span className="inline-flex items-center gap-1.5 max-[359px]:hidden">
            <LockIcon className="size-3.5" /> Protected sign-in
          </span>
          <span>© {year} EduSpyre · Built by Klopterz</span>
        </footer>
      </div>

      <AuthShowcase />
    </div>
  );
}
