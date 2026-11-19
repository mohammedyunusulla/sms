import { FC, ReactNode, SelectHTMLAttributes } from 'react';

/** Compact, unlabelled select for the toolbar (use placeholder option text). */
export const ToolbarSelect: FC<SelectHTMLAttributes<HTMLSelectElement>> = ({ className = '', ...props }) => (
  <select
    {...props}
    className={`h-10 rounded-lg border border-gray-300 bg-white px-3 text-theme-sm text-gray-700 focus:border-brand-300 focus:outline-none focus:ring-3 focus:ring-brand-500/20 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300 ${className}`}
  />
);

interface TableToolbarProps {
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  searchPlaceholder?: string;
  /** Filter controls (e.g. ToolbarSelect elements). */
  children?: ReactNode;
  resultCount?: number;
  resultLabel?: string;
  /** Shows a "Clear" link when there are active filters. */
  hasActiveFilters?: boolean;
  onClear?: () => void;
  /** Right-aligned actions (e.g. an Export button). */
  rightActions?: ReactNode;
}

/**
 * Slim, consistent filter/search bar for list pages — replaces the bulky
 * labelled 6-column filter cards each page rolled on its own.
 */
const TableToolbar: FC<TableToolbarProps> = ({
  searchValue,
  onSearchChange,
  searchPlaceholder = 'Search…',
  children,
  resultCount,
  resultLabel = 'results',
  hasActiveFilters,
  onClear,
  rightActions,
}) => {
  return (
    <div className="card p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
        {onSearchChange && (
          <div className="relative flex-1 lg:max-w-xs">
            <svg
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
              aria-hidden="true"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-4.35-4.35M17 11a6 6 0 1 1-12 0 6 6 0 0 1 12 0Z" />
            </svg>
            <input
              type="text"
              value={searchValue ?? ''}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder={searchPlaceholder}
              className="h-10 w-full rounded-lg border border-gray-300 bg-white pl-9 pr-3 text-theme-sm text-gray-700 placeholder-gray-400 focus:border-brand-300 focus:outline-none focus:ring-3 focus:ring-brand-500/20 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300"
            />
          </div>
        )}

        {children && <div className="flex flex-wrap items-center gap-2">{children}</div>}

        <div className="flex items-center gap-3 lg:ml-auto">
          {typeof resultCount === 'number' && (
            <span className="text-theme-sm text-gray-500 dark:text-gray-400">
              {resultCount.toLocaleString('en-IN')} {resultLabel}
            </span>
          )}
          {hasActiveFilters && onClear && (
            <button
              type="button"
              onClick={onClear}
              className="text-theme-sm font-medium text-brand-600 hover:text-brand-700 dark:text-brand-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40 rounded"
            >
              Clear
            </button>
          )}
          {rightActions}
        </div>
      </div>
    </div>
  );
};

export default TableToolbar;
