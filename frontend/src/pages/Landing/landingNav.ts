import { useEffect, useState } from "react";
import { useAuth } from "../../hooks/useAuth";

/** In-page sections shown in the navbar and footer. */
export const NAV_LINKS: { id: string; label: string; badge?: string }[] = [
  { id: "features", label: "Features" },
  { id: "roles", label: "Who it's for" },
  { id: "mobile-app", label: "Mobile app", badge: "Soon" },
  { id: "how-it-works", label: "How it works" },
  { id: "faq", label: "FAQ" },
  { id: "contact", label: "Contact" },
];

function prefersReducedMotion() {
  return window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
}

/** Smooth-scroll to an in-page section (sections use scroll-mt-* to clear the fixed navbar). */
export function scrollToSection(id: string) {
  document
    .getElementById(id)
    ?.scrollIntoView({ behavior: prefersReducedMotion() ? "auto" : "smooth", block: "start" });
}

export function scrollToTop() {
  window.scrollTo({ top: 0, behavior: prefersReducedMotion() ? "auto" : "smooth" });
}

export function usePrefersReducedMotion() {
  const [reduced, setReduced] = useState(prefersReducedMotion);
  useEffect(() => {
    const mq = window.matchMedia?.("(prefers-reduced-motion: reduce)");
    if (!mq) return;
    const onChange = () => setReduced(mq.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);
  return reduced;
}

/**
 * Primary call-to-action target. Visitors go to the login page;
 * someone who is already signed in goes straight to their dashboard.
 */
export function useLoginCta() {
  const { isAuthenticated } = useAuth();
  return isAuthenticated
    ? { to: "/dashboard", label: "Go to dashboard", shortLabel: "Dashboard", isAuthenticated }
    : { to: "/signin", label: "Log in", shortLabel: "Log in", isAuthenticated };
}
