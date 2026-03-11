window.pushManager = {
    vapidPublicKey: null,
    swRegistration: null,

    getStatus() {
        if (!('serviceWorker' in navigator) || !('PushManager' in window) || !('Notification' in window)) return 'unsupported';
        if (Notification.permission === 'denied') return 'denied';
        if (Notification.permission === 'granted') return 'granted';
        return 'default';
    },

    async requestPermission() {
        console.log('🔔 requestPermission appelé');
        if (!('Notification' in window)) { console.log('❌ Notification non supporté'); return false; }
        
        // IMPORTANT iOS : requestPermission doit etre appele sans await precedent
        let permission;
        try {
            permission = await Notification.requestPermission();
            console.log('📋 Permission:', permission);
        } catch(e) {
            console.error('❌ requestPermission error:', e);
            return false;
        }
        
        if (permission !== 'granted') return false;
        
        try {
            // Charger la clé VAPID
            const resp = await fetch('/api/push/vapid-public-key');
            const data = await resp.json();
            this.vapidPublicKey = data.publicKey;
            console.log('🔑 Clé VAPID:', this.vapidPublicKey ? 'OK' : 'MANQUANTE');
            
            // Attendre le service worker
            this.swRegistration = await navigator.serviceWorker.ready;
            console.log('⚙️ ServiceWorker ready');
            
            // S abonner
            const sub = await this.swRegistration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: this.urlBase64ToUint8Array(this.vapidPublicKey)
            });
            console.log('✅ Abonné aux push');
            
            // Enregistrer sur le serveur
            await fetch('/api/push/subscribe', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(sub)
            });
            return true;
        } catch(e) {
            console.error('❌ Erreur abonnement push:', e);
            return false;
        }
    },

    async sendTestNotification() {
        try {
            const resp = await fetch('/api/push/test', {method: 'POST'});
            const data = await resp.json();
            return data.success;
        } catch(e) { return false; }
    },

    urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
        const rawData = atob(base64);
        return new Uint8Array([...rawData].map(c => c.charCodeAt(0)));
    }
};
