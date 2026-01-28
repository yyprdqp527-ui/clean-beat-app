const CACHE_NAME = 'cleanbeat-demo-v1';
const URLS_TO_CACHE = ['/','/index.html','/demo-data.json',
  'https://raw.githubusercontent.com/yyprdqp527-ui/clean-beat-app/main/static/avatars/avatar_boy_1.svg',
  'https://raw.githubusercontent.com/yyprdqp527-ui/clean-beat-app/main/static/avatars/dicebear_lorelei_default.svg'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(URLS_TO_CACHE))
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request).then(response => response || fetch(event.request))
  );
});
