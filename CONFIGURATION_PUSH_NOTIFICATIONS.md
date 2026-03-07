# 🔔 Configuration des Notifications Push

## ✅ Clés VAPID Générées

Copie ces 3 variables d'environnement dans Render :

```
VAPID_PUBLIC_KEY=-----BEGIN PUBLIC KEY-----
MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEO379IU9upqP3LoPNnSYPs1MZFi7p
0jB+aW/43dcELh7SzZvLXNHbMNhYam8+nufJJAJcUCBLmdx5yILrFVmAqQ==
-----END PUBLIC KEY-----

VAPID_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----
MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgabiRwe/2bk7Hq0lN
wXDUBcbBwBwJJLx9sBTbHNKp/TOhRANCAAQ7fv0hT26mo/cug82dJg+zUxkWLunS
MH5pb/jd1wQuHtLNm8tc0dsw2Fhqbz6e58kkAlxQIEuZ3HnIgusVWYCp
-----END PRIVATE KEY-----

VAPID_EMAIL=mailto:ton-email@example.com
```

## 📋 Étapes de Configuration sur Render

1. **Aller dans ton service Render :**
   - Ouvre https://dashboard.render.com
   - Sélectionne ton service "clean-beat-app"

2. **Ajouter les variables d'environnement :**
   - Clique sur l'onglet **"Environment"**
   - Clique **"Add Environment Variable"**
   - Ajoute les 3 variables ci-dessus (une par une)
   - **Important** : Pour VAPID_PUBLIC_KEY et VAPID_PRIVATE_KEY, colle TOUTES les lignes incluant `-----BEGIN` et `-----END`

3. **Remplace l'email :**
   - Dans `VAPID_EMAIL`, remplace `ton-email@example.com` par **ton vrai email** (par exemple : `mailto:anne.gaelle@example.com`)

4. **Redéployer :**
   - Render va automatiquement redéployer après l'ajout des variables
   - Attends 2-3 minutes

## 📱 Comment Activer les Notifications sur Téléphone

### Pour chaque utilisateur :

1. **Ouvrir l'app sur Safari/Chrome**
2. **Installer l'app sur l'écran d'accueil** (voir instructions PWA)
3. **Ouvrir l'app depuis l'écran d'accueil**
4. **À la première ouverture**, une popup demandera : *"Autoriser les notifications ?"*
5. **Cliquer "Autoriser"** ✅

## 🎯 Résultat Final

Une fois configuré :

✅ Quand quelqu'un envoie un message, le destinataire reçoit une **vraie notification** sur son téléphone  
✅ Ça fonctionne **même si l'app est fermée**  
✅ Le message apparaît comme une notification système (comme un SMS)  
✅ En cliquant sur la notification, ça ouvre directement la messagerie  

## 🧪 Tester

1. Installe l'app sur ton téléphone
2. Autorise les notifications
3. **Ferme complètement l'app**
4. Demande à quelqu'un de t'envoyer un message
5. Tu devrais recevoir une notification push ! 🎉

## ⚠️ Notes

- **iOS Safari** : Les notifications push Web ne sont pas encore supportées sur iOS (limitation Apple)
- **Android Chrome** : Fonctionne parfaitement ✅
- **Desktop** : Fonctionne sur Chrome, Firefox, Edge ✅

### Solution pour iPhone :

Pour iPhone, les utilisateurs verront les messages instantanément quand l'app est **ouverte** (via WebSocket). Pour les notifications app fermée sur iPhone, il faudrait une vraie app native (App Store).

Alternative : Envoyer des **SMS** (payant ~0,05€/SMS) via Twilio.
