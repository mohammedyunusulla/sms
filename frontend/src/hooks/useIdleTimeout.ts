/**
 * useIdleTimeout Hook
 * Logs the user out after a period of inactivity.
 *
 * The time of the last activity is kept in localStorage (not just a timer in this page), so:
 * - activity in ANY tab counts for all tabs (one idle tab no longer logs out a user working in another);
 * - closing the tab / app doesn't skip the timeout: reopening after the limit logs out straight away.
 * Checked every 30s and whenever the page comes back to the foreground (phones pause background pages,
 * so a single long setTimeout isn't reliable).
 */

import { useEffect, useRef } from 'react';

const IDLE_EVENTS = ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart', 'click'] as const;
export const LAST_ACTIVITY_KEY = 'eduspyre.lastActivity';
/** sessionStorage: why the user was signed out, shown once by the sign-in page (survives a reload). */
export const SIGNED_OUT_REASON_KEY = 'eduspyre.signedOutReason';
const WRITE_EVERY_MS = 5_000; // don't write localStorage on every mouse move
const CHECK_EVERY_MS = 30_000;

/** Start the idle clock from now (on sign-in), so an old value from a previous session can't log the user out. */
export const markActivityNow = () => {
    try {
        localStorage.setItem(LAST_ACTIVITY_KEY, String(Date.now()));
    } catch {
        /* storage unavailable: the in-page fallback below still works */
    }
};

/** Forget the idle clock (on sign-out). */
export const clearActivity = () => {
    try {
        localStorage.removeItem(LAST_ACTIVITY_KEY);
    } catch {
        /* ignore */
    }
};

const readLastActivity = (fallback: number) => {
    try {
        const value = Number(localStorage.getItem(LAST_ACTIVITY_KEY));
        return Number.isFinite(value) && value > 0 ? value : fallback;
    } catch {
        return fallback;
    }
};

interface UseIdleTimeoutOptions {
    /** Timeout in milliseconds (default: 15 minutes) */
    timeout?: number;
    /** Callback when idle timeout is reached */
    onIdle: () => void;
    /** Whether the hook is enabled (default: true) */
    enabled?: boolean;
}

export const useIdleTimeout = ({
    timeout = 15 * 60 * 1000, // 15 minutes
    onIdle,
    enabled = true,
}: UseIdleTimeoutOptions): void => {
    const onIdleRef = useRef(onIdle);
    onIdleRef.current = onIdle;

    useEffect(() => {
        if (!enabled) return;

        let localLast = Date.now(); // used if localStorage isn't available
        let lastWrite = 0;
        let fired = false;

        // first run after sign-in or a reload: no stored time yet means "active now"
        try {
            if (!localStorage.getItem(LAST_ACTIVITY_KEY)) markActivityNow();
        } catch {
            /* ignore */
        }

        const check = () => {
            if (fired) return;
            if (Date.now() - readLastActivity(localLast) >= timeout) {
                fired = true;
                onIdleRef.current();
            }
        };

        const handleActivity = () => {
            const now = Date.now();
            localLast = now;
            if (now - lastWrite >= WRITE_EVERY_MS) {
                lastWrite = now;
                markActivityNow();
            }
        };

        const handleVisible = () => {
            if (document.visibilityState === 'visible') check();
        };

        check(); // reopened after the limit (e.g. the tab was closed) -> log out right away
        const interval = setInterval(check, CHECK_EVERY_MS);
        IDLE_EVENTS.forEach((event) => document.addEventListener(event, handleActivity, { passive: true }));
        document.addEventListener('visibilitychange', handleVisible);
        window.addEventListener('focus', check);
        window.addEventListener('pageshow', check);

        return () => {
            clearInterval(interval);
            IDLE_EVENTS.forEach((event) => document.removeEventListener(event, handleActivity));
            document.removeEventListener('visibilitychange', handleVisible);
            window.removeEventListener('focus', check);
            window.removeEventListener('pageshow', check);
        };
    }, [enabled, timeout]);
};
