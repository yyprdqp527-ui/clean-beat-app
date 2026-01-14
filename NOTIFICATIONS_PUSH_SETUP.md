# 🔔 Configuration des Notifications Push - CleanBeat

## 📦 Installation des dépendances

```bash
pip install -r requirements.txt
```

## 🔑 Génération des clés VAPID

Les clés VAPID sont nécessaires pour envoyer des notifications push. Voici comment les générer :

### Méthode 1 : Avec Python

```python
from pywebpush import webpush
import json

# Générer les clés
vapid_keys = webpush.generate_vapid_keys()

print("=" * 60)
print("CLÉS VAPID GÉNÉRÉES")
print("=" * 60)
print("\nClé Privée (VAPID_PRIVATE_KEY):")
print(vapid_keys['private_key'])
print("\nClé Publique (VAPID_PUBLIC_KEY):")
print(vapid_keys['public_key'])
print("\n" + "=" * 60)
print("\n⚠️  IMPORTANT:")
print("- Gardez la clé privée SECRÈTE !")
print("- Ne la committez JAMAIS dans Git")
print("- Stockez-la dans les variables d'environnement")
print("=" * 60)

# Sauvegarder dans un fichier (à ne PAS committer)
with open('.vapid_keys.json', 'w') as f:
    json.dump(vapid_keys, f, indent=2)

print("\n✅ Clés sauvegardées dans .vapid_keys.json")
print("   Ajoutez ce fichier dans .gitignore !")
```

### Méthode 2 : Avec vapid CLI

```bash
# Installer vapid CLI
pip install py-vapid

# Générer les clés
vapid --gen

# Afficher la clé publique (à partager)
vapid --applicationServerKey

# Afficher la clé privée (à garder secrète)
vapid --sign
```

## 🔐 Configuration des variables d'environnement

### Sur votre serveur local (développement)

Créez un fichier `.env` à la racine du projet :

```bash
# .env (à ne PAS committer)
VAPID_PRIVATE_KEY="votre_clé_privée_ici"
VAPID_PUBLIC_KEY="votre_clé_publique_ici"
```

Puis chargez-les dans votre shell :

```bash
export $(cat .env | xargs)
python3 app.py
```

### Sur macOS/Linux (permanent)

Ajoutez dans votre `~/.zshrc` ou `~/.bashrc` :

```bash
export VAPID_PRIVATE_KEY="votre_clé_privée_ici"
export VAPID_PUBLIC_KEY="votre_clé_publique_ici"
```

Puis rechargez :

```bash
source ~/.zshrc  # ou source ~/.bashrc
```

### Sur Heroku

```bash
heroku config:set VAPID_PRIVATE_KEY="votre_clé_privée_ici"
heroku config:set VAPID_PUBLIC_KEY="votre_clé_publique_ici"
```

### Sur Render / Railway / autres

Ajoutez les variables d'environnement dans le panneau de configuration du service.

## 📱 Test des notifications

### 1. Démarrer l'application

```bash
python3 app.py
```

### 2. Ouvrir dans un navigateur compatible

Les notifications push fonctionnent sur :
- ✅ Chrome/Edge (Windows, macOS, Android)
- ✅ Firefox (Windows, macOS, Android)
- ✅ Safari (macOS, iOS 16.4+)
- ❌ Safari iOS < 16.4

### 3. Activer les notifications

1. Ouvrir le menu burger (☰)
2. Cliquer sur "🔔 Activer les notifications"
3. Accepter la permission quand demandé
4. Une notification de test sera envoyée automatiquement

### 4. Tester les notifications automatiques

1. Valider une tâche → Notification envoyée à tous les membres
2. Ajouter une tâche → Notification envoyée à tous les membres
3. Envoyer un message → Notification envoyée aux autres membres

## 🔧 Dépannage

### "VAPID keys non configurées"

Vérifiez que les variables d'environnement sont bien définies :

```bash
echo $VAPID_PRIVATE_KEY
echo $VAPID_PUBLIC_KEY
```

Si vides, suivez la section "Configuration des variables d'environnement" ci-dessus.

### "pywebpush non installé"

Installez les dépendances :

```bash
pip install pywebpush py-vapid
```

### Notifications ne marchent pas sur iOS

- Vérifiez la version d'iOS : doit être **16.4 ou supérieur**
- Sur iOS, l'application doit être "installée" (Add to Home Screen)
- Les notifications web ne fonctionnent pas dans Safari normal sur iOS < 16.4

### Erreur 410 (Gone)

La subscription push a expiré. Elle sera automatiquement désactivée. L'utilisateur doit se réabonner.

## 📊 Structure de la base de données

### Table `push_subscriptions`

```sql
CREATE TABLE IF NOT EXISTS push_subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_email TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    p256dh_key TEXT NOT NULL,
    auth_key TEXT NOT NULL,
    user_agent TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_used DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1,
    FOREIGN KEY(user_email) REFERENCES users(email),
    UNIQUE(user_email, endpoint)
)
```

## 🚀 Déploiement sur les App Stores

### iOS (App Store)

Pour publier sur l'App Store, vous avez 2 options :

#### Option 1 : Application native (Swift/React Native)
- Intégration native d'APNs (Apple Push Notification service)
- Nécessite un compte Apple Developer ($99/an)
- Badge sur l'icône natif

#### Option 2 : Progressive Web App (PWA)
- Ajoutez l'app à l'écran d'accueil
- Notifications push disponibles sur iOS 16.4+
- Badge affiché sur l'icône PWA
- **Gratuit** mais moins de visibilité (pas dans l'App Store)

### Android (Google Play)

#### Option 1 : Application native (Kotlin/React Native)
- Firebase Cloud Messaging (FCM)
- Badge sur l'icône natif
- Publication sur Google Play ($25 une fois)

#### Option 2 : Progressive Web App (PWA) + TWA
- Utilisez Trusted Web Activity (TWA)
- Publiez votre PWA comme app native sur le Play Store
- Notifications push via Web Push API
- Badge fonctionnel sur l'icône

**Recommandation pour CleanBeat :** Commencez avec une PWA (gratuit, rapide), puis migrez vers natif si nécessaire.

## 📚 Ressources

- [Web Push API Documentation](https://developer.mozilla.org/en-US/docs/Web/API/Push_API)
- [pywebpush Library](https://github.com/web-push-libs/pywebpush)
- [VAPID Specification](https://datatracker.ietf.org/doc/html/rfc8292)
- [PWA on iOS](https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/)

## ✅ Checklist de mise en production

- [ ] Générer les clés VAPID
- [ ] Configurer les variables d'environnement sur le serveur
- [ ] Installer les dépendances (pip install -r requirements.txt)
- [ ] Tester sur Chrome/Firefox
- [ ] Tester sur Safari macOS/iOS
- [ ] Configurer HTTPS (obligatoire pour PWA)
- [ ] Ajouter .vapid_keys.json dans .gitignore
- [ ] Vérifier que le service worker est accessible sur /static/service-worker.js
- [ ] Tester les notifications sur plusieurs devices
- [ ] Monitorer les erreurs 410 (subscriptions expirées)
