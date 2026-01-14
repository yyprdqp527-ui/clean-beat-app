# Flux d'Inscription Complet - Ménage à Deux

## 🎯 Parcours Utilisateur Final

### **1. Page d'Accueil** (`/`)
- ✅ **Image** : "Ménage à Deux.png" affichée
- ✅ **Boutons** : "S'inscrire" | "Se connecter"
- ✅ **Design** : Palette harmonieuse (A6D3DC → 597176)

### **2. Options d'Inscription** (`/signup`)
- ✅ **Facebook** : Bouton avec logo (simulation)
- ✅ **Google** : Bouton avec logo (simulation)  
- ✅ **Email** : Inscription fonctionnelle complète

### **3. Inscription Email** (`/signup/email`)
- ✅ **Formulaire** :
  - Prénom (obligatoire)
  - Email (unique, validation)
  - Mot de passe (min 6 caractères)
  - Confirmation mot de passe
- ✅ **Sécurité** : Hashage password, validation complète
- ✅ **Stockage** : Session temporaire pour étapes suivantes

### **4. Invitation Partenaire** (`/invite-partner`)
- ✅ **Liste contacts** : Simulation réaliste (10 contacts)
- ✅ **Recherche** : Par nom ou téléphone
- ✅ **Interface** : Sélection interactive avec avatars
- ✅ **SMS** : Intégration Twilio (simulation fonctionnelle)
- ✅ **Validation** : Contact obligatoire

### **5. Création Profil** (`/register`)
- ✅ **Photo** : Capture caméra HTML5 + base64
- ✅ **Avatars** : Grille de 12 avatars en ligne
- ✅ **Upload** : Sauvegarde fichiers dans `/static/avatars/`
- ✅ **Validation** : Photo OU avatar obligatoire

### **6. Finalisation** (Automatique)
- ✅ **Base de données** :
  - Création utilisateur complet
  - Génération maison automatique
  - Code maison unique (6 caractères)
  - Points initiaux à 0
- ✅ **Session** : Connexion automatique
- ✅ **Nettoyage** : Suppression données temporaires

### **7. Page Maison/Menu** (`/menu`)
- ✅ **Bienvenue** : Message d'accueil avec instructions
- ✅ **Zones interactives** :
  - 🍳 **Cuisine** : Café, Vaisselle, Courses, Surfaces
  - 🚿 **Toilettes** : Nettoyer WC, Changer rouleau, Lavabo
  - 👕 **Buanderie** : Machine, Plier linge, Repasser
  - 🛏️ **Chambre** : Faire lit, Ranger vêtements, Aspirateur
- ✅ **Objectifs** : Explication système points + équipe

## 🔄 Flux de Connexion Alternative

### **Utilisateur Existant** (`/login`)
- ✅ **Formulaire** : Email + mot de passe
- ✅ **Validation** : Vérification hash
- ✅ **Redirection** : Menu directement
- ✅ **Design** : Cohérent avec palette

## 📱 Fonctionnalités Techniques

### **Gestion Session**
```python
session['user'] = email  # Connexion persistante
session['signup_data']   # Données temporaires inscription
session.pop('signup_data', None)  # Nettoyage après finalisation
```

### **Base de Données**
```sql
users: email, password, name, house_id, avatar, points, photo_filename, avatar_url
houses: id, name, code
completed_tasks: user_email, category, task_name, points
```

### **Sécurité**
- ✅ **Passwords** : Hash Werkzeug
- ✅ **Validation** : Formulaires complets
- ✅ **Sessions** : Gestion état utilisateur
- ✅ **Upload** : Fichiers sécurisés

## 🎮 Début du Jeu

### **Page Menu Améliorée**
- ✅ **Message d'accueil** pour nouveaux joueurs
- ✅ **Instructions claires** sur le gameplay
- ✅ **Zones cliquables** repositionnées et agrandies
- ✅ **Design cohérent** avec palette application

### **Actions Disponibles**
1. **Cliquer pièce** → Liste des tâches
2. **Sélectionner tâche** → Page détaille + validation
3. **Valider tâche** → +Points + retour menu
4. **Progression** → Système points partagé en équipe

## ✅ Status Final

**FLUX COMPLET FONCTIONNEL** : Accueil → Inscription → SMS → Profil → Menu → Jeu

**Navigation fluide** avec redirections automatiques et messages de feedback.

**Prêt à jouer** dès la fin de l'inscription !

## 🚀 Prochaines Étapes (Optionnel)

- 🔗 **API Contacts** : Remplacer simulation par vraie API device
- 📱 **Twilio** : Configuration compte réel pour SMS
- 👥 **Multi-joueurs** : Synchronisation temps réel maison
- 🏆 **Récompenses** : Système d'échange points
- 📊 **Stats** : Tableau de bord progression