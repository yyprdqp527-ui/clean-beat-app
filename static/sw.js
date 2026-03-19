// Service Worker CleanBeat - Notifications Push

self.addEventListener('push', function(event) {
    if (!event.data) return;
    
    const data = event.data.json();
    const title = data.title || 'CleanBeat';
    const badgeCount = data.badge || 1;
    const options = {
        body: data.body || '',
        icon: data.icon || '/static/images/logo.png',
        badge: '/static/images/logo.png',
        vibrate: [200, 100, 200],
        data: { url: data.url || '/', badge_count: badgeCount },
        requireInteraction: false
    };
    
    event.waitUntil(
        Promise.all([
            // 🏠 Badge icône AVANT showNotification pour ne pas dépasser le budget iOS
            ('setAppBadge' in self) ? self.setAppBadge(badgeCount).catch(function(){}) : Promise.resolve(),
            self.registration.showNotification(title, options),
            // Demander à toutes les fenêtres ouvertes de rafraîchir leurs badges
            self.clients.matchAll({ type: 'window' }).then(function(clients) {
                clients.forEach(function(client) {
                    client.postMessage({ type: 'REFRESH_BADGES' });
                });
            })
        ])
    );
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    const url = event.notification.data.url || '/';
    
    // 🏠 Effacer le badge icône au clic sur la notification
    if ('clearAppBadge' in self) {
        self.clearAppBadge().catch(function(){});
    }
    
    event.waitUntil(
        clients.matchAll({ type: 'window' }).then(function(clientList) {
            for (const client of clientList) {
                if (client.url === url && 'focus' in client) {
                    return client.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow(url);
            }
        })
    );
});
