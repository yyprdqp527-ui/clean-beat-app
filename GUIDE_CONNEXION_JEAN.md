# 🔧 Guide de connexion pour Jean

## ✅ Étapes pour Jean

### 1️⃣ Vérifier le WiFi
- Jean DOIT être connecté au **même réseau WiFi** que Anne-Gaëlle
- Pas de données mobiles (4G/5G) ❌
- WiFi uniquement ✅

### 2️⃣ URL à utiliser
Jean doit ouvrir **Safari** ou **Chrome** et taper exactement :

```
http://192.168.1.156:8000/menu
```

### 3️⃣ Si ça ne marche pas

**Option A - Tester la connexion de base :**
```
http://192.168.1.156:8000/ping
```
Devrait afficher "OK"

**Option B - Utiliser le code d'invitation :**
1. Obtenir le code de la maison (6 caractères)
2. Ouvrir : `http://192.168.1.156:8000/join_house?code=XXXXXX`

### 4️⃣ Problèmes courants

| Symptôme | Cause | Solution |
|----------|-------|----------|
| "Impossible de se connecter" | WiFi différent | Vérifier le nom du WiFi |
| "Délai d'attente dépassé" | Données mobiles activées | Désactiver 4G/5G |
| Page blanche | Cache du navigateur | Mode navigation privée |
| "Serveur introuvable" | Mauvaise IP | Vérifier l'adresse IP |

### 5️⃣ Commandes de diagnostic (pour Anne-Gaëlle)

**Vérifier que le serveur tourne :**
```bash
lsof -i:8000 | grep LISTEN
```

**Obtenir l'adresse IP actuelle :**
```bash
ifconfig | grep "inet " | grep -v "127.0.0.1"
```

**Tester depuis un autre appareil :**
```bash
curl http://192.168.1.156:8000/ping
```

### 6️⃣ Solution de secours

Si vraiment ça ne marche pas, **redémarrer le serveur** :

1. Dans VS Code, cliquer sur l'onglet "Lancer CleanBeat"
2. Cliquer sur l'icône 🗑️ (poubelle) pour arrêter
3. Cliquer sur ▶️ pour relancer
4. Attendre 5 secondes
5. Jean réessaye l'URL

---

## 📱 Instructions à envoyer à Jean par SMS

```
👋 Jean, pour te connecter à CleanBeat :

1️⃣ Connecte-toi au WiFi : [NOM_DU_WIFI]
2️⃣ Désactive tes données mobiles
3️⃣ Ouvre Safari
4️⃣ Tape cette adresse :
http://192.168.1.156:8000/menu

Si ça marche pas, dis-moi quel message d'erreur tu vois !
```

---

## 🔍 Logs à vérifier

Quand Jean essaye de se connecter, vous devriez voir dans les logs du serveur :
```
192.168.1.XXX - - [Date] "GET /menu HTTP/1.1" 200 -
```

Si vous ne voyez RIEN → Jean n'est pas sur le bon réseau WiFi
Si vous voyez une erreur 500 → Problème serveur
Si vous voyez 404 → Mauvaise URL
