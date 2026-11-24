/**
 * Refresh button for the installed app, which has no browser reload button
 * (and on iPhone no pull-to-refresh). Not shown in a normal browser tab.
 * Reloads the current page's data; see hooks/usePageRefresh.ts.
 */
import { useState } from "react";
import { isStandalone } from "./platform";
import { requestPageRefresh } from "../../hooks/usePageRefresh";

export default function RefreshButton({ className = "" }: { className?: string }) {
    const [spinning, setSpinning] = useState(false);
    if (!isStandalone()) return null;

    const refresh = () => {
        requestPageRefresh();
        setSpinning(true);
        setTimeout(() => setSpinning(false), 700);
    };

    return (
        <button
            type="button"
            onClick={refresh}
            aria-label="Refresh this page"
            title="Refresh"
            className={`flex shrink-0 items-center justify-center rounded-full border border-gray-200 bg-white text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-white ${className}`}
        >
            <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth={1.9}
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
                className={`size-5 ${spinning ? "animate-spin" : ""}`}
            >
                <path d="M20 11a8 8 0 1 0-2.3 5.7" />
                <path d="M20 4v7h-7" />
            </svg>
        </button>
    );
}
