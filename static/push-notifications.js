// 🔔 CleanBeat - Gestionnaire de Notifications Push
// Version: 1.0.0

class PushNotificationManager {
    constructor() {
        this.isSupported = 'serviceWorker' in navigator && 'PushManager' in window;
        this.registration = null;
        this.subscription = null;
        this.vapidPublicKey = null;
    }

    /**
     * Initialise le système de notifications
     */
    async init() {
        if (!this.isSupported) {
            console.warn('⚠️ Push notifications non supportées par ce navigateur');
            return false;
        }

        try {
            // Enregistrer le Service Worker (sw.js à la racine pour scope global + setAppBadge)
            this.registration = await navigator.serviceWorker.register('/sw.js');
            console.log('✅ Service Worker enregistré');

            // Attendre qu'il soit actif
            await navigator.serviceWorker.ready;
            console.log('✅ Service Worker prêt');

            // Récupérer la clé VAPID publique
            await this.fetchVapidKey();

            // Vérifier si déjà abonné
            this.subscription = await this.registration.pushManager.getSubscription();
            
            if (this.subscription) {
                console.log('✅ Déjà abonné aux notifications');
                // Ré-envoyer la subscription au serveur au cas où elle n'y serait pas (ex: après reset DB)
                await this.sendSubscriptionToServer(this.subscription);
                return true;
            }

            // Si permission déjà accordée → s'abonner automatiquement
            if (Notification.permission === 'granted' && this.vapidPublicKey) {
                console.log('🔄 Permission accordée, abonnement automatique...');
                await this.subscribe();
            }

            // Si permission jamais demandée → ne PAS demander automatiquement
            // iOS Safari exige un geste utilisateur pour requestPermission()
            // La demande se fait via le bouton/banner sur menu.html
            if (Notification.permission === 'default') {
                console.log('🔔 Permission notifications pas encore demandée (attente geste utilisateur)');
            }

            return true;

        } catch (error) {
            console.error('❌ Erreur initialisation notifications:', error);
            return false;
        }
    }

    /**
     * Récupère la clé publique VAPID depuis le serveur
     */
    async fetchVapidKey() {
        try {
            const response = await fetch('/api/push/vapid-public-key');
            const data = await response.json();
            
            if (data.publicKey) {
                this.vapidPublicKey = data.publicKey;
                console.log('✅ Clé VAPID récupérée');
                return true;
            } else {
                console.error('❌ Clé VAPID manquante');
                return false;
            }
        } catch (error) {
            console.error('❌ Erreur récupération clé VAPID:', error);
            return false;
        }
    }

    /**
     * Demande la permission et s'abonne aux notifications
     */
    async requestPermission() {
        if (!this.isSupported) {
            alert('❌ Votre navigateur ne supporte pas les notifications push');
            return false;
        }

        try {
            // Demander la permission
            const permission = await Notification.requestPermission();
            
            if (permission !== 'granted') {
                console.log('⚠️ Permission notifications refusée');
                return false;
            }

            console.log('✅ Permission notifications accordée');

            // S'abonner aux push notifications
            return await this.subscribe();

        } catch (error) {
            console.error('❌ Erreur demande permission:', error);
            return false;
        }
    }

    /**
     * S'abonne aux notifications push
     */
    async subscribe() {
        if (!this.registration) {
            console.error('❌ Service Worker non enregistré');
            return false;
        }

        if (!this.vapidPublicKey) {
            console.error('❌ Clé VAPID manquante');
            return false;
        }

        try {
            // Convertir la clé VAPID en Uint8Array
            const convertedVapidKey = this.urlBase64ToUint8Array(this.vapidPublicKey);

            // S'abonner
            this.subscription = await this.registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: convertedVapidKey
            });

            console.log('✅ Abonné aux push notifications');

