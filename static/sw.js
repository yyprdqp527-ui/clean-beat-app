// Service Worker CleanBeat - Notifications Push

self.addEventListener('push', function(event) {
    if (!event.data) return;
    
    const data = event.data.json();
    const title = data.title || 'CleanBeat';
    const options = {
        body: data.body || '',
        icon: data.icon || '/static/images/logo.png',
        badge: '/static/images/logo.png',
        vibrate: [200, 100, 200],
        data: { url: data.url || '/', badge_count: data.badge || 1 },
        requireInteraction: false
    };
    
    event.waitUntil(
        self.registration.showNotification(title, options).then(function() {
            // 🏠 Mettre à jour le badge icône écran d'accueil
            if ('setAppBadge' in navigator) {
                return navigator.setAppBadge(data.badge || 1).catch(function(){});
            }
        })
    );
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    const url = event.notification.data.url || '/';
    
    // 🏠 Effacer le badge icône au clic sur la notification
    if ('clearAppBadge' in navigator) {
        navigator.clearAppBadge().catch(function(){});
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
