import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import svgr from "vite-plugin-svgr";
import { VitePWA } from "vite-plugin-pwa";
import type { Plugin } from "vite";

/**
 * Dev server only: answer /sw.js with a worker that deletes its caches and removes itself, then reloads the
 * open pages. A production service worker left on this address (e.g. after `vite preview` on the same port)
 * would otherwise keep serving the old build: the browser checks /sw.js for updates on every visit, so this
 * replaces it on the next page load. Production builds are not affected (apply: "serve").
 */
const SELF_REMOVING_SW = `
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.map((k) => caches.delete(k)));
    await self.registration.unregister();
    const windows = await self.clients.matchAll({ type: "window" });
    windows.forEach((w) => w.navigate(w.url));
  })());
});
`;
const removeStaleServiceWorkerInDev = (): Plugin => ({
  name: "eduspyre-remove-stale-sw-in-dev",
  apply: "serve",
  configureServer(server) {
    server.middlewares.use((req, res, next) => {
      if (req.url?.split("?")[0] !== "/sw.js") return next();
      res.setHeader("Content-Type", "text/javascript");
      res.setHeader("Cache-Control", "no-store");
      res.end(SELF_REMOVING_SW);
    });
  },
});

const ICONS = "/images/logo/eduspyre";

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    removeStaleServiceWorkerInDev(),
    react(),
    svgr({
      svgrOptions: {
        icon: true,
        // This will transform your SVG to a React component
        exportType: "named",
        namedExport: "ReactComponent",
      },
    }),
    // Installable app (PWA). The service worker caches only the app shell (HTML/JS/CSS/icons):
    // API calls are never cached, so no institution's data is ever kept on a (possibly shared) device.
    VitePWA({
      registerType: "prompt", // a new deploy shows a "New version - Reload" toast (src/components/pwa/PwaUpdater.tsx)
      injectRegister: false, // registered from PwaUpdater
      manifest: {
        id: "/",
        name: "EduSpyre",
        short_name: "EduSpyre",
        description: "One platform for your whole institution - schools, colleges and universities.",
        start_url: "/signin", // signed-in users are sent on to /dashboard
        scope: "/",
        display: "standalone",
        orientation: "any",
        theme_color: "#ffffff",
        background_color: "#ffffff",
        icons: [
          { src: `${ICONS}/eduspyre-app-icon-192.png`, sizes: "192x192", type: "image/png", purpose: "any" },
          { src: `${ICONS}/eduspyre-app-icon-512.png`, sizes: "512x512", type: "image/png", purpose: "any" },
          { src: `${ICONS}/eduspyre-maskable-192.png`, sizes: "192x192", type: "image/png", purpose: "maskable" },
          { src: `${ICONS}/eduspyre-maskable-512.png`, sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
      },
      workbox: {
        // Precache only the entry shell (~0.7 MB) so installing is light on phones.
        globPatterns: [
          "index.html",
          "assets/index-*.{js,css}",
          "assets/*.css",
          "favicon.png",
          // brand logos shown on sign-in and in the app header (~0.5 MB); the manifest icons are added by the plugin itself
          "images/logo/eduspyre/eduspyre-{favicon-192,icon,logo-light,logo-dark,logo-white}.png",
        ],
        navigateFallback: "/index.html",
        navigateFallbackDenylist: [/^\/api\//, /^\/socket\.io\//, /^\/uploads\//],
        cleanupOutdatedCaches: true,
        // push notification handlers (show + open the right page on tap)
        importScripts: ["/push-sw.js"],
        // Page chunks are cached the first time each page is opened. They are content-hashed
        // build files (no user data), so serving them from cache is always safe.
        // Nothing else has a runtime rule: /api/* always goes to the network.
        runtimeCaching: [
          {
            urlPattern: ({ url, sameOrigin }) => sameOrigin && url.pathname.startsWith("/assets/"),
            handler: "CacheFirst",
            options: {
              cacheName: "eduspyre-chunks",
              expiration: { maxEntries: 150, maxAgeSeconds: 60 * 60 * 24 * 30 },
              cacheableResponse: { statuses: [200] },
            },
          },
        ],
      },
    }),
  ],
  resolve: {
    alias: {
      "@": "/src",
    },
  },
});
