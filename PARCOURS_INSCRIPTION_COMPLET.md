# 🎯 Nouveau Parcours d'Inscription TOG

## ✅ Implémentation Complète

### Flux d'inscription optimisé :

```
1. 🏠 Landing Page (/welcome)
   ↓ Présentation avec "TOG - Share. Compete. Live together."
   
2. 📝 Inscription Email (/signup_email)
   ↓ Nom, email, mot de passe
   
3. 🏡 Type de logement (/choose_house_type)
   ↓ Couple / Coloc / Famille
   
4. 🎮 Explication + Invitation (/onboarding_invite)
   ↓ Pourquoi inviter des partenaires
   → Inviter par SMS (/invite_partner)
   → Ajouter enfants (/add_children)
   → Ou skip "Je ferai ça plus tard"
   
5. 🏠 Nommer le foyer (/name_house)
   ↓ Personnalisation du nom de la maison
   
6. 👤 Création profil (/create_profile)
   ↓ Avatar + Pseudo
   
7. 🎉 Page d'accueil (/menu)
   → Prêt à jouer !
```

## 📁 Fichiers Créés/Modifiés

### Nouveaux templates :
- ✅ `templates/choose_house_type.html` - Choix couple/coloc/famille
- ✅ `templates/onboarding_invite.html` - Explication pourquoi inviter
- ✅ `templates/name_house.html` - Nommer le foyer

### Templates modifiés :
- ✅ `templates/welcome.html` - Ajout tagline "TOG - Share. Compete..."
- ✅ `templates/create_profile.html` - Ajout barre de progression (étape 5/5)

### Routes ajoutées dans app.py :
- ✅ `/` - Redirection intelligente (welcome ou menu)
- ✅ `/choose_house_type` (GET/POST) - Étape 2
- ✅ `/onboarding_invite` (GET) - Étape 3
- ✅ `/name_house` (GET/POST) - Étape 4

### Routes modifiées :
- ✅ `/signup_email` - Redirige vers `/choose_house_type`
- ✅ `/invite_partner` - Redirige vers `/name_house` (si onboarding)
- ✅ `/register` (create_profile) - Crée maison avec nom + type

## 🎨 Design

Tous les éléments respectent le style de l'appli :
- ✅ Glassmorphisme (`backdrop-filter: blur`)
- ✅ Couleurs : #A6D3DC, #597176, #FDAE54, #F4C68D
- ✅ Cartes arrondies avec ombres
- ✅ Barre de progression (5 étapes)
- ✅ Animations et transitions fluides
- ✅ Boutons avec flèches → 
- ✅ Messages flash stylisés
- ✅ Responsive mobile optimisé

## 🔄 Flux de Données

### Session variables :
- `user` - Email de l'utilisateur
- `user_name` - Nom de l'utilisateur
- `registration_step` - Étape actuelle
- `house_type` - Type choisi (temporaire)
- `house_name` - Nom choisi (temporaire)

### Base de données :
La maison est créée à la fin avec :
- `name` / `house_name` - Nom personnalisé
- `house_type` - couple/coloc/family
- `code` - Code unique pour invitations
- `level`, `health`, `mood`, `progress` - Gamification

## 🚀 Pour Tester

1. Arrêter le serveur actuel
2. Relancer : `python3 app.py`
3. Ouvrir : `http://192.168.1.149:8000/`
4. Suivre le parcours complet

## 📝 Notes

- Le parcours est fluide et guidé
- Possibilité de skip certaines étapes ("Je ferai ça plus tard")
- Messages encourageants à chaque étape
- Sauvegarde automatique de la progression
- Design cohérent avec le reste de l'app
