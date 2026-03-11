// Service Worker CleanBeat - Notifications Push

self.addEventListener('push', function(event) {
    if (!event.data) return;
    
    const data = event.data.json();
    const title = data.title || 'CleanBeat';
    const options = {
        body: data.body || '',
        icon: data.icon || '/static/icon-192.png',
        badge: '/static/icon-192.png',
        vibrate: [200, 100, 200],
        data: { url: data.url || '/' },
        requireInteraction: false
    };
    
    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    const url = event.notification.data.url || '/';
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
