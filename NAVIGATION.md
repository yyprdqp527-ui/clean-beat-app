# Plan de Navigation - Ménage à Deux (VERSION RESTAURÉE)

## Corrections Apportées

### ✅ 1. Page d'accueil supprimée
- Route `/` redirige directement vers `/register` (création de profil)
- Fichier `home.html` supprimé
- Navigation simplifiée : Inscription → Profil → Menu

### ✅ 2. Page d'inscription = Création de profil
- **Route unique** : `/register` 
- **Fichier** : `templates/create_profile.html`
- **Fonctionnalités restaurées** :
  - Photo avec caméra ou sélection avatar
  - Saisie du prénom obligatoire
  - Liste des contacts automatique
  - Invitation partenaire par SMS obligatoire
  - Palette de couleurs sans émojis appliquée

### ✅ 3. Zones cliquables repositionnées
- **Cuisine** : Zone élargie (110,100,140x120) avec label plus visible
- **Toilettes** : Zone mieux centrée (250,280,80x100) 
- **Buanderie** : Zone ajustée (10,200,90x110)
- **Chambre** : Zone repositionnée (100,340,130x120)
- **Style** : Couleur A6D3DC avec transparence améliorée

### ✅ 4. Login adapté
- Fond : Dégradé A6D3DC → 597176
- Boutons : Dégradé FDAE54 → F4C68D  
- Focus inputs : Couleur 597176

## Structure de Navigation ACTUELLE

1. **URL d'entrée** : `http://127.0.0.1:5000/`
   - Redirige automatiquement vers création de profil

2. **Création de Profil** : `/register`
   - Photo + prénom + contact + SMS → `/menu`

3. **Connexion** : `/login` 
   - Email + mot de passe → `/menu`

4. **Menu Principal** : `/menu`
   - Zones cliquables : Cuisine, Toilettes, Buanderie, Chambre

5. **Catégories** : `/categorie/<cat>`
   - Tâches enrichies disponibles

## ✅ Tâches Enrichies

- **Cuisine** : Café, **Vaisselle**, Courses, Nettoyer surfaces
- **Toilettes** : Nettoyer WC, Changer rouleau, **Nettoyer lavabo**
- **Buanderie** : Machine, Plier linge, **Repasser**
- **Chambre** : Faire lit, **Ranger vêtements**, **Aspirateur**

## Status : ✅ TOUTES CORRECTIONS RESTAURÉES

L'application fonctionne maintenant comme demandé :
- ❌ Page d'accueil supprimée
- ✅ Inscription = création profil complet avec SMS
- ✅ Zones de maison repositionnées et agrandies
- ✅ Palette de couleurs cohérente
- ✅ Navigation fluide inscription → menu