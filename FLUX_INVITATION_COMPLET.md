# 📱 Flux Complet d'Invitation CleanBeat

## 🎯 Vue d'ensemble

Ce document décrit le parcours complet depuis l'invitation d'un partenaire jusqu'à son arrivée dans le jeu avec un profil personnalisé.

---

## 🔄 Étapes du Flux

### 1️⃣ **L'utilisateur existant invite un partenaire**

**Page** : `/invite_partner`

L'utilisateur connecté :
- Accède à la page d'invitation
- Voit son **code de maison** (ex: `ABC123`)
- Ajoute un ou plusieurs partenaires :
  - Nom du partenaire
  - Numéro de téléphone
- Clique sur **"Envoyer les invitations"**

**Résultat** :
- Un SMS est envoyé à chaque partenaire (simulé en développement)
- Le SMS contient : `🏠 [Nom] vous invite à jouer à CleanBeat ! Lien: http://127.0.0.1:8000/join_house?code=ABC123`

---

### 2️⃣ **Le partenaire reçoit le SMS**

**SMS reçu** :
```
🏠 Marie vous invite à jouer à CleanBeat !
Rejoignez la maison avec ce lien:
➡️ http://127.0.0.1:8000/join_house?code=ABC123
```

Le partenaire :
- Clique sur le lien dans le SMS
- Arrive directement sur `/join_house?code=ABC123`
- **Le code est automatiquement pré-rempli** dans le formulaire

---

### 3️⃣ **Inscription du partenaire (4 étapes)**

**Page** : `/join_house`

