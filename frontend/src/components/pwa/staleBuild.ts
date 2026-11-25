/**
 * Recovering from a page file of an older deploy.
 *
 * Every deploy gives the app's files new names and removes the old ones. An installed app still running the
 * previous version (its service worker serves the old page until "Reload" is pressed) can then ask for a page
 * file that no longer exists, e.g. the first time someone opens a page after a deploy - and the page stays blank.
 *
 * When that happens: activate the new version if one is waiting, and reload ONCE. If it happens again within
 * 30 seconds we don't reload again (no loop); the normal error screen shows instead.
 */
const RELOADED_AT_KEY = "eduspyre.staleBuildReloadAt";
const NO_LOOP_MS = 30_000;
let recovering = false;

const CHUNK_ERROR = /Failed to fetch dynamically imported module|Importing a module script failed|error loading dynamically imported module|Unable to preload CSS/i;

/** Make a newer service worker (if the server has one) take over before reloading. */
async function activateNewVersion(): Promise<void> {
    const reg = await navigator.serviceWorker?.getRegistration();
    if (!reg) return;
    try {
        await reg.update();
    } catch {
        // offline or no new version: just reload
    }
    const worker = reg.waiting || reg.installing;
    if (!worker) return;
    await new Promise<void>((resolve) => {
        const timer = window.setTimeout(resolve, 8000);
        const check = () => {
            if (worker.state === "installed") worker.postMessage({ type: "SKIP_WAITING" });
            if (worker.state === "activated" || worker.state === "redundant") {
                window.clearTimeout(timer);
                resolve();
            }
        };
        worker.addEventListener("statechange", check);
        check();
    });
}

export function recoverFromStaleBuild(): void {
    if (recovering) return;
    const last = Number(sessionStorage.getItem(RELOADED_AT_KEY) || 0);
    if (Date.now() - last < NO_LOOP_MS) return; // already reloaded for this just now: don't loop
    recovering = true;
    sessionStorage.setItem(RELOADED_AT_KEY, String(Date.now()));
    activateNewVersion().finally(() => window.location.reload());
}

export function installStaleBuildRecovery(): void {
    // Vite fires this when a page file (or its CSS) can't be loaded
    window.addEventListener("vite:preloadError", () => recoverFromStaleBuild());
    // fallback for browsers / paths where only the failed import surfaces
    window.addEventListener("unhandledrejection", (e) => {
        const reason = e.reason as { message?: string } | string | undefined;
        const message = typeof reason === "string" ? reason : reason?.message || "";
        if (CHUNK_ERROR.test(message)) recoverFromStaleBuild();
    });
}

/**
 * Dev server only: a service worker left over from a production build on this address (e.g. after running
 * `vite preview` on the same port) keeps serving the old build. Remove it and its caches, then reload once.
 * (The dev server also answers /sw.js with a worker that removes itself - see vite.config.ts - for the case
 * where the old worker stops this code from loading at all.)
 */
export async function removeDevServiceWorkers(): Promise<void> {
    if (!("serviceWorker" in navigator)) return;
    const regs = await navigator.serviceWorker.getRegistrations();
    if (!regs.length) return;
    await Promise.all(regs.map((r) => r.unregister()));
    if ("caches" in window) {
        const keys = await caches.keys();
        await Promise.all(keys.map((k) => caches.delete(k)));
    }
    if (navigator.serviceWorker.controller) window.location.reload();
}
