// Service worker of the Baymax family app: lets the page show alerts as system notifications and be installed as an app.
// There is no offline cache on purpose: the page must always show the live state, never an old one.
self.addEventListener("install", e => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));
self.addEventListener("notificationclick", e => {
  e.notification.close();
  e.waitUntil(self.clients.matchAll({type: "window", includeUncontrolled: true}).then(cs => cs.length ? cs[0].focus() : self.clients.openWindow("/")));
});
