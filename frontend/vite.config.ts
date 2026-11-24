import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import svgr from "vite-plugin-svgr";
import { VitePWA } from "vite-plugin-pwa";

const ICONS = "/images/logo/eduspyre";

// https://vite.dev/config/
export default defineConfig({
  plugins: [
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
    // API calls are never cached, so no school's data is ever kept on a (possibly shared) device.
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
