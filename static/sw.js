// Service Worker — cache des images statiques CleanBeat
const CACHE_NAME = 'cleanbeat-images-v1';

// Intercepte les requêtes d'images uniquement
self.addEventListener('fetch', function(event) {
    const url = event.request.url;
    // Mettre en cache uniquement les images statiques
    if (url.includes('/static/images/') || url.includes('/static/avatars/')) {
        event.respondWith(
            caches.open(CACHE_NAME).then(function(cache) {
                return cache.match(event.request).then(function(cached) {
                    if (cached) {
                        // Retourner depuis le cache immédiatement
                        return cached;
                    }
                    // Sinon télécharger et stocker
                    return fetch(event.request).then(function(response) {
                        if (response && response.status === 200) {
                            cache.put(event.request, response.clone());
                        }
                        return response;
                    });
                });
            })
        );
    }
});

// Nettoyer les anciens caches à la mise à jour
self.addEventListener('activate', function(event) {
    event.waitUntil(
        caches.keys().then(function(keys) {
            return Promise.all(
                keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
            );
        })
    );
});
