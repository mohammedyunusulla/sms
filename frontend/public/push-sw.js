/*
 * Push notifications - loaded into the generated service worker (vite.config.ts: workbox.importScripts).
 * The backend (app/services/push_service.py) sends JSON: { title, body, url, tag }.
 */
self.addEventListener("push", (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch {
    data = { body: event.data ? event.data.text() : "" };
  }
  const title = data.title || "EduSpyre";
  event.waitUntil(
    self.registration.showNotification(title, {
      body: data.body || "",
      icon: "/images/logo/eduspyre/eduspyre-app-icon-192.png",
      badge: "/images/logo/eduspyre/eduspyre-favicon-192.png",
      tag: data.tag || undefined, // the same event never stacks twice
      renotify: Boolean(data.tag),
      data: { url: data.url || "/dashboard" },
    }),
  );
});

// Tapping a notification: reuse an open EduSpyre window if there is one, otherwise open the app.
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const target = new URL(event.notification.data?.url || "/dashboard", self.location.origin).href;
  event.waitUntil(
    (async () => {
      const windows = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
      for (const client of windows) {
        if (new URL(client.url).origin === self.location.origin) {
          await client.focus();
          if ("navigate" in client) return client.navigate(target);
          return undefined;
        }
      }
      return self.clients.openWindow(target);
    })(),
  );
});
