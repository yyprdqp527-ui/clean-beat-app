# 🚀 Guide de Démarrage Rapide - WebSockets

## ✨ Ce qui a changé

Vos points se synchronisent maintenant **INSTANTANÉMENT** entre les écrans sans rafraîchir la page !

---

## 🎯 Démarrer le Serveur

```bash
cd "/Users/anne-gaelledaval/Downloads/Appli web-2"
python3 app.py
```

**Message attendu** :
```
Démarrage de CleanBeat sur le port 8000...
🔥 Mode TEMPS RÉEL activé : WebSockets configurés
```

---

## 🧪 Tester la Synchronisation

### 1. Ouvrir 2 appareils
- **PC** : http://192.168.1.156:8000
- **Mobile** : http://192.168.1.156:8000

### 2. Se connecter avec 2 comptes différents
- Appareil 1 : Anne
- Appareil 2 : Jean

### 3. Valider une tâche sur l'appareil 1
✨ **L'appareil 2 affiche instantanément** :
- Les nouveaux points
- Une notification verte : `✨ Anne +5 pts!`
- Les barres mises à jour

---

## 🔍 Vérifier que ça Fonctionne

### Dans la console navigateur (F12) :
```
🔌 Socket.IO chargé
✅ Connecté au serveur WebSocket
✅ Rejoint la room: house_123
🔥 Points mis à jour! {player_name: "Anne", points_gained: 5}
```

### Dans le terminal serveur :
```
🔌 [WEBSOCKET] Client connecté
✅ [WEBSOCKET] anne@example.com a rejoint la room house_123
🔥 [WEBSOCKET] Émission points_updated pour house_123
```

---

## ⚡ Résolution Rapide

### ❌ Pas de message de connexion WebSocket ?
**Solution** : Vider le cache du navigateur (Ctrl+Maj+R ou Cmd+Maj+R)

### ❌ Points ne se synchronisent pas ?
**Solution** : Le système utilise automatiquement le polling (mise à jour toutes les 30s)

### ❌ Erreur au démarrage ?
**Solution** :
```bash
pip3 install --upgrade flask-socketio python-socketio
python3 app.py
```

---

## 📱 Compatibilité

✅ **Fonctionne sur** :
- Chrome / Edge
- Firefox
- Safari (PC & iPhone)
- Opera

✅ **Fonctionne avec** :
- WiFi local
- 4G / 5G (si le serveur est accessible)
- Plusieurs appareils simultanément

---

## 💡 Conseils

1. **Gardez les deux écrans ouverts** pendant le test
2. **Attendez 1-2 secondes** après le chargement de la page
3. **Consultez la console** (F12) pour voir les logs de connexion
4. **Si ça ne marche pas** : le polling prend le relais automatiquement

---

**Pour plus de détails** : Consultez `WEBSOCKET_TEMPS_REEL.md`
