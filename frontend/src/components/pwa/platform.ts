/** Device checks shared by the install button and push notifications. */

/** Running as the installed app (home screen / desktop app window). */
export const isStandalone = () =>
    window.matchMedia?.("(display-mode: standalone)").matches ||
    (navigator as Navigator & { standalone?: boolean }).standalone === true;

/**
 * The installed app on a phone or tablet (touchscreen). Treated as the person's own device:
 * no idle logout there. An app installed on a computer (possibly shared) doesn't count.
 */
export const isInstalledOnPhoneOrTablet = () =>
    isStandalone() && (window.matchMedia?.("(pointer: coarse)").matches || isIos());

/** iPhone / iPad. iPadOS reports itself as a Mac, so also check for touch. */
export const isIos = () =>
    /iphone|ipad|ipod/i.test(navigator.userAgent) ||
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
