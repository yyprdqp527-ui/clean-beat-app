// 🔔 Service Worker pour les notifications push - CleanBeat
// Version: 1.1.0

const CACHE_NAME = 'cleanbeat-v133';
const OFFLINE_URL = '/static/manifest.json';

// URLs à purger du cache (anciennes images remplacées)
const PURGE_URLS = [
    '/static/icon-192.png',
    '/static/icon-512.png',
    '/static/icon-192.png?v=2',
    '/static/icon-512.png?v=2',
    '/static/icon-192.png?v=3',
    '/static/icon-512.png?v=3',
    '/static/icon-192-v3.png',
    '/static/icon-512-v3.png',
    '/static/images/cuisinewoop.webp',
    '/static/images/thumbs/cuisinewoop.webp',
    '/static/qfq-icon-192.png',
    '/static/qfq-icon-512.png',
    '/static/qfq-192.png',
    '/static/qfq-512.png',
];

const PRECACHE_URLS = [
    '/static/manifest.json',
    '/static/qfq-icon-192-v2.png',
    '/static/qfq-icon-512-v2.png',
    '/static/images/thumbs/chambreparentale_marron.webp',
    '/static/images/thumbs/chambre1.webp',
    '/static/images/thumbs/chambre2.webp',
    '/static/images/thumbs/chambre_garçon3.webp',
    '/static/images/thumbs/chambre_enfant_4.webp',
    '/static/images/thumbs/chambre_bébé4_.webp',
    '/static/images/thumbs/salonorange.webp',
    '/static/images/thumbs/cuisinewoop.webp',
    '/static/images/thumbs/sdbwoop.webp',
    '/static/images/thumbs/Wc2.webp',
    '/static/images/thumbs/buanderie5.webp',
    '/static/images/thumbs/Garage2.webp',
    '/static/socket.io.min.js',
    '/static/soundManager.js',
];

// Installation du Service Worker
self.addEventListener('install', (event) => {
    console.log('🔧 Service Worker: Installation...');

    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(PRECACHE_URLS))
            .then(() => self.skipWaiting())
    );
});

// Activation du Service Worker
self.addEventListener('activate', (event) => {
    console.log('✅ Service Worker: Activation...');
    
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('🗑️ Service Worker: Suppression ancien cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        }).then(() => {
            // Purger les URLs spécifiques du nouveau cache aussi
            return caches.open(CACHE_NAME).then((cache) => {
                return Promise.all(PURGE_URLS.map(url => cache.delete(url)));
            });
        })
    );
    
    // Prend le contrôle de tous les clients immédiatement
    return self.clients.claim();
});

// Gestion des requêtes (stratégie Network First, puis Cache)
self.addEventListener('fetch', (event) => {
    // Ignorer les requêtes non-GET
    if (event.request.method !== 'GET') return;
    
    const url = new URL(event.request.url);
    
    // 🎨 Cache First pour les avatars proxy (SVG cachés 7 jours côté serveur)
    if (url.pathname === '/api/avatar_proxy') {
        event.respondWith(
            caches.match(event.request).then((cached) => {
                if (cached) return cached;
                return fetch(event.request).then((response) => {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
                    return response;
                });
            })
        );
        return;
    }

    // 🚫 Ne JAMAIS mettre en cache les requêtes API ni les pages dynamiques
    // (les badges/compteurs/avatars doivent toujours être frais)
    if (url.pathname.startsWith('/api/') || 
        url.pathname === '/menu' || 
        url.pathname === '/comments' ||
        url.pathname === '/mes_recompenses' ||
        url.pathname === '/manage_players' ||
        url.pathname === '/rewards' ||
        url.pathname.startsWith('/edit_player/') ||
        url.pathname.startsWith('/categorie/') ||
        url.pathname.startsWith('/tasks/') ||
        url.pathname === '/') {
        event.respondWith(
            fetch(event.request).catch(() => {
                return caches.match(event.request).then((response) => {
                    return response || caches.match(OFFLINE_URL);
                });
            })
        );
        return;
    }

    // 🏠 Cache First pour TOUTES les images statiques (pièces + tâches + récompenses)
    const isStaticImage = url.pathname.startsWith('/static/images/') &&
        /\.(webp|png|jpg|jpeg)$/i.test(url.pathname);

    if (isStaticImage) {
        event.respondWith(
            caches.match(event.request).then((cached) => {
                if (cached) return cached;
                return fetch(event.request).then((response) => {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
                    return response;
                });
            })
        );
        return;
    }
    
    event.respondWith(
        fetch(event.request)
            .then((response) => {
                // Clone la réponse car elle ne peut être consommée qu'une fois
                const responseClone = response.clone();
                
                caches.open(CACHE_NAME).then((cache) => {
                    cache.put(event.request, responseClone);
                });
                
                return response;
            })
            .catch(() => {
                // Si le réseau échoue, essayer le cache
                return caches.match(event.request).then((response) => {
                    return response || caches.match(OFFLINE_URL);
                });
            })
    );
});

// ⚠️ Les notifications push sont gérées UNIQUEMENT par /sw.js pour éviter les doublons.
// Ce service worker gère uniquement le cache et le mode offline.

// ⚠️ notificationclick, notificationclose et message supprimés ici.
// Ils sont gérés uniquement par /sw.js pour éviter les doublons.

// 📨 Messages depuis le client (SKIP_WAITING uniquement, pas de badges)
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});

console.log('🚀 Service Worker: Chargé et prêt !');
