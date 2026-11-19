import { FC } from "react";
import Skeleton from "./Skeleton";

/**
 * Fallback shown inside the app shell while a lazy route chunk loads.
 * Renders a thin top progress bar plus a lightweight content skeleton, so the
 * sidebar/header stay mounted and the content area doesn't collapse to a blank.
 */
const PageSuspenseFallback: FC = () => (
  <>
    {/* Indeterminate top progress bar (spans the viewport, above the header) */}
    <div className="fixed inset-x-0 top-0 z-999999 h-0.5 overflow-hidden bg-brand-500/15">
      <div className="h-full w-1/4 rounded-full bg-brand-500 animate-route-bar" />
    </div>

    {/* Content-area skeleton */}
    <div className="space-y-5 animate-fade-in" aria-busy="true" aria-live="polite">
      <span className="sr-only">Loading…</span>
      <Skeleton className="h-7 w-56" />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24 rounded-2xl" />
        ))}
      </div>
      <Skeleton className="h-72 rounded-2xl" />
    </div>
  </>
);

export default PageSuspenseFallback;
