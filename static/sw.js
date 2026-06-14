// Service Worker CleanBeat - Notifications Push v5

const CACHE_NAME = 'qfq-cache-v1';
const STATIC_ASSETS = ['/menu', '/static/manifest.json'];

// Force le nouveau SW à prendre le contrôle immédiatement (sans attendre fermeture des onglets)
self.addEventListener('install', function(event) {
    self.skipWaiting();
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(STATIC_ASSETS))
    );
});

self.addEventListener('fetch', event => {
    if (event.request.method !== 'GET') return;
    if (event.request.url.includes('/api/')) return;
    event.respondWith(
        fetch(event.request)
            .then(response => {
                const clone = response.clone();
                caches.open(CACHE_NAME)
                    .then(cache => cache.put(event.request, clone));
                return response;
            })
            .catch(() => caches.match(event.request))
    );
});
self.addEventListener('activate', function(event) {
    event.waitUntil(self.clients.claim());
});

self.addEventListener('push', function(event) {
    if (!event.data) return;
    
    let data;
    try {
        data = event.data.json();
    } catch (e) {
        data = { title: 'QuiFaitQuoi', body: event.data.text() };
    }
    const title = data.title || 'QuiFaitQuoi';
    const badgeCount = (data.badge !== undefined && data.badge !== null) ? parseInt(data.badge, 10) : 1;
    const options = {
        body: data.body || '',
        icon: data.icon || '/static/qfq-icon-192-v2.png',
        badge: '/static/qfq-icon-192-v2.png',
        tag: 'cleanbeat-notification',   // tag unique → remplace la notif précédente
        renotify: true,                  // son/vibration même si même tag
        vibrate: [200, 100, 200],
        data: { url: data.url || '/menu', badge_count: badgeCount },
        requireInteraction: false
    };
    
    event.waitUntil(
        (async function() {
            // 1. Badge sur l'icône d'accueil — essayer plusieurs APIs
            let badgeOk = false;
            let badgeError = null;

            // API standard SW (iOS 16.4+ / Chrome)
            if (!badgeOk && 'setAppBadge' in self) {
                try {
                    await self.setAppBadge(badgeCount);
                    badgeOk = true;
                } catch(e) { badgeError = String(e); }
            }
            // Fallback : navigator accessible depuis le SW (certaines versions WebKit)
            if (!badgeOk && self.navigator && 'setAppBadge' in self.navigator) {
                try {
                    await self.navigator.setAppBadge(badgeCount);
                    badgeOk = true;
                } catch(e) { badgeError = String(e); }
            }

            // 2. Afficher la notification
            await self.registration.showNotification(title, {
                ...options,
                silent: false,
                requireInteraction: false,
                vibrate: [200, 100, 200]
            });

            // 3. Informer les fenêtres ouvertes (rafraîchissement + debug badge)
            const clientList = await self.clients.matchAll({ type: 'window' });
            const isReminder = (data.url || '').indexOf('reminder=') !== -1;
            clientList.forEach(function(client) {
                client.postMessage({ type: 'REFRESH_BADGES', badge_count: badgeCount });
                client.postMessage({ type: 'BADGE_DEBUG', ok: badgeOk, error: badgeError, count: badgeCount });
                // 🔔 Si c'est un reminder 20h, demander à TOUTES les pages
                // ouvertes d'afficher le popup (peu importe la page courante)
                if (isReminder) {
                    client.postMessage({ type: 'SHOW_REMINDER', url: data.url });
                }
            });
        })()
    );
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    const url = event.notification.data.url || '/menu';
    
    event.waitUntil(
        clients.matchAll({ type: 'window' }).then(function(clientList) {
            const isReminder = url.indexOf('reminder=') !== -1;
            // Demander à toutes les fenêtres de recalculer le badge (via /api/unread_counts)
            // Et envoyer SHOW_REMINDER pour que la page affiche le popup
            clientList.forEach(function(client) {
                client.postMessage({ type: 'REFRESH_BADGES' });
                if (isReminder) {
                    // 🔔 Le client va recevoir SHOW_REMINDER et se rediriger vers /menu?reminder=<id>
                    client.postMessage({ type: 'SHOW_REMINDER', url: url });
                }
            });
            // 🎯 Essayer client.navigate() (ne fonctionne pas sur iOS mais ok sur Android/desktop)
            for (const client of clientList) {
                if ('focus' in client) {
                    if ('navigate' in client) {
                        return client.navigate(url).then(function() { return client.focus(); }).catch(function() { return client.focus(); });
                    }
                    return client.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow(url);
            }
        })
    );
});
