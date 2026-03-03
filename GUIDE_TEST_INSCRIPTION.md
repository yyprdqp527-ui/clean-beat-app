# 🧪 Guide de Test - Nouveau Parcours d'Inscription

## ✅ Parcours Complet à Tester

### 📱 URL de départ
```
http://192.168.1.149:8000/
```

### 🔄 Étapes du Parcours

#### 1️⃣ Page d'Accueil (Landing)
**URL:** `/` ou `/welcome`

**À vérifier :**
- ✅ Logo "TOG" visible en grand
- ✅ Tagline "Share. Compete. Live together."
- ✅ Description du concept
- ✅ Bouton "Que le meilleur gagne !"
- ✅ Design glassmorphisme cohérent
- ✅ Responsive mobile

**Action :** Cliquer sur "Que le meilleur gagne !"

---

#### 2️⃣ Inscription Email
**URL:** `/signup_email`

**À vérifier :**
- ✅ Carte glassmorphisme avec icône 📝
- ✅ Titre "Créer votre compte"
- ✅ Champs : Prénom, Email, Mot de passe, Confirmation
- ✅ Validation : minimum 6 caractères
- ✅ Messages d'erreur si champs vides
- ✅ Pas de barre de progression (étape 1)

**Action :** Remplir et soumettre le formulaire

**Résultat attendu :** Message "Bienvenue [Nom] ! 🎉" et redirection vers `/choose_house_type`

---

#### 3️⃣ Type de Logement
**URL:** `/choose_house_type`

**À vérifier :**
- ✅ Icône 🏠 et titre "Votre type de logement"
- ✅ Barre de progression : étape 2/5 active
- ✅ 3 cartes cliquables :
  - 💑 En couple
  - 👥 En colocation  
  - 👨‍👩‍👧‍👦 En famille
- ✅ Carte sélectionnée s'illumine
- ✅ Bouton "Suivant →" activé après sélection
- ✅ Design glassmorphisme

**Action :** Sélectionner un type et cliquer "Suivant"

**Résultat attendu :** Redirection vers `/onboarding_invite`

---

#### 4️⃣ Invitation Partenaires
**URL:** `/onboarding_invite`

**À vérifier :**
- ✅ Icône 🎮 et titre "On ne joue pas seul !"
- ✅ Barre de progression : étape 3/5 active
- ✅ Explication pédagogique :
  - Pourquoi inviter ?
  - Liste des avantages (✓)
- ✅ 2 boutons d'action :
  - 📱 Inviter par SMS
  - 👶 Ajouter des enfants
- ✅ Lien "Je ferai ça plus tard →"

**Options :**
- **Option A :** Cliquer "Inviter par SMS" → `/invite_partner`
- **Option B :** Cliquer "Ajouter des enfants" → `/add_children`
- **Option C :** Cliquer "Je ferai ça plus tard" → `/name_house`

---

#### 5️⃣ Nommer le Foyer
**URL:** `/name_house`

**À vérifier :**
- ✅ Icône 🏡 et titre "Nommer votre foyer"
- ✅ Barre de progression : étape 4/5 active
- ✅ Champ de texte avec placeholder
- ✅ Suggestions cliquables :
  - La Villa des Champions
  - Chez Nous
  - Le Nid Douillet
  - La Casa
  - Sweet Home
  - Le QG
- ✅ Cliquer sur une suggestion remplit le champ
- ✅ Bouton "Suivant →"
- ✅ Message helper en bas

**Action :** Entrer un nom (ou cliquer suggestion) et soumettre

**Résultat attendu :** Redirection vers `/create_profile`

---

#### 6️⃣ Création du Profil
**URL:** `/create_profile`

**À vérifier :**
- ✅ Titre "Créer votre profil de joueur"
- ✅ Barre de progression : étape 5/5 active
- ✅ Section photo/avatar :
  - Bouton "📷 Photo"
  - Bouton "🎨 Avatar"
- ✅ Grille d'avatars DiceBear
- ✅ Champ "Prénom/Pseudo"
- ✅ Bouton "Créer mon profil"
- ✅ Design harmonisé glassmorphisme

**Action :** Choisir un avatar et entrer un pseudo

**Résultat attendu :** 
- Message "🎉 Profil créé ! Bienvenue dans l'aventure, [Nom] !"
- Redirection vers `/menu`
- Maison créée avec le nom et le type choisis

---

#### 7️⃣ Page d'Accueil (Menu)
**URL:** `/menu`

**À vérifier :**
- ✅ Affichage normal de l'application
- ✅ Nom du foyer visible
- ✅ Avatar du joueur affiché
- ✅ Points à 0
- ✅ Possibilité de naviguer dans l'app

---

## 🔍 Points de Contrôle Techniques

### Base de données
Après inscription complète, vérifier :
```sql
-- L'utilisateur existe
SELECT * FROM users WHERE email = '[email_test]';

-- La maison existe avec nom et type
SELECT * FROM houses WHERE code = '[code_maison]';

-- L'utilisateur est bien lié à la maison
SELECT u.name, h.house_name, h.house_type 
FROM users u 
JOIN houses h ON u.house_id = h.id 
WHERE u.email = '[email_test]';
```

### Session
Variables sauvegardées :
- `user` : email de l'utilisateur
- `user_name` : nom/pseudo
- `registration_step` : 'complete'

Variables temporaires (nettoyées après) :
- `house_type`
- `house_name`

---

## 🐛 Tests d'Erreurs

### Tester les validations :
1. **Email vide** → Message d'erreur
2. **Mot de passe < 6 caractères** → Message d'erreur
3. **Mots de passe différents** → Message d'erreur
4. **Email déjà utilisé** → Message d'erreur
5. **Aucun type de logement sélectionné** → Bouton désactivé
6. **Nom de foyer vide** → Message d'erreur
7. **Pas d'avatar sélectionné** → Message d'erreur

### Tester la persistance :
1. Rafraîchir la page pendant l'inscription
2. Utiliser le bouton retour du navigateur
3. Vérifier que la session persiste

---

## 📊 Résultat Attendu Final

Après le parcours complet :
- ✅ Utilisateur créé et connecté
- ✅ Maison créée avec nom personnalisé
- ✅ Type de foyer enregistré (couple/coloc/famille)
- ✅ Avatar et pseudo configurés
- ✅ Prêt à utiliser l'application
- ✅ Peut inviter d'autres joueurs

---

## 🎨 Design Cohérent

Sur toutes les pages :
- ✅ Glassmorphisme avec `backdrop-filter: blur()`
- ✅ Couleurs harmonieuses (#A6D3DC, #597176, #FDAE54)
- ✅ Cartes arrondies avec ombres
- ✅ Boutons avec effet hover
- ✅ Messages flash stylisés
- ✅ Barre de progression visible (étapes 2-5)
- ✅ Responsive mobile optimal
