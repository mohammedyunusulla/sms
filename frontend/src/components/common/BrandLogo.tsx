/**
 * EduSpyre logo that swaps to the light-on-dark variant in dark mode.
 * Both PNGs have transparent backgrounds and are sized for ~2x display density.
 */
export default function Logo({ className = "h-9" }: { className?: string }) {
  return (
    <>
      <img
        src="/images/logo/eduspyre/eduspyre-logo-light.png"
        alt="EduSpyre"
        width={765}
        height={256}
        className={`${className} w-auto dark:hidden`}
      />
      <img
        src="/images/logo/eduspyre/eduspyre-logo-dark.png"
        alt="EduSpyre"
        width={765}
        height={256}
        className={`${className} hidden w-auto dark:block`}
      />
    </>
  );
}
