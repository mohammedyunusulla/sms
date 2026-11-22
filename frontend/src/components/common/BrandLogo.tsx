/**
 * EduSpyre logo that swaps to the light-on-dark variant in dark mode.
 * Both PNGs have transparent backgrounds and are sized for ~2x display density.
 * The logo is the same size everywhere (sidebar, landing page, sign-in, loader): change LOGO_HEIGHT only.
 */
export const LOGO_HEIGHT = "h-[37px]";

export default function Logo({ className = LOGO_HEIGHT }: { className?: string }) {
  return (
    <>
      <img
        src="/images/logo/eduspyre/eduspyre-logo-light.png"
        alt="EduSpyre"
        width={734}
        height={256}
        className={`${className} w-auto dark:hidden`}
      />
      <img
        src="/images/logo/eduspyre/eduspyre-logo-dark.png"
        alt="EduSpyre"
        width={734}
        height={256}
        className={`${className} hidden w-auto dark:block`}
      />
    </>
  );
}
