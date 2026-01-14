# 📱 Flux d'Invitation des Partenaires - CleanBeat

## 🎯 Vue d'ensemble

Le système d'invitation permet à un utilisateur d'inviter un ou plusieurs partenaires via SMS pour rejoindre sa maison CleanBeat.

## 📋 Processus en 2 parties

### 👤 Partie 1 : L'Hôte (celui qui invite)

**Page : `/invite_partner` (invite_partner_clean.html)**

1. **Affichage du code de maison**
   - Le code unique de la maison est affiché en haut de la page
   - Ce code permet aux partenaires de rejoindre la maison

2. **Ajout de partenaires**
   - L'utilisateur peut ajouter plusieurs partenaires
   - Pour chaque partenaire :
     - Nom
     - Numéro de téléphone
   - Les partenaires sont ajoutés à une liste

3. **Envoi des invitations**
   - Bouton "Envoyer les invitations SMS"
   - Envoie un SMS à chaque partenaire avec :
     - Le nom de l'hôte
     - Le code de la maison
     - Le lien pour rejoindre

### 🎉 Partie 2 : Le Partenaire (celui qui rejoint)

**Page : `/join_house` (join_house.html)**

Le partenaire suit 4 étapes guidées :

#### Étape 1 : Code de la maison
- Entre le code reçu par SMS (6 caractères)
- Validation du format

#### Étape 2 : Nom de la maison
- Donne un nom personnalisé à la maison
- Exemple : "Chez nous", "La villa du bonheur"

#### Étape 3 : Création du compte
- Nom d'utilisateur
- Email
- Mot de passe (minimum 6 caractères)

#### Étape 4 : Confirmation
- Récapitulatif de toutes les informations
- Validation finale

#### ✅ Après validation
- Le partenaire est automatiquement connecté
- Il rejoint la maison existante
- Le nom de la maison est mis à jour
- Redirection vers le menu avec message de bienvenue

## 🔧 Fonctionnalités techniques

### Route `/invite_partner`

**GET** : Affiche la page d'invitation avec le code de la maison

**POST** : Traite l'envoi des invitations
- Paramètre : `partners` (JSON array)
- Chaque partenaire : `{ name, phone, status }`
- Envoie un SMS à chaque partenaire via `send_sms_invitation()`
- Affiche un message de succès avec le nombre d'invitations envoyées

### Route `/join_house`

**GET** : Affiche le formulaire multi-étapes

**POST** : Traite l'inscription du partenaire
- Paramètres :
  - `house_code` : Code de la maison à rejoindre
  - `house_name` : Nom personnalisé de la maison
  - `user_name` : Nom du nouvel utilisateur
  - `email` : Email du nouvel utilisateur
  - `password` : Mot de passe (hashé)

- Validations :
  - Vérification que le code existe
  - Email unique
  - Mot de passe minimum 6 caractères
  
- Actions :
  - Création du compte utilisateur
  - Association à la maison existante
  - Mise à jour du nom de la maison
  - Connexion automatique
  - Redirection vers le menu

## 📱 Messages SMS

Format du SMS d'invitation :
```
[Nom de l'hôte] vous invite à jouer à CleanBeat !
Code maison: [CODE]
Rendez-vous sur http://127.0.0.1:5000/join_house
```

## 🎨 Interface utilisateur

### Page d'invitation
- Design moderne avec gradient violet
- Liste interactive des partenaires
- Ajout/suppression dynamique
- Code de maison mis en évidence
- Responsive mobile

### Page de rejointe
- Processus guidé en 4 étapes
- Indicateur de progression visuel
- Navigation avant/arrière
- Validation à chaque étape
- Récapitulatif avant soumission
- Auto-uppercase du code de maison

## 🔒 Sécurité

- Mots de passe hashés avec `werkzeug.security`
- Validation des emails uniques
- Vérification de l'existence du code de maison
- Protection des sessions

## ✨ Améliorations futures possibles

1. Envoi de vrais SMS via API (Twilio, etc.)
2. QR Code pour partager le code de maison
3. Invitation par email en plus du SMS
4. Historique des invitations envoyées
5. Gestion des partenaires en attente
6. Notification quand un partenaire rejoint