            // Envoyer la subscription au serveur
            return await this.sendSubscriptionToServer(this.subscription);

        } catch (error) {
            console.error('❌ Erreur souscription push:', error);
            return false;
        }
    }

    /**
     * Envoie la subscription au serveur
     */
    async sendSubscriptionToServer(subscription) {
        try {
            const response = await fetch('/api/push/subscribe', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(subscription.toJSON())
            });

            const data = await response.json();

            if (data.success) {
                console.log('✅ Subscription enregistrée sur le serveur');
                return true;
            } else {
                console.error('❌ Erreur enregistrement subscription:', data.error);
                return false;
            }

        } catch (error) {
            console.error('❌ Erreur envoi subscription:', error);
            return false;
        }
    }

    /**
     * Se désabonne des notifications
     */
    async unsubscribe() {
        if (!this.subscription) {
            console.log('⚠️ Pas de subscription active');
            return true;
        }

        try {
            // Informer le serveur
            await fetch('/api/push/unsubscribe', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    endpoint: this.subscription.endpoint
                })
            });

            // Désabonner localement
            await this.subscription.unsubscribe();
            this.subscription = null;

            console.log('✅ Désabonné des notifications');
            return true;

        } catch (error) {
            console.error('❌ Erreur désinscription:', error);
            return false;
        }
    }

    /**
     * Vérifie le statut des notifications
     */
    getStatus() {
        if (!this.isSupported) {
            return 'unsupported';
        }

        if (Notification.permission === 'denied') {
            return 'denied';
        }

        if (Notification.permission === 'granted' && this.subscription) {
            return 'granted';
        }

        return 'default';
    }

    /**
     * Teste l'envoi d'une notification
     */
    async sendTestNotification() {
        try {
            const response = await fetch('/api/push/test', {
                method: 'POST'
            });

            const data = await response.json();

            if (data.success) {
                console.log('✅ Notification test envoyée');
                return true;
            } else {
                console.error('❌ Erreur envoi notification test:', data.error);
                return false;
            }

        } catch (error) {
            console.error('❌ Erreur test notification:', error);
            return false;
        }
    }

    /**
     * Utilitaire: Convertit une clé VAPID base64 en Uint8Array
     */
    urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/\-/g, '+')
            .replace(/_/g, '/');

        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);

        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }

        return outputArray;
    }

    /**
     * Affiche une notification locale (test)
     */
    async showLocalNotification(title, options = {}) {
        if (!this.isSupported || Notification.permission !== 'granted') {
            console.warn('⚠️ Notifications non autorisées');
            return;
        }

        if (!this.registration) {
            // Notification browser simple
            new Notification(title, {
                body: options.body || '',
                icon: options.icon || '/static/qfq-icon-192-v2.png',
                badge: options.badge || '/static/qfq-icon-192-v2.png'
            });
        } else {
            // Notification via Service Worker
            await this.registration.showNotification(title, {
                body: options.body || '',
                icon: options.icon || '/static/qfq-icon-192-v2.png',
                badge: options.badge || '/static/qfq-icon-192-v2.png',
                tag: options.tag || 'cleanbeat-local',
                requireInteraction: options.requireInteraction || false,
                vibrate: [200, 100, 200]
            });
        }
    }
}

// Instance globale - utiliser un nom différent de 'pushManager' car c'est une API native du navigateur
console.log('🔧 Création instance CleanBeatPushManager...');
try {
    window.cleanBeatPush = new PushNotificationManager();
    console.log('✅ Instance CleanBeatPushManager créée:', window.cleanBeatPush);
    console.log('✅ Méthode init disponible:', typeof window.cleanBeatPush.init);
} catch (error) {
    console.error('❌ Erreur création CleanBeatPushManager:', error);
    window.cleanBeatPush = null;
}

// Auto-initialisation au chargement
(function() {
    const init = async function() {
        console.log('🔔 Initialisation gestionnaire notifications CleanBeat...');
        
        // Vérifier que cleanBeatPush existe et a une méthode init
        if (!window.cleanBeatPush || typeof window.cleanBeatPush.init !== 'function') {
            console.error('❌ cleanBeatPush non disponible ou init() manquante');
            return;
        }
        
        try {
            await window.cleanBeatPush.init();
            
            // Afficher le statut dans la console
            const status = window.cleanBeatPush.getStatus();
            console.log(`📊 Statut notifications: ${status}`);
        } catch (error) {
            console.warn('⚠️ Erreur initialisation cleanBeatPush:', error);
        }
    };
    
    // Attendre que le DOM soit chargé
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        // DOM déjà chargé, exécuter au prochain tick
        setTimeout(init, 0);
    }
})();
