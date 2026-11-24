/**
 * Registers the service worker and, when a new deploy is available, shows a
 * "New version available - Reload" toast. Without this an installed app could
 * keep running the previous build until every tab/window is closed.
 */
import { useEffect } from "react";
import toast from "react-hot-toast";
import { useRegisterSW } from "virtual:pwa-register/react";

const UPDATE_TOAST_ID = "pwa-update";
const CHECK_EVERY_MS = 60 * 60 * 1000; // look for a new deploy once an hour

export default function PwaUpdater() {
    const {
        needRefresh: [needRefresh],
        updateServiceWorker,
    } = useRegisterSW({
        onRegisteredSW(_url, registration) {
            if (!registration) return;
            setInterval(() => {
                if (navigator.onLine) registration.update().catch(() => undefined);
            }, CHECK_EVERY_MS);
        },
    });

    useEffect(() => {
        if (!needRefresh) return;
        toast(
            (t) => (
                <div className="flex items-center gap-3">
                    <span className="text-sm">A new version of EduSpyre is available.</span>
                    <button
                        type="button"
                        onClick={async () => {
                            toast.dismiss(t.id);
                            // Reload once the new version is active. Done here rather than relying on the
                            // plugin, which only reloads when the page was already controlled by a worker
                            // (not the case on someone's very first visit).
                            const waiting = (await navigator.serviceWorker?.getRegistration())?.waiting;
                            if (!waiting) {
                                window.location.reload();
                                return;
                            }
                            waiting.addEventListener("statechange", () => {
                                if (waiting.state === "activated") window.location.reload();
                            });
                            updateServiceWorker(true); // tells the waiting worker to activate
                        }}
                        className="shrink-0 rounded-lg bg-brand-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-600"
                    >
                        Reload
                    </button>
                </div>
            ),
            { id: UPDATE_TOAST_ID, duration: Infinity },
        );
    }, [needRefresh, updateServiceWorker]);

    return null;
}
