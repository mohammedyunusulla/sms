/**
 * "Install app" button for the sign-in page.
 * - Chrome/Edge/Android: uses the browser's install prompt (beforeinstallprompt).
 * - iPhone/iPad Safari: there is no prompt, so we show the "Share -> Add to Home Screen" steps.
 * - Hidden when already running as the installed app, or when the browser can't install.
 */
import { useEffect, useRef, useState } from "react";
import { SmartphoneIcon } from "../common/StrokeIcons";

interface BeforeInstallPromptEvent extends Event {
    prompt: () => Promise<void>;
    userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

const isStandalone = () =>
    window.matchMedia?.("(display-mode: standalone)").matches ||
    (navigator as Navigator & { standalone?: boolean }).standalone === true;

// iPadOS reports itself as a Mac, so also check for touch.
const isIos = () =>
    /iphone|ipad|ipod/i.test(navigator.userAgent) ||
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);

const STYLES = {
    // sign-in page header
    auth: "rounded-lg border border-gray-200 bg-white/80 px-3 py-1.5 text-sm font-medium text-gray-700 hover:border-brand-300 hover:text-brand-600 focus-visible:ring-brand-500/20 dark:border-gray-700 dark:bg-gray-900/80 dark:text-gray-300 dark:hover:text-white",
    // landing page navbar: a round icon button on phones, icon + label from `sm` up
    landing:
        "h-11 justify-center rounded-full border border-gray-200 bg-white px-3 text-sm font-semibold text-gray-700 hover:bg-gray-100 focus-visible:ring-brand-500/30 max-sm:w-11 max-sm:px-0 sm:px-4 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-300 dark:hover:bg-gray-800",
    // a row inside the landing page's mobile (hamburger) menu
    menu: "w-full gap-2 rounded-xl px-4 py-3 text-base font-medium text-gray-700 hover:bg-gray-100 focus-visible:ring-brand-500/30 dark:text-gray-200 dark:hover:bg-white/5",
};

export default function InstallAppButton({
    variant = "auth",
    className = "",
}: {
    variant?: keyof typeof STYLES;
    className?: string; // extra classes for the wrapper, e.g. to show it only at some widths
}) {
    const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null);
    const [installed, setInstalled] = useState(isStandalone);
    const [showIosHelp, setShowIosHelp] = useState(false);
    const helpRef = useRef<HTMLDivElement>(null);
    const ios = isIos();

    useEffect(() => {
        const onPrompt = (e: Event) => {
            e.preventDefault(); // keep the event so our own button can trigger it
            setDeferred(e as BeforeInstallPromptEvent);
        };
        const onInstalled = () => {
            setInstalled(true);
            setDeferred(null);
        };
        window.addEventListener("beforeinstallprompt", onPrompt);
        window.addEventListener("appinstalled", onInstalled);
        return () => {
            window.removeEventListener("beforeinstallprompt", onPrompt);
            window.removeEventListener("appinstalled", onInstalled);
        };
    }, []);

    // close the iOS help when tapping elsewhere
    useEffect(() => {
        if (!showIosHelp) return;
        const close = (e: PointerEvent) => {
            if (!helpRef.current?.contains(e.target as Node)) setShowIosHelp(false);
        };
        document.addEventListener("pointerdown", close);
        return () => document.removeEventListener("pointerdown", close);
    }, [showIosHelp]);

    if (installed || (!deferred && !ios)) return null;

    const install = async () => {
        if (ios) {
            setShowIosHelp((v) => !v);
            return;
        }
        if (!deferred) return;
        await deferred.prompt();
        await deferred.userChoice;
        setDeferred(null); // the event can only be used once
    };

    return (
        <div ref={helpRef} className={`relative ${className}`}>
            <button
                type="button"
                onClick={install}
                aria-expanded={ios ? showIosHelp : undefined}
                aria-label="Install app"
                title="Install the EduSpyre app"
                className={`inline-flex shrink-0 items-center gap-1.5 transition-colors focus-visible:outline-none focus-visible:ring-4 ${STYLES[variant]}`}
            >
                <SmartphoneIcon className={variant === "landing" ? "size-4.5 sm:size-4" : "size-4"} />
                <span className={variant === "landing" ? "max-sm:hidden" : undefined}>Install app</span>
            </button>
            {ios && showIosHelp && (
                <div
                    role="dialog"
                    aria-label="Install EduSpyre on iPhone or iPad"
                    className="absolute right-0 top-full z-20 mt-2 w-64 max-sm:fixed max-sm:inset-x-4 max-sm:top-16 max-sm:w-auto rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-600 shadow-lg dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300"
                >
                    <p className="mb-2 font-semibold text-gray-800 dark:text-white">Install on iPhone / iPad</p>
                    <ol className="list-decimal space-y-1 pl-4">
                        <li>
                            Tap the <span className="font-medium">Share</span> button in Safari.
                        </li>
                        <li>
                            Choose <span className="font-medium">Add to Home Screen</span>.
                        </li>
                        <li>
                            Tap <span className="font-medium">Add</span>.
                        </li>
                    </ol>
                </div>
            )}
        </div>
    );
}
