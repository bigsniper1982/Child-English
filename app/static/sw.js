/* Minimal offline-friendly service worker. Caches the app shell and static
   assets; network-first for navigation so login/auth always works online. */
var CACHE = 'adventure-island-v1';
var SHELL = [
  '/static/css/style.css',
  '/static/js/tts.js',
  '/static/manifest.webmanifest',
  '/static/icons/icon.svg'
];

self.addEventListener('install', function (e) {
  e.waitUntil(caches.open(CACHE).then(function (c) { return c.addAll(SHELL); }));
  self.skipWaiting();
});

self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.map(function (k) {
      if (k !== CACHE) return caches.delete(k);
    }));
  }));
  self.clients.claim();
});

self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET') return;                 // never cache POSTs
  var url = new URL(req.url);
  if (url.pathname.indexOf('/static/') === 0) {
    // cache-first for static assets
    e.respondWith(caches.match(req).then(function (r) {
      return r || fetch(req).then(function (resp) {
        var copy = resp.clone();
        caches.open(CACHE).then(function (c) { c.put(req, copy); });
        return resp;
      });
    }));
  }
  // everything else: default network behaviour
});
