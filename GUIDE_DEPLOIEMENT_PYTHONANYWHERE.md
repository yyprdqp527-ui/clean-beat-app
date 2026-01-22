# 🚀 Guide de Déploiement CleanBeat sur PythonAnywhere

## 📦 Étape 1 : Créer un compte PythonAnywhere

1. Allez sur **https://www.pythonanywhere.com**
2. Cliquez sur **"Start running Python online in less than a minute!"**
3. Créez un compte **gratuit** (Beginner)
4. Confirmez votre email

---

## 📤 Étape 2 : Upload vos fichiers

### Option A : Via Git (Recommandé)

Sur votre Mac :
```bash
cd "/Users/anne-gaelledaval/Downloads/Appli web-2"

# Initialiser Git si pas déjà fait
git init
git add .
git commit -m "CleanBeat initial commit"

# Pousser sur GitHub
# (Créez un repo sur github.com d'abord)
git remote add origin https://github.com/VOTRE_USERNAME/cleanbeat.git
git push -u origin main
```

Sur PythonAnywhere :
1. Cliquez sur **"Consoles"** → **"Bash"**
2. Tapez :
```bash
git clone https://github.com/VOTRE_USERNAME/cleanbeat.git
cd cleanbeat
```

### Option B : Upload direct (Plus simple)

1. Sur PythonAnywhere, allez dans **"Files"**
2. Créez un dossier `cleanbeat`
3. Uploadez tous vos fichiers un par un :
   - `app.py`
   - `users.db`
   - Dossier `templates/` (tous les .html)
   - Dossier `static/` (images, CSS, JS)

---

## ⚙️ Étape 3 : Configuration de l'application

### 3.1 Installer les dépendances

Dans la console Bash PythonAnywhere :
```bash
cd ~/cleanbeat
pip3.10 install --user -r requirements.txt
```

### 3.2 Créer une application web

1. Allez dans **"Web"**
2. Cliquez sur **"Add a new web app"**
3. Choisissez **"Manual configuration"**
4. Sélectionnez **Python 3.10**

### 3.3 Configurer le WSGI

1. Dans la page Web, trouvez **"Code"** → **"WSGI configuration file"**
2. Cliquez sur le lien (ex: `/var/www/votre_username_pythonanywhere_com_wsgi.py`)
3. **Supprimez tout** le contenu
4. Remplacez par :

```python
import sys
import os

# Ajouter le chemin de votre application
path = '/home/VOTRE_USERNAME/cleanbeat'
if path not in sys.path:
    sys.path.append(path)

# Importer l'application Flask
from app import app as application
```

**⚠️ Remplacez `VOTRE_USERNAME` par votre nom d'utilisateur PythonAnywhere**

5. Cliquez sur **"Save"**

### 3.4 Configurer les chemins

Retour sur la page **"Web"** :

1. **Source code** : `/home/VOTRE_USERNAME/cleanbeat`
2. **Working directory** : `/home/VOTRE_USERNAME/cleanbeat`
3. **Static files** :
   - URL : `/static/`
   - Directory : `/home/VOTRE_USERNAME/cleanbeat/static`

---

## 🔧 Étape 4 : Modifications du code pour production

### 4.1 Modifier app.py

Sur PythonAnywhere, ouvrez `app.py` et modifiez :

**Ligne avec `app.run()` (à la fin du fichier)** :
```python
# ANCIEN (développement local) :
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)

# NOUVEAU (production PythonAnywhere) :
if __name__ == '__main__':
    app.run()
```

### 4.2 Chemin de la base de données

Dans `app.py`, trouvez :
```python
DB = "users.db"
```

Remplacez par :
```python
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "users.db")
```

---

## 🌐 Étape 5 : Lancer l'application

1. Retournez dans **"Web"**
2. Cliquez sur le gros bouton vert **"Reload votre_username.pythonanywhere.com"**
3. Attendez quelques secondes
4. Cliquez sur le lien en haut : **`https://votre_username.pythonanywhere.com`**

**🎉 Votre app est en ligne !**

---

## 📱 Étape 6 : Mettre à jour les liens d'invitation

### Sur PythonAnywhere, modifiez les fichiers :

**1. Dans `app.py` (fonction send_sms_invitation)** :
```python
# Remplacer :
http://192.168.1.156:8000

# Par :
https://votre_username.pythonanywhere.com
```

**2. Dans `templates/invite_partner_new.html`** :
```javascript
// Remplacer toutes les occurrences de :
http://192.168.1.156:8000

// Par :
https://votre_username.pythonanywhere.com
```

Après chaque modification, cliquez sur **"Reload"** dans l'onglet Web.

---

## ✅ Avantages de PythonAnywhere

- ✅ **Gratuit** (jusqu'à 512 MB de stockage)
- ✅ **Accessible 24h/24** depuis n'importe où
- ✅ **HTTPS automatique** (sécurisé)
- ✅ **Pas besoin de laisser votre Mac allumé**
- ✅ **Facile à mettre à jour**

---

## 🔄 Pour mettre à jour l'app après des modifications

### Si vous utilisez Git :
```bash
cd ~/cleanbeat
git pull
```

### Si vous uploadez manuellement :
1. Allez dans "Files"
2. Uploadez les fichiers modifiés
3. Remplacez les anciens

**N'oubliez pas de cliquer sur "Reload" après chaque mise à jour !**

---

## 📊 Vérifier que tout fonctionne

1. Ouvrez `https://votre_username.pythonanywhere.com`
2. Créez un compte de test
3. Testez les tâches
4. Testez l'invitation

---

## 🆘 En cas de problème

### Voir les logs d'erreur
1. Web → **"Log files"**
2. Ouvrez **"Error log"**
3. Les erreurs Python s'affichent ici

### Problème courant : "Application not found"
- Vérifiez le fichier WSGI
- Vérifiez que `app = Flask(__name__)` est bien dans app.py

### Base de données verrouillée
- Assurez-vous que `users.db` est uploadé
- Les permissions doivent être correctes

---

## 💰 Plan gratuit - Limitations

- **512 MB** de stockage (largement suffisant)
- **100 secondes** de CPU par jour (OK pour usage familial)
- **1 application web** seulement
- Domaine : `votre_username.pythonanywhere.com`

Pour un domaine personnalisé (ex: cleanbeat.com), il faut passer au plan payant (5$/mois).

---

## 🎯 Prochaines étapes après déploiement

1. Testez l'app en ligne
2. Invitez votre famille via le nouveau lien
3. Ajoutez l'app à l'écran d'accueil des téléphones
4. Profitez de CleanBeat partout ! 🎉

**Besoin d'aide ? Les étapes détaillées sont dans ce guide !**
