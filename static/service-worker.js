const CACHE_NAME = 'si-trading-v1';
const urlsToCache = [
  '/',
  '/static/css/style.css',
  '/static/js/app.js'
  // Ajoutez ici les URLs de vos pages et ressources importantes
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request))
  );
});
