/**
 * Thin bar shown while the device has no connection. The app shell opens from
 * the service-worker cache, but all school data comes live from the API, so we
 * say so plainly instead of letting requests fail silently.
 */
import { useEffect, useState } from "react";

export default function OfflineBanner() {
    const [online, setOnline] = useState(() => navigator.onLine);

    useEffect(() => {
        const up = () => setOnline(true);
        const down = () => setOnline(false);
        window.addEventListener("online", up);
        window.addEventListener("offline", down);
        return () => {
            window.removeEventListener("online", up);
            window.removeEventListener("offline", down);
        };
    }, []);

    if (online) return null;
    return (
        <div
            role="status"
            className="fixed inset-x-0 top-0 z-[1000000] bg-gray-900 px-4 py-2 text-center text-sm font-medium text-white"
            style={{ paddingTop: "max(0.5rem, env(safe-area-inset-top))" }}
        >
            You're offline. Reconnect to continue - nothing you see will update until then.
        </div>
    );
}
