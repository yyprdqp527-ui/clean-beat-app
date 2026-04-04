// 🔔 Service Worker pour les notifications push - CleanBeat
// Version: 1.1.0

const CACHE_NAME = 'cleanbeat-v11';
const OFFLINE_URL = '/static/manifest.json';

// Installation du Service Worker
self.addEventListener('install', (event) => {
    console.log('🔧 Service Worker: Installation...');
    
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('📦 Service Worker: Cache ouvert');
            // ⚠️ Ne PAS pré-cacher les pages dynamiques (menu, comments, /)
            // car elles contiennent des badges/données qui changent constamment
            return cache.addAll([
                '/static/manifest.json'
            ]);
        })
    );
    
    // Force le nouveau service worker à prendre le contrôle immédiatement
    self.skipWaiting();
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
    
    // 🚫 Ne JAMAIS mettre en cache les requêtes API ni les pages dynamiques
    // (les badges/compteurs/avatars doivent toujours être frais)
    // 🚫 Ne JAMAIS mettre en cache les images des pièces (elles peuvent changer)
    if (url.pathname.startsWith('/api/') || 
        url.pathname === '/menu' || 
        url.pathname === '/comments' ||
        url.pathname === '/mes_recompenses' ||
        url.pathname === '/manage_players' ||
        url.pathname === '/rewards' ||
        url.pathname.startsWith('/edit_player/') ||
        url.pathname === '/' ||
        (url.pathname.startsWith('/static/images/') && url.pathname.endsWith('.webp'))) {
        event.respondWith(
            fetch(event.request).catch(() => {
                // Fallback cache uniquement en cas d'échec réseau
                return caches.match(event.request).then((response) => {
                    return response || caches.match(OFFLINE_URL);
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

// (push handler supprimé)
self.addEventListener('push_DISABLED', (event) => {
    console.log('📬 Service Worker: Notification push reçue (désactivé - voir sw.js)');
    
    let notificationData = {
        title: 'CleanBeat',
        body: 'Vous avez un nouveau message',
        icon: '/static/images/logo.png',
        badge: '/static/images/logo.png',
        tag: 'cleanbeat-notification',
        requireInteraction: false,
        data: {
            url: '/comments'
        }
    };
    
    if (event.data) {
        try {
            const data = event.data.json();
            notificationData = {
                title: data.title || 'CleanBeat',
                body: data.body || data.message || 'Vous avez un nouveau message',
                icon: data.icon || '/static/images/logo.png',
                badge: '/static/images/logo.png',
                tag: data.tag || 'cleanbeat-notification',
                requireInteraction: data.requireInteraction || false,
                data: {
                    url: data.url || '/comments',
                    messageId: data.messageId,
                    messageType: data.messageType
                },
                actions: data.actions || [
                    {
                        action: 'open',
                        title: 'Ouvrir'
                    },
                    {
                        action: 'close',
                        title: 'Fermer'
                    }
                ]
            };
        } catch (e) {
            console.error('❌ Erreur parsing notification data:', e);
        }
    }
    
    event.waitUntil(
        self.registration.showNotification(notificationData.title, {
            body: notificationData.body,
            icon: notificationData.icon,
            badge: notificationData.badge,
            tag: notificationData.tag,
            requireInteraction: notificationData.requireInteraction,
            data: notificationData.data,
            actions: notificationData.actions,
            vibrate: [200, 100, 200],
            timestamp: Date.now()
        }).then(() => {
            // 🏠 Badge sur l'icône de l'app (écran d'accueil)
            // Dans un Service Worker, l'API Badge est sur `self`, pas `navigator`
            if ('setAppBadge' in self) {
                return self.setAppBadge(1).catch(() => {});
            }
        })
    );
});

// ⚠️ notificationclick, notificationclose et message supprimés ici.
// Ils sont gérés uniquement par /sw.js pour éviter les doublons.

// 📨 Messages depuis le client (SKIP_WAITING uniquement, pas de badges)
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});

console.log('🚀 Service Worker: Chargé et prêt !');
