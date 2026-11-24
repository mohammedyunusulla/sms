/**
 * Push notifications on this device: browser subscription + backend registration (app/api/push.py).
 * The service worker side (showing a notification, opening the page on tap) is public/push-sw.js.
 */
import { getApiClient } from "../../services/api/client";
import { API_ENDPOINTS } from "../../services/api/config";
import { isIos, isStandalone } from "./platform";

export type PushState =
    | "unsupported" // this browser can't do push
    | "needs-install" // iPhone/iPad: only works from the installed app
    | "server-off" // the server has no notification keys yet
    | "blocked" // the user blocked notifications in browser settings
    | "off"
    | "on";

export const pushSupported = () =>
    typeof window !== "undefined" && "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;

/** The browser wants the server key as bytes. */
const keyBytes = (base64Url: string) => {
    const base64 = (base64Url + "=".repeat((4 - (base64Url.length % 4)) % 4)).replace(/-/g, "+").replace(/_/g, "/");
    const raw = atob(base64);
    return Uint8Array.from(raw, (c) => c.charCodeAt(0));
};

const registration = async () => {
    // the service worker only exists in production builds; give up rather than wait forever in dev
    const timeout = new Promise<null>((resolve) => setTimeout(() => resolve(null), 8000));
    return Promise.race([navigator.serviceWorker.ready, timeout]);
};

const browserSubscription = async () => (await registration())?.pushManager.getSubscription() ?? null;

interface PushConfig {
    enabled: boolean;
    public_key: string | null;
}

/** Current state for the signed-in user on this device. */
export async function getPushState(): Promise<PushState> {
    if (isIos() && !isStandalone()) return "needs-install";
    if (!pushSupported()) return "unsupported";
    const config = (await getApiClient().get(API_ENDPOINTS.PUSH.CONFIG)) as PushConfig;
    if (!config?.enabled || !config.public_key) return "server-off";
    if (Notification.permission === "denied") return "blocked";
    if (Notification.permission !== "granted") return "off";
    const sub = await browserSubscription();
    if (!sub) return "off";
    // the browser may still hold a subscription from someone who signed out on this device
    const { subscribed } = (await getApiClient().post(API_ENDPOINTS.PUSH.STATUS, { endpoint: sub.endpoint })) as {
        subscribed: boolean;
    };
    return subscribed ? "on" : "off";
}

/** Ask permission (must run from a tap) and register this device. Returns the new state. */
export async function turnOnPush(): Promise<PushState> {
    const config = (await getApiClient().get(API_ENDPOINTS.PUSH.CONFIG)) as PushConfig;
    if (!config?.enabled || !config.public_key) return "server-off";
    const permission = await Notification.requestPermission();
    if (permission === "denied") return "blocked";
    if (permission !== "granted") return "off";
    const reg = await registration();
    if (!reg) throw new Error("The app is still loading. Try again in a moment.");
    let sub = await reg.pushManager.getSubscription();
    // a subscription made with a different server key can't be reused
    const wanted = keyBytes(config.public_key);
    const current = sub?.options?.applicationServerKey;
    if (sub && current && new Uint8Array(current).toString() !== wanted.toString()) {
        await sub.unsubscribe();
        sub = null;
    }
    if (!sub) sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: wanted });
    await getApiClient().post(API_ENDPOINTS.PUSH.SUBSCRIBE, { subscription: sub.toJSON() });
    return "on";
}

/** Stop notifications for the signed-in user on this device. */
export async function turnOffPush(): Promise<PushState> {
    const sub = await browserSubscription();
    if (sub) {
        await getApiClient().post(API_ENDPOINTS.PUSH.UNSUBSCRIBE, { endpoint: sub.endpoint }).catch(() => undefined);
        await sub.unsubscribe().catch(() => undefined);
    }
    return "off";
}

export const sendTestPush = () => getApiClient().post(API_ENDPOINTS.PUSH.TEST, {});

/**
 * Sign-out: drop this device's browser subscription so nothing more arrives for the previous user.
 * (The server also forgets the device on logout.) Never throws, never waits long.
 */
export async function clearPushOnThisDevice(): Promise<void> {
    if (!pushSupported()) return;
    const work = (async () => {
        const reg = await navigator.serviceWorker.getRegistration();
        const sub = await reg?.pushManager.getSubscription();
        await sub?.unsubscribe();
    })().catch(() => undefined);
    await Promise.race([work, new Promise((resolve) => setTimeout(resolve, 1500))]);
}
