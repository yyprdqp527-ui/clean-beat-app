# 📱 Flux d'Invitation Simplifié - CleanBeat

## 🎯 Résumé

Le partenaire invité reçoit un **code par SMS** qu'il doit **entrer manuellement** pour rejoindre la maison. Le nom de la maison sera défini **plus tard** par les joueurs.

---

## 🔄 Nouveau Parcours (3 étapes seulement)

### 1️⃣ L'utilisateur invite un partenaire

**Page** : `/invite_partner`

Actions :
- Ajoute le nom et numéro du partenaire
- Clique sur "Envoyer les invitations"

**SMS reçu par le partenaire** :
```
🏠 Marie vous invite à jouer à CleanBeat !
Entrez ce code pour rejoindre: ABC123
➡️ http://127.0.0.1:8000/join_house?code=ABC123
```

---

### 2️⃣ Le partenaire rejoint la maison

**Page** : `/join_house` (3 étapes)

#### Étape 1 : Code de la maison ✅
- **Le code est pré-rempli** si le lien du SMS est utilisé
- OU le partenaire peut entrer le code manuellement : `ABC123`
- Validation et vérification du code

#### Étape 2 : Création du compte 👤
- Nom d'utilisateur
- Email
- Mot de passe (minimum 6 caractères)

#### Étape 3 : Confirmation ✨
- Récapitulatif :
  - Code de la maison
  - Nom d'utilisateur
  - Email
- Clic sur "Rejoindre et commencer à jouer !"

**Actions backend** :
```python
1. Vérifie que le code existe
2. Crée le compte utilisateur
3. Assigne à la maison (house_id)
4. Auto-login (session)
5. ➡️ Redirige vers /create_profile
```

---

### 3️⃣ Création du profil

**Page** : `/create_profile`

Le nouveau joueur :
- **Choisit son avatar** 🎭 (60+ options)
- Ajoute une bio (optionnel)
- Upload une photo (optionnel)

Puis :
```python
➡️ Redirige vers /menu
```

---

### 4️⃣ Menu principal

**Page** : `/menu`

- Le joueur arrive avec **son avatar personnalisé**
- Peut commencer à jouer immédiatement
- **Si la maison n'a pas de nom** :
  - Une modal s'affiche automatiquement
  - Demande de nommer la maison
  - Les joueurs choisissent ensemble le nom

---

## 📊 Schéma Visuel

```
┌─────────────────────────────────┐
│  Utilisateur existant           │
│  /invite_partner                │
│  • Entre nom + téléphone        │
│  • Envoie invitation            │
└────────────┬────────────────────┘
             │
             │ SMS avec code
             ▼
┌─────────────────────────────────┐
│  📱 SMS reçu                    │
│  🏠 Marie vous invite...        │
│  Code: ABC123                   │
│  Lien: /join_house?code=ABC123  │
└────────────┬────────────────────┘
             │
             │ Clique sur le lien
             ▼
┌─────────────────────────────────┐
│  /join_house (3 étapes)         │
│  1. Code (pré-rempli) ✅        │
│  2. Compte (nom/email/mdp) 👤   │
│  3. Confirmation ✨              │
└────────────┬────────────────────┘
             │
             │ Compte créé
             ▼
┌─────────────────────────────────┐
│  /create_profile                │
│  • Choisit avatar 🎭            │
│  • Bio + Photo (opt.)           │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│  /menu                          │
│  ✅ Prêt à jouer !              │
│  ⚠️ Modal si maison sans nom    │
└─────────────────────────────────┘
```

---

## 🔑 Points Clés

### Ce qui a changé

❌ **RETIRÉ** : Étape "Donner un nom à la maison" pendant l'inscription  
✅ **AJOUTÉ** : Le nom sera défini plus tard (modal dans le menu)  
✅ **SIMPLIFIÉ** : 3 étapes au lieu de 4  
✅ **FOCUS** : Code + Compte + Avatar  

### Pourquoi ce changement ?

