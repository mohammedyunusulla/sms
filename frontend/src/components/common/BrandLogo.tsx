/**
 * Edusphere wordmark that swaps to the light-on-dark variant in dark mode.
 * Uses landing-specific copies of the logo: the light one has a transparent
 * background (the original is opaque white) and the dark one has the stray
 * corner sparkle removed. Both are trimmed and sized for ~2x display density.
 */
export default function Logo({ className = "h-9" }: { className?: string }) {
  return (
    <>
      <img
        src="/images/logo/edusphere-light-transparent.png"
        alt="Edusphere"
        width={332}
        height={96}
        className={`${className} w-auto dark:hidden`}
      />
      <img
        src="/images/logo/edusphere-dark-clean.png"
        alt="Edusphere"
        width={331}
        height={96}
        className={`${className} hidden w-auto dark:block`}
      />
    </>
  );
}
