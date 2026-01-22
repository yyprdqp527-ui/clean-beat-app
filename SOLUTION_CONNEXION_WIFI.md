# 🔥 Solution : "URL ne peut être affichée"

## 🚨 Le problème

Votre partenaire est sur le même WiFi mais voit : **"URL ne peut être affichée"**

Cela signifie que votre Mac **bloque les connexions entrantes**.

---

## ✅ Solution 1 : Désactiver le pare-feu Mac (RECOMMANDÉ)

### Sur votre Mac :

1. Ouvrez **Préférences Système** (ou **Réglages Système** sur macOS récent)
2. Allez dans **Sécurité et confidentialité** → **Pare-feu**
3. Cliquez sur le cadenas 🔒 en bas à gauche (entrez votre mot de passe)
4. Cliquez sur **"Désactiver le pare-feu"**

**OU** si vous voulez garder le pare-feu actif :

1. Cliquez sur **"Options du pare-feu..."**
2. Cherchez **"Python"** dans la liste
3. Si présent, assurez-vous qu'il est sur **"Autoriser les connexions entrantes"**
4. Sinon, cliquez sur **"+"** et ajoutez Python :
   - Emplacement : `/usr/bin/python3` ou `/usr/local/bin/python3`
   - Réglez sur **"Autoriser les connexions entrantes"**

### Ensuite, testez à nouveau

Demandez à votre partenaire d'ouvrir à nouveau :
```
http://192.168.1.156:8000/join_house?code=XXXXX
```

---

## ✅ Solution 2 : Vérifier l'isolation WiFi

Certains routeurs ont une fonction **"Isolation AP"** qui empêche les appareils de communiquer.

### Vérifications :

1. **WiFi invité ?** → Votre partenaire ne doit PAS être sur le WiFi invité
2. **Réseaux séparés ?** → Vérifiez que vous êtes tous les deux sur le même SSID (nom WiFi)
3. **5GHz vs 2.4GHz ?** → Certains routeurs séparent les deux bandes

### Test rapide :

**Sur le téléphone de votre partenaire**, ouvrez le navigateur et tapez :
```
http://192.168.1.156:8000
```

- ✅ **Page d'accueil CleanBeat s'affiche** → Le problème vient du code ou du lien
- ❌ **"Impossible de se connecter"** → Problème réseau/pare-feu

---

## ✅ Solution 3 : Alternative QR Code

Au lieu d'envoyer un SMS, utilisez un **QR Code** :

### Sur votre ordinateur :

1. Ouvrez : `http://127.0.0.1:8000/qr_invitation`
2. Un QR Code s'affiche avec votre code d'invitation
3. Votre partenaire **scanne le QR Code** avec l'appareil photo de son téléphone
4. Ça devrait ouvrir directement la page !

---

## ✅ Solution 4 : Saisie manuelle (sans lien)

Si le lien ne fonctionne pas du tout :

### Votre partenaire doit :

1. Ouvrir un navigateur
2. Taper : `http://192.168.1.156:8000/join_house`
3. Entrer manuellement le code que vous lui donnez : **XXXXX**
4. Remplir le formulaire

---

## ✅ Solution 5 : Déploiement cloud (PERMANENT)

La meilleure solution pour éviter tous ces problèmes :

### Déployez sur PythonAnywhere

Une fois déployé, votre app aura une URL publique :
```
https://cleanbeat.pythonanywhere.com/join_house?code=XXXXX
```

**Avantages :**
- ✅ Fonctionne depuis n'importe où (4G, 5G, WiFi)
- ✅ Pas de problème de pare-feu
- ✅ Pas besoin d'être sur le même WiFi
- ✅ Gratuit avec PythonAnywhere

**Guide complet** : `SOLUTION_SMS_PARTENAIRE.md`

---

## 🧪 Tests de diagnostic

### Test 1 : Vérifier que le serveur est accessible

**Depuis votre ordinateur :**
```bash
curl http://127.0.0.1:8000/
```

✅ Si ça affiche du HTML → Serveur OK

---

### Test 2 : Vérifier depuis le téléphone de votre partenaire

**Ouvrir dans le navigateur du téléphone :**
```
http://192.168.1.156:8000/diagnostic
```

- ✅ **Page s'affiche** → Réseau OK, le problème vient du lien spécifique
- ❌ **Erreur** → Problème de pare-feu ou d'isolation réseau

---

### Test 3 : Ping depuis le téléphone

**Sur le téléphone de votre partenaire :**

1. Installez une app comme **"Network Analyzer"** ou **"Fing"**
2. Faites un **ping vers 192.168.1.156**
3. Si ça répond → Réseau OK
4. Si ça ne répond pas → Problème d'isolation réseau

---

## 📊 Résumé des solutions

| Solution | Rapidité | Efficacité | Permanent |
|----------|----------|-----------|-----------|
| Désactiver pare-feu Mac | ⚡ 1 min | ✅ 90% | ⏰ Temporaire |
| QR Code | ⚡ 2 min | ✅ 85% | ⏰ Tant que sur WiFi |
| Saisie manuelle | ⚡ 1 min | ✅ 85% | ⏰ Tant que sur WiFi |
| Déploiement PythonAnywhere | ⏱️ 15 min | ✅ 100% | ✅ Permanent |

---

## 🆘 Si rien ne fonctionne

1. **Redémarrez le routeur WiFi**
2. **Connectez les deux appareils en USB partage de connexion**
3. **Utilisez ngrok pour exposer temporairement** :
   ```bash
   brew install ngrok
   ngrok http 8000
   ```
   Puis utilisez l'URL ngrok fournie

4. **Déployez sur PythonAnywhere** (solution définitive)

---

## 💡 Recommandation finale

Pour éviter définitivement ces problèmes réseau :

**→ Déployez sur PythonAnywhere maintenant !**

Vous avez déjà tout configuré, il reste juste :
1. Configurer le fichier WSGI (5 min)
2. Mettre à jour les URLs dans le code (2 min)
3. Recharger l'app (1 clic)

**Total : 10 minutes pour une solution permanente !**
