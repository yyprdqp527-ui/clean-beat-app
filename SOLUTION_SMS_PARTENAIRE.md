# 🔧 Solution : Le partenaire ne peut pas ouvrir le lien SMS

## 🚨 Diagnostic

Le lien SMS contient : `http://192.168.1.156:8000/join_house?code=XXXXX`

**Problème** : Cette adresse IP locale (`192.168.1.156`) ne fonctionne QUE sur votre réseau WiFi domestique.

---

## ✅ Solutions possibles

### Option 1 : Test immédiat (Même WiFi)
Votre partenaire doit être **sur le MÊME WiFi** que vous :
1. Connectez votre partenaire au même WiFi
2. Cliquez sur le lien SMS
3. ✅ Ça devrait fonctionner !

**Limitations** : Ne fonctionne PAS en 4G/5G ou sur un autre WiFi.

---

### Option 2 : Déploiement PythonAnywhere (Recommandé) 🌍

Pour que le lien fonctionne **depuis n'importe où** (4G, 5G, n'importe quel WiFi) :

#### Étape 1 : Configurer PythonAnywhere
Vous avez déjà :
- ✅ Compte PythonAnywhere (username: `cleanbeat`)
- ✅ Code sur GitHub (`clean-beat-app`)
- ✅ Web app créée

Il reste à configurer le fichier WSGI :

1. Allez sur https://www.pythonanywhere.com/user/cleanbeat/
2. Cliquez sur **"Web"** dans le menu
3. Cliquez sur le nom de votre app
4. Trouvez la section **"Code"**
5. Cliquez sur le lien du fichier WSGI (ex: `/var/www/cleanbeat_pythonanywhere_com_wsgi.py`)

6. Remplacez TOUT le contenu par :
```python
import sys
import os

# Ajouter le chemin de votre projet
project_home = '/home/cleanbeat/clean-beat-app'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Importer l'application Flask
from app import app as application
```

7. Cliquez sur **"Save"**
8. Retournez à l'onglet **"Web"**
9. Dans la section **"Code"**, configurez :
   - **Source code** : `/home/cleanbeat/clean-beat-app`
   - **Working directory** : `/home/cleanbeat/clean-beat-app`

10. Cliquez sur le gros bouton vert **"Reload cleanbeat.pythonanywhere.com"**

#### Étape 2 : Mettre à jour les URLs dans le code

Dans `app.py`, trouvez les lignes **746 et 759** et remplacez :
```python
# AVANT
http://192.168.1.156:8000/join_house?code={house_code}

# APRÈS
https://cleanbeat.pythonanywhere.com/join_house?code={house_code}
```

#### Étape 3 : Pousser sur GitHub et tirer sur PythonAnywhere

**Sur votre ordinateur :**
```bash
git add app.py
git commit -m "Fix: URLs production pour SMS"
git push
```

**Sur PythonAnywhere (console Bash) :**
```bash
cd ~/clean-beat-app
git pull
```

Puis cliquez sur **"Reload"** dans l'onglet Web.

---

## 🧪 Test final

1. Envoyez un nouveau SMS d'invitation
2. Votre partenaire peut cliquer depuis **n'importe où** (4G, 5G, WiFi différent)
3. ✅ La page devrait s'ouvrir !

---

## 📊 Vérifications

### Tester la page manuellement
Ouvrez : https://cleanbeat.pythonanywhere.com/diagnostic

Cette page affiche :
- État du serveur
- URLs actuelles
- Guide de dépannage

### Vérifier les logs
Sur PythonAnywhere → **Web** → **Log files** :
- `error.log` : erreurs Python
- `server.log` : requêtes HTTP

---

## 🆘 Si ça ne marche toujours pas

1. **Vérifiez que le serveur PythonAnywhere est actif** :
   - https://cleanbeat.pythonanywhere.com/ doit afficher la page d'accueil

2. **Vérifiez que la base de données est sur PythonAnywhere** :
   - Le fichier `users.db` doit être dans `/home/cleanbeat/clean-beat-app/`

3. **Vérifiez les logs d'erreur** sur PythonAnywhere

4. **Test local** : Ouvrez http://127.0.0.1:8000/diagnostic pour voir l'état actuel

---

## 📝 Résumé

| Méthode | Fonctionne en 4G ? | Fonctionne sur autre WiFi ? | Gratuit ? |
|---------|-------------------|----------------------------|-----------|
| URL locale (`192.168.1.156`) | ❌ Non | ❌ Non | ✅ Oui |
| PythonAnywhere (`cleanbeat.pythonanywhere.com`) | ✅ Oui | ✅ Oui | ✅ Oui |

**Conclusion** : Déployez sur PythonAnywhere pour que les SMS fonctionnent partout !
