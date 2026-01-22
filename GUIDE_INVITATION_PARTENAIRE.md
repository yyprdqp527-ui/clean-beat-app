# 📱 Guide d'Invitation des Partenaires

## ✅ Pages d'Invitation Professionnelles

Toutes les pages de test ont été supprimées et remplacées par des pages professionnelles prêtes pour la production.

### 🔗 Routes Disponibles

#### 1. **`/partager_invitation`** - Page de Partage Simple
- **Accès** : Depuis le menu principal
- **Fonctionnalités** :
  - Affichage du code d'invitation
  - QR Code scannable
  - Bouton "Copier le code"
  - Bouton "Copier le lien"
  - Bouton "Partager" (utilise l'API native de partage)
  - Instructions d'utilisation
  
#### 2. **`/invite_partner`** - Page d'Invitation Complète
- **Accès** : Depuis le processus d'inscription
- **Fonctionnalités** :
  - Formulaire complet d'invitation
  - Envoi de SMS aux partenaires
  - Création de profils enfants
  - Affichage du code et QR Code

#### 3. **`/join_house?code=XXXXX`** - Page d'Inscription Partenaire
- **Accès** : Via lien SMS ou QR Code
- **Fonctionnalités** :
  - Inscription avec le code de maison
  - Bouton "Se connecter" pour les utilisateurs existants
  - Création automatique du compte
  - Redirection vers création de profil

---

## 🎨 Caractéristiques des Nouvelles Pages

### Design Professionnel
- ✨ Interface moderne et épurée
- 📱 100% responsive (mobile et desktop)
- 🎨 Cohérence visuelle avec le reste de l'application
- 🌈 Dégradés de couleurs élégants
- 💫 Animations fluides

### Expérience Utilisateur
- 🎯 Navigation intuitive
- 📋 Copie en un clic
- 📤 Partage natif (iOS/Android)
- ✅ Messages de confirmation
- 🔙 Retour facile au menu

### Sécurité & Performance
- 🔒 Vérification de connexion
- ⚡ Chargement rapide
- 📊 Code QR haute qualité
- 🔄 Gestion d'erreurs robuste

---

## 📋 Comment Inviter un Partenaire

### Méthode 1 : Code Simple
1. Connectez-vous à CleanBeat
2. Accédez au menu
3. Cliquez sur "Inviter un partenaire"
4. Partagez le **code à 6 caractères** affiché
5. Votre partenaire entre ce code lors de son inscription

### Méthode 2 : QR Code
1. Accédez à la page d'invitation
2. Faites scanner le **QR Code** par votre partenaire
3. Il est automatiquement redirigé vers la page d'inscription
4. Le code est pré-rempli !

### Méthode 3 : Lien Direct
1. Cliquez sur "Copier le lien"
2. Envoyez le lien par SMS, email, ou messagerie
3. Votre partenaire clique sur le lien
4. Il arrive directement sur la page d'inscription

### Méthode 4 : Partage Natif
1. Cliquez sur "Partager"
2. Choisissez l'application (WhatsApp, SMS, etc.)
3. Le code ET le lien sont envoyés automatiquement

---

## 🔧 Configuration Technique

### URL de Production
Actuellement configuré : `http://192.168.1.156:8000`

⚠️ **Important** : Avant le déploiement sur PythonAnywhere, modifier l'URL dans :
- `app.py` ligne ~6331 : `join_url = f"https://cleanbeat.pythonanywhere.com/join_house?code={house_code}"`
- `app.py` ligne ~4659 : `join_url = f"https://cleanbeat.pythonanywhere.com/join_house?code={house_code}"`

### Base de Données
- **Table** : `houses`
- **Champ code** : Code unique à 6 caractères (lettres majuscules + chiffres)
- **Format** : Exemple `VPRX9O`

---

## 🎯 Workflow Complet

### Pour l'Inviteur
1. Connexion à CleanBeat
2. Navigation vers `/partager_invitation`
3. Partage du code ou du QR Code
4. Attente de l'inscription du partenaire

### Pour l'Invité
1. Réception du code/lien/QR Code
2. Accès à `/join_house?code=XXXXX`
3. Inscription avec nom et email
4. Création du profil et choix d'avatar
5. Accès au menu principal
6. ✅ **Rejoint automatiquement la maison de l'inviteur !**

---

## 🗑️ Pages Supprimées

Les pages de test suivantes ont été **supprimées** :
- ❌ `/test_invitation_link`
- ❌ `/qr_invitation`
- ❌ `/diagnostic`
- ❌ `templates/test_invitation_link.html`
- ❌ `templates/qr_invitation.html`
- ❌ `templates/diagnostic_connexion.html`

---

## 📦 Fichiers Créés

### Nouveaux Templates
- ✅ `templates/invitation_partner.html` - Page d'invitation professionnelle

### Routes Actives
- ✅ `/partager_invitation` - Route de partage simple
- ✅ `/invitation_partner` - Route complète (renommée depuis `/qr_invitation`)
- ✅ `/invite_partner` - Route du formulaire d'inscription (existante, améliorée)
- ✅ `/join_house` - Route d'inscription partenaire (existante, améliorée)

---

## 🚀 Prochaines Étapes

1. **Déploiement PythonAnywhere**
   - Mettre à jour les URLs vers `https://cleanbeat.pythonanywhere.com`
   - Tester le QR Code en production
   - Vérifier l'envoi de SMS

2. **Améliorations Futures**
   - Statistiques d'invitation (combien de partenaires invités)
   - Historique des invitations
   - Notification quand un partenaire rejoint
   - Personnalisation du message d'invitation

3. **Tests**
   - ✅ Test de la page `/partager_invitation`
   - ✅ Test du QR Code
   - ✅ Test du partage natif
   - ✅ Test de l'inscription via code

---

## 📞 Support

En cas de problème d'invitation :
1. Vérifier que le serveur est démarré
2. Vérifier que le code de maison existe
3. Vérifier que l'URL est accessible
4. Consulter les logs Flask pour les erreurs

**Logs** : Visibles dans le terminal où `python3 app.py` est lancé

---

✨ **Les invitations sont maintenant professionnelles et prêtes pour la production !**
