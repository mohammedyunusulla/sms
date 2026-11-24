/**
 * usePageRefresh
 * Reloads the current page's data by remounting it (the page's own data fetching runs again);
 * the header, sidebar and sign-in stay as they are.
 *
 * - Manual: the header's refresh button dispatches REFRESH_EVENT (installed app only - a browser has its own reload).
 * - Automatic (installed app only): coming back to the app after more than a minute in the background.
 *   Skipped if the user has typed into a form on this page, so unsaved input is never lost.
 */
import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router";
import { isStandalone } from "../components/pwa/platform";

export const REFRESH_EVENT = "eduspyre:refresh-page";
const AUTO_REFRESH_AFTER_MS = 60_000;

export const requestPageRefresh = () => window.dispatchEvent(new Event(REFRESH_EVENT));

export function usePageRefresh(): number {
    const [refreshKey, setRefreshKey] = useState(0);
    const { pathname } = useLocation();
    const typedOnThisPage = useRef(false);
    const hiddenAt = useRef<number | null>(null);

    // a new page (or a refresh) starts with no unsaved input
    useEffect(() => {
        typedOnThisPage.current = false;
    }, [pathname, refreshKey]);

    useEffect(() => {
        const refresh = () => {
            typedOnThisPage.current = false;
            setRefreshKey((k) => k + 1);
        };
        const onInput = (e: Event) => {
            const el = e.target as HTMLElement | null;
            // typing in the header search isn't page data
            if (el && !el.closest("header")) typedOnThisPage.current = true;
        };
        const onVisibility = () => {
            if (!isStandalone()) return;
            if (document.visibilityState === "hidden") {
                hiddenAt.current = Date.now();
            } else if (hiddenAt.current !== null) {
                const away = Date.now() - hiddenAt.current;
                hiddenAt.current = null;
                if (away > AUTO_REFRESH_AFTER_MS && !typedOnThisPage.current) refresh();
            }
        };
        window.addEventListener(REFRESH_EVENT, refresh);
        document.addEventListener("input", onInput, true);
        document.addEventListener("visibilitychange", onVisibility);
        return () => {
            window.removeEventListener(REFRESH_EVENT, refresh);
            document.removeEventListener("input", onInput, true);
            document.removeEventListener("visibilitychange", onVisibility);
        };
    }, []);

    return refreshKey;
}
