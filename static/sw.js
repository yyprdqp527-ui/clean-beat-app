// Service Worker CleanBeat - Notifications Push v3

// Force le nouveau SW à prendre le contrôle immédiatement (sans attendre fermeture des onglets)
self.addEventListener('install', function(event) {
    self.skipWaiting();
});
self.addEventListener('activate', function(event) {
    event.waitUntil(self.clients.claim());
});

self.addEventListener('push', function(event) {
    if (!event.data) return;
    
    const data = event.data.json();
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
            clientList.forEach(function(client) {
                client.postMessage({ type: 'REFRESH_BADGES', badge_count: badgeCount });
                client.postMessage({ type: 'BADGE_DEBUG', ok: badgeOk, error: badgeError, count: badgeCount });
            });
        })()
    );
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    const url = event.notification.data.url || '/menu';
    
    event.waitUntil(
        clients.matchAll({ type: 'window' }).then(function(clientList) {
            // Demander à toutes les fenêtres de recalculer le badge (via /api/unread_counts)
            clientList.forEach(function(client) {
                client.postMessage({ type: 'REFRESH_BADGES' });
            });
            for (const client of clientList) {
                if (client.url.includes('/menu') && 'focus' in client) {
                    return client.focus();
                }
            }
            // Si aucune fenêtre menu ouverte, chercher n'importe quelle fenêtre
            for (const client of clientList) {
                if ('focus' in client) {
                    client.navigate(url);
                    return client.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow(url);
            }
        })
    );
});