#### Étape 1 : Code de la maison ✅
- Le code `ABC123` est **déjà rempli** (depuis l'URL)
- Le partenaire vérifie et clique sur "Suivant"

#### Étape 2 : Nom de la maison 🏠
- Le partenaire donne un nom à la maison
- Ex: "Chez nous", "Villa du bonheur"
- Clique sur "Suivant"

#### Étape 3 : Création du compte 👤
- Nom d'utilisateur
- Email
- Mot de passe (min 6 caractères)
- Clique sur "Suivant"

#### Étape 4 : Confirmation ✨
- Récapitulatif des informations
- Clique sur "Rejoindre la maison !"

**Actions backend** :
```python
# Dans /join_house POST :
1. Vérifie le code de maison
2. Crée le compte utilisateur
3. Assigne l'utilisateur à la maison
4. Met à jour le nom de la maison
5. Connecte automatiquement l'utilisateur (session)
6. ➡️ Redirige vers /create_profile
```

---

### 4️⃣ **Création du profil personnalisé**

**Page** : `/create_profile`

Le nouveau partenaire :
- Modifie son nom si besoin
- Ajoute une bio (optionnel)
- **Choisit son avatar emoji** 🎭
  - 60+ avatars disponibles
  - Catégories : Personnes, Animaux, Fantastique, Robots...
- Peut prendre/uploader une photo (optionnel)

**Actions backend** :
```python
# Dans /create_profile POST :
1. Enregistre le nom, bio, avatar, photo
2. Définit registration_step = 'profile_created'
3. ➡️ Redirige vers /menu
```

---

### 5️⃣ **Arrivée au menu de jeu**

**Page** : `/menu`

Le partenaire arrive au menu principal :
- Son **avatar personnalisé** est affiché dans l'en-tête
- Il voit les informations de la maison
- Il peut commencer à jouer immédiatement

**Si la maison n'a pas encore de nom** :
- Une **modal** s'affiche automatiquement
- Demande de nommer la maison
- Non-fermable tant que la maison n'est pas nommée
- *(Normalement déjà fait à l'étape 3)*

---

## 📊 Schéma du Flux

```
┌─────────────────────────────────────┐
│  Utilisateur existant               │
│  Page: /invite_partner              │
│  • Entre nom et téléphone           │
│  • Clique "Envoyer invitations"     │
└──────────────┬──────────────────────┘
               │
               │ SMS avec lien + code
               ▼
┌─────────────────────────────────────┐
│  Partenaire reçoit SMS              │
│  Contenu:                           │
│  🏠 [Nom] vous invite...            │
│  Lien: /join_house?code=ABC123      │
└──────────────┬──────────────────────┘
               │
               │ Clique sur le lien
               ▼
┌─────────────────────────────────────┐
│  Page: /join_house                  │
│  Étape 1: Code (pré-rempli) ✅      │
│  Étape 2: Nom de maison 🏠          │
│  Étape 3: Compte (email/mdp) 👤     │
│  Étape 4: Confirmation ✨            │
└──────────────┬──────────────────────┘
               │
               │ Compte créé, auto-login
               ▼
┌─────────────────────────────────────┐
│  Page: /create_profile              │
│  • Choisit avatar emoji 🎭          │
│  • Ajoute bio (optionnel)           │
│  • Upload photo (optionnel)         │
└──────────────┬──────────────────────┘
               │
               │ Profil sauvegardé
               ▼
┌─────────────────────────────────────┐
│  Page: /menu                        │
│  ✅ Avatar personnalisé affiché     │
│  ✅ Peut jouer immédiatement        │
│  ✅ Fait partie de la maison        │
└─────────────────────────────────────┘
```

---

## 🔑 Points Clés

### Avantages du flux

✅ **Code pré-rempli** : Le partenaire n'a pas à retaper le code  
✅ **Auto-login** : Pas besoin de se connecter après inscription  
✅ **Avatar personnalisé** : Chaque joueur a son identité visuelle  
✅ **Expérience guidée** : 4 étapes claires avec indicateurs de progression  
✅ **Validation** : Vérifications à chaque étape  

### Données créées

Dans la base de données `users.db` :

**Table `users`** :
```sql
INSERT INTO users (
    email,           -- Email du nouveau partenaire
    password,        -- Hash du mot de passe
    name,            -- Nom d'utilisateur
    house_id,        -- ID de la maison (lien avec houses)
    avatar,          -- Emoji choisi (ex: '🧑')
    photo,           -- Photo en base64 (optionnel)
    bio,             -- Biographie (optionnel)
    registration_step -- 'profile_created'
)
```

**Table `houses`** :
```sql
UPDATE houses SET 
    name = 'Nom choisi',
    house_name = 'Nom choisi'
WHERE code = 'ABC123'
```

---

## 🧪 Test du Flux

### En développement (SMS simulé)

1. Connectez-vous avec un utilisateur existant
2. Allez sur `http://127.0.0.1:8000/invite_partner`
3. Invitez un partenaire (ex: 0612345678)
4. **Regardez la console Python** :
   ```
   SMS simulé vers 0612345678: Marie vous invite à jouer à CleanBeat ! 
   Lien: http://127.0.0.1:8000/join_house?code=ABC123
   ```
5. Copiez le lien et ouvrez-le dans un **autre navigateur/incognito**
6. Suivez les 4 étapes d'inscription
7. Choisissez votre avatar
8. Arrivez au menu avec votre avatar affiché !

### En production (SMS réel via Twilio)

Configurez les variables dans `app.py` :
```python
TWILIO_ACCOUNT_SID = "votre_sid"
TWILIO_AUTH_TOKEN = "votre_token"
TWILIO_PHONE_NUMBER = "+33612345678"
```

Le SMS sera automatiquement envoyé via Twilio.

---

## 🐛 Problèmes Potentiels

### Le code n'est pas pré-rempli
- Vérifiez que l'URL contient `?code=ABC123`
- Vérifiez le JavaScript dans `join_house.html` (ligne 433+)

### Redirection vers /menu au lieu de /create_profile
- Vérifiez la route `/join_house` ligne 1628 de `app.py`
- Doit rediriger vers `redirect(url_for('create_profile'))`

### L'avatar ne s'affiche pas dans le menu
- Vérifiez que `avatar` est bien sauvegardé dans la base de données
- Vérifiez le template `menu.html` ligne 237+ pour l'affichage de l'avatar

### Le SMS n'est pas envoyé
- En dev : normal, SMS simulé (voir console Python)
- En prod : vérifiez les credentials Twilio

---

## 📝 Fichiers Impliqués

| Fichier | Rôle |
|---------|------|
| `app.py` | Routes `/invite_partner`, `/join_house`, `/create_profile`, `/menu` |
| `templates/invite_partner_clean.html` | Interface d'invitation multi-partenaires |
| `templates/join_house.html` | Inscription guidée en 4 étapes |
| `templates/create_profile.html` | Sélection d'avatar et personnalisation |
| `templates/menu.html` | Menu principal avec affichage avatar |
| `users.db` | Base de données SQLite (tables users, houses) |

---

## 🚀 Améliorations Futures

- [ ] Notifications push en plus du SMS
- [ ] QR Code pour invitation encore plus rapide
- [ ] Limite du nombre de partenaires par maison
- [ ] Historique des invitations envoyées
- [ ] Rappel automatique si le partenaire ne s'inscrit pas sous 24h

---

**Date de création** : 9 décembre 2025  
**Version** : 1.0  
**Auteur** : CleanBeat Team
