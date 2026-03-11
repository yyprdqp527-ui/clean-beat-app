window.pushManager = {
    vapidPublicKey: null,
    swRegistration: null,

    async init() {
        if (!('serviceWorker' in navigator) || !('PushManager' in window)) return false;
        try {
            const resp = await fetch('/api/push/vapid-public-key');
            const data = await resp.json();
            this.vapidPublicKey = data.public_key;
            this.swRegistration = await navigator.serviceWorker.ready;
            return true;
        } catch(e) { return false; }
    },

    getStatus() {
        if (!('serviceWorker' in navigator) || !('PushManager' in window)) return 'unsupported';
        if (Notification.permission === 'denied') return 'denied';
        if (Notification.permission === 'granted') return 'granted';
        return 'default';
    },

    async requestPermission() {
        try {
            await this.init();
            const permission = await Notification.requestPermission();
            if (permission !== 'granted') return false;
            const sub = await this.swRegistration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: this.urlBase64ToUint8Array(this.vapidPublicKey)
            });
            await fetch('/api/push/subscribe', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(sub)
            });
            return true;
        } catch(e) { console.error('Push error:', e); return false; }
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