1. **Moins intimidant** : L'inscription est plus rapide
2. **Décision collective** : Les joueurs nomment la maison ensemble (pas juste le nouveau)
3. **Flexibilité** : Pas besoin de se presser pour trouver un nom
4. **Meilleure UX** : Le partenaire peut rejoindre en 2 minutes

### Format du SMS

**En développement (console)** :
```
📱 SMS simulé envoyé vers 0612345678:
   🏠 Marie vous invite à jouer à CleanBeat !
   Entrez ce code pour rejoindre la maison: ABC123
   Lien: http://127.0.0.1:8000/join_house?code=ABC123
```

**En production (Twilio)** :
```
🏠 Marie vous invite à jouer à 'CleanBeat' !
Entrez ce code pour rejoindre: ABC123
➡️ http://127.0.0.1:8000/join_house?code=ABC123
```

---

## 🧪 Test du Flux

### Scénario complet

1. **Connectez-vous** avec un compte existant
2. Allez sur `/invite_partner`
3. Invitez un partenaire (ex: `0612345678`)
4. **Console Python** affiche :
   ```
   📱 SMS simulé envoyé vers 0612345678:
      🏠 [Votre nom] vous invite à jouer à CleanBeat !
      Entrez ce code pour rejoindre la maison: ABC123
      Lien: http://127.0.0.1:8000/join_house?code=ABC123
   ```
5. **Copiez le lien** et ouvrez en **incognito**
6. Le code `ABC123` est **déjà rempli** ✅
7. Passez les 3 étapes (code déjà OK → compte → confirmation)
8. Choisissez votre avatar 🎭
9. Arrivez au menu et **jouez** ! 🎉
10. Modal de nom de maison apparaît si pas encore nommée

### Test manuel du code

Si le partenaire n'utilise pas le lien :
1. Allez sur `http://127.0.0.1:8000/join_house`
2. Entrez manuellement le code : `ABC123`
3. Le formulaire accepte le code et continue

---

## 💾 Base de Données

### Création d'utilisateur

```sql
INSERT INTO users (
    email,           -- Email du partenaire
    password,        -- Hash du mot de passe
    name,            -- Nom d'utilisateur
    house_id,        -- ID de la maison (lien)
    avatar,          -- '🧑' par défaut, puis choisi dans create_profile
    points,          -- 0 au départ
    created_at       -- Timestamp
)
```

### Maison

```sql
-- La maison EXISTE déjà (créée par l'utilisateur principal)
-- Le nouveau membre rejoint juste via house_id
-- Le nom de la maison reste vide jusqu'à ce que quelqu'un le définisse
```

---

## 📝 Fichiers Modifiés

| Fichier | Changements |
|---------|-------------|
| `templates/join_house.html` | **Réduit de 4 à 3 étapes**, retiré champ `house_name` |
| `app.py` (route `/join_house`) | **Retiré validation `house_name`**, ne met plus à jour le nom de maison |
| `app.py` (fonction `send_sms_invitation`) | **Message SMS mis à jour** : "Entrez ce code pour rejoindre: ABC123" |

---

## ✅ Avantages du Nouveau Flux

1. **Plus rapide** : 3 étapes au lieu de 4
2. **Plus simple** : Juste le code + compte + avatar
3. **Moins de pression** : Pas besoin de nommer la maison tout de suite
4. **Meilleure logique** : Le nom de la maison est défini collectivement plus tard
5. **Code pré-rempli** : Un clic sur le SMS et c'est bon !

---

## 🐛 Dépannage

### Le code n'est pas pré-rempli
- Vérifiez l'URL : doit contenir `?code=ABC123`
- JavaScript dans `join_house.html` ligne 421+ gère le pré-remplissage

### Erreur "Code invalide"
- Le code doit exister dans la table `houses`
- Format : 6 caractères alphanumériques (ex: `ABC123`)

### La maison n'a pas de nom dans le menu
- C'est normal ! La modal apparaîtra pour le demander
- Route `/name_house` gère le nommage

---

**Version** : 2.0 (Simplifié)  
**Date** : 9 décembre 2025  
**Auteur** : CleanBeat Team
