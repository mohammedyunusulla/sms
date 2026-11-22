import { FC } from "react";

interface AppLoaderProps {
  /** Announced to screen readers. */
  message?: string;
}

/**
 * Full-screen branded loader: EduSpyre logo with a small indeterminate
 * loading bar beneath it. Used while route chunks load and while auth state
 * is restored. Fades in after a short delay so quick loads don't flash.
 */
const AppLoader: FC<AppLoaderProps> = ({ message = "Loading…" }) => (
  <div
    role="status"
    aria-live="polite"
    className="app-loader flex min-h-screen flex-col items-center justify-center bg-white dark:bg-gray-950"
  >
    <div className="app-loader-logo">
      <img
        src="/images/logo/eduspyre/eduspyre-logo-light.png"
        alt=""
        width={931}
        height={256}
        className="h-[37px] w-auto dark:hidden"
      />
      <img
        src="/images/logo/eduspyre/eduspyre-logo-dark.png"
        alt=""
        width={931}
        height={256}
        className="hidden h-[37px] w-auto dark:block"
      />
    </div>

    <div className="mt-6 h-1 w-44 overflow-hidden rounded-full bg-brand-500/15 dark:bg-white/10">
      <div className="app-loader-bar h-full w-2/5 rounded-full bg-gradient-to-r from-brand-500 via-blue-light-500 to-success-500" />
    </div>

    <span className="sr-only">{message}</span>
  </div>
);

export default AppLoader;
