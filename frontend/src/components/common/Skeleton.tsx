import { CSSProperties, FC } from "react";
import { cn } from "../../utils/cn";

interface SkeletonProps {
  className?: string;
  style?: CSSProperties;
}

/**
 * Shimmer placeholder block. Size/shape it with className (h-*, w-*, rounded-*).
 * The shimmer + reduced-motion handling live in the `.skeleton` CSS (index.css).
 */
const Skeleton: FC<SkeletonProps> = ({ className, style }) => (
  <div className={cn("skeleton", className)} style={style} aria-hidden="true" />
);

/** A stack of text-line skeletons; the last line is shortened for realism. */
export const SkeletonText: FC<{ lines?: number; className?: string }> = ({
  lines = 3,
  className,
}) => (
  <div className={cn("space-y-2", className)} aria-hidden="true">
    {Array.from({ length: lines }).map((_, i) => (
      <Skeleton key={i} className={cn("h-4", i === lines - 1 ? "w-2/3" : "w-full")} />
    ))}
  </div>
);

interface PageSkeletonProps {
  /** Render the title/subtitle header block. Omit when the page already shows a
   *  real PageHeader above the loading area. */
  header?: boolean;
  /** Number of small cards in the top info grid (0 to omit the grid). */
  infoCards?: number;
  /** Grid column classes for the info-card row. */
  infoCardCols?: string;
  /** Number of larger content panels rendered below the info grid. */
  panels?: number;
  /** Lines of body skeleton inside each panel. */
  panelLines?: number;
  className?: string;
}

/**
 * Full-page loading skeleton for detail/form pages: an optional header block, an
 * optional grid of small info cards, and one or more content panels. Mirrors the
 * common PageHeader + card-section layout so the page keeps its footprint while
 * loading. Set `header={false}` for pages that render a real header above the
 * loading region.
 */
export const PageSkeleton: FC<PageSkeletonProps> = ({
  header = true,
  infoCards = 0,
  infoCardCols = "grid-cols-2 sm:grid-cols-3 lg:grid-cols-6",
  panels = 2,
  panelLines = 4,
  className,
}) => (
  <div className={cn("space-y-6", className)} aria-hidden="true">
    {/* Header */}
    {header && (
      <div>
        <Skeleton className="h-7 w-56 mb-3" />
        <Skeleton className="h-4 w-80" />
      </div>
    )}

    {/* Info-card grid */}
    {infoCards > 0 && (
      <div className={cn("grid gap-4", infoCardCols)}>
        {Array.from({ length: infoCards }).map((_, i) => (
          <div
            key={i}
            className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
          >
            <Skeleton className="h-3 w-2/3 mb-2" />
            <Skeleton className="h-5 w-1/2" />
          </div>
        ))}
      </div>
    )}

    {/* Content panels */}
    {Array.from({ length: panels }).map((_, i) => (
      <div
        key={i}
        className="p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
      >
        <Skeleton className="h-4 w-40 mb-4" />
        <SkeletonText lines={panelLines} />
      </div>
    ))}
  </div>
);

export default Skeleton;
