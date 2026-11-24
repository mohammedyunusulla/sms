/**
 * Turn push notifications on/off for this device.
 * - variant "prompt": a dismissible card on the dashboard, only while notifications are off
 *   (or on iPhone, where the app must be installed first).
 * - variant "settings": the "Notifications" section of My Profile, always shown.
 * Browsers only allow the permission request from a tap, so nothing is asked on page load.
 */
import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import { Button } from "../index";
import { useAuthStore } from "../../stores/authStore";
import { getPushState, PushState, sendTestPush, turnOffPush, turnOnPush } from "./pushClient";

const BellIcon = ({ className = "size-5" }: { className?: string }) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className={className}>
        <path d="M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
        <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
    </svg>
);

const errorText = (err: unknown, fallback: string) => (err as { message?: string })?.message || fallback;

const IOS_STEPS = "Tap Share → View More or scroll down → Add to Home Screen → Add, then open EduSpyre from your home screen.";

export default function NotificationsCard({ variant }: { variant: "prompt" | "settings" }) {
    const userId = useAuthStore((s) => s.user?.id);
    const dismissKey = `eduspyre.pushPromptDismissed.${userId ?? "anon"}`;
    const [state, setState] = useState<PushState | null>(null);
    const [busy, setBusy] = useState(false);
    const [dismissed, setDismissed] = useState(() => localStorage.getItem(dismissKey) === "1");

    const refresh = useCallback(async () => {
        try {
            setState(await getPushState());
        } catch {
            setState("unsupported");
        }
    }, []);

    useEffect(() => {
        refresh();
    }, [refresh]);

    const run = async (action: () => Promise<PushState>, success?: string) => {
        setBusy(true);
        try {
            const next = await action();
            setState(next);
            if (next === "on" && success) toast.success(success);
            if (next === "blocked") toast.error("Notifications are blocked for this site in your browser settings.");
        } catch (err) {
            toast.error(errorText(err, "Couldn't change notifications. Please try again."));
        } finally {
            setBusy(false);
        }
    };

    const test = async () => {
        setBusy(true);
        try {
            await sendTestPush();
            toast.success("Test notification sent. It should arrive in a few seconds.");
        } catch (err) {
            toast.error(errorText(err, "Couldn't send a test notification"));
        } finally {
            setBusy(false);
        }
    };

    if (state === null) return null;

    if (variant === "prompt") {
        if (dismissed || (state !== "off" && state !== "needs-install")) return null;
        const dismiss = () => {
            localStorage.setItem(dismissKey, "1");
            setDismissed(true);
        };
        return (
            <div className="mb-6 flex flex-col gap-4 rounded-xl border border-brand-200 bg-brand-50 p-4 sm:flex-row sm:items-center dark:border-brand-500/30 dark:bg-brand-500/10">
                <div className="flex flex-1 items-start gap-3">
                    <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-white text-brand-600 dark:bg-gray-900 dark:text-brand-300">
                        <BellIcon />
                    </span>
                    <div>
                        <p className="font-semibold text-gray-900 dark:text-white">
                            {state === "needs-install" ? "Install the app to get notifications" : "Turn on notifications"}
                        </p>
                        <p className="text-sm text-gray-600 dark:text-gray-300">
                            {state === "needs-install"
                                ? `On iPhone and iPad, alerts only work in the installed app. ${IOS_STEPS}`
                                : "Get an alert for announcements, new homework, published results and attendance, even when EduSpyre is closed."}
                        </p>
                    </div>
                </div>
                <div className="flex shrink-0 gap-2 sm:flex-col md:flex-row">
                    {state === "off" && (
                        <Button variant="primary" size="sm" disabled={busy} onClick={() => run(turnOnPush, "Notifications are on for this device")}>
                            {busy ? "Turning on…" : "Turn on"}
                        </Button>
                    )}
                    <Button variant="secondary" size="sm" onClick={dismiss}>
                        Not now
                    </Button>
                </div>
            </div>
        );
    }

    // settings (My Profile)
    const status: Record<PushState, string> = {
        on: "On for this device. You'll get alerts for announcements, new homework, published results and attendance.",
        off: "Off for this device.",
        blocked: "Blocked in your browser settings. Allow notifications for this site there, then come back here.",
        "needs-install": `On iPhone and iPad, notifications only work in the installed app. ${IOS_STEPS}`,
        unsupported: "This browser can't show notifications. Try Chrome, Edge, Firefox or Safari.",
        "server-off": "Notifications aren't set up on the server yet.",
    };
    return (
        <div className="p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
            <h3 className="mb-1 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
                <BellIcon /> Notifications
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400" data-testid="push-status">
                {status[state]}
            </p>
            {(state === "on" || state === "off") && (
                <div className="mt-5 flex flex-wrap gap-3">
                    {state === "off" ? (
                        <Button variant="primary" disabled={busy} onClick={() => run(turnOnPush, "Notifications are on for this device")}>
                            {busy ? "Turning on…" : "Turn on notifications"}
                        </Button>
                    ) : (
                        <>
                            <Button variant="secondary" disabled={busy} onClick={test}>
                                Send a test notification
                            </Button>
                            <Button variant="secondary" disabled={busy} onClick={() => run(turnOffPush)}>
                                Turn off
                            </Button>
                        </>
                    )}
                </div>
            )}
        </div>
    );
}
