// Service Worker CleanBeat - Notifications Push

self.addEventListener('push', function(event) {
    if (!event.data) return;
    
    const data = event.data.json();
    const title = data.title || 'CleanBeat';
    const badgeCount = (data.badge !== undefined && data.badge !== null) ? data.badge : 1;
    const options = {
        body: data.body || '',
        icon: data.icon || '/static/images/logo.png',
        badge: '/static/images/logo.png',
        tag: 'cleanbeat-notification',   // tag unique → remplace la notif précédente
        renotify: true,                  // son/vibration même si même tag
        vibrate: [200, 100, 200],
        data: { url: data.url || '/menu', badge_count: badgeCount },
        requireInteraction: false
    };
    
    // iOS exige : setAppBadge AVANT showNotification, de façon séquentielle
    event.waitUntil(
        (async function() {
            // 1. Badge sur l'icône d'accueil (iOS 16.4+, doit précéder showNotification)
            if ('setAppBadge' in self) {
                if (badgeCount > 0) {
                    await self.setAppBadge(badgeCount).catch(function(){});
                } else {
                    await self.clearAppBadge().catch(function(){});
                }
            }
            // 2. Afficher la notification
            await self.registration.showNotification(title, options);
            // 3. Demander aux fenêtres ouvertes de rafraîchir leurs badges
            const clientList = await self.clients.matchAll({ type: 'window' });
            clientList.forEach(function(client) {
                client.postMessage({ type: 'REFRESH_BADGES' });
            });
        })()
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
