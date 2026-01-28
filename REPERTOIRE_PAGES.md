# 📋 Répertoire des Pages de CleanBeat

## 🟡 Pages Valides - Actives dans l'Application (41 pages)

### Pages d'Authentification
- `welcome.html` - Page d'accueil/bienvenue
- `login.html` - Connexion
- `quick_login.html` - Connexion rapide
- `signup.html` - Inscription
- `signup_email.html` - Inscription par email
- `register.html` - Enregistrement

### Pages de Profil et Gestion
- `create_profile.html` - Création du profil utilisateur
- `profile.html` - Page profil
- `manage_players.html` - Gestion des joueurs
- `edit_player.html` - Édition d'un joueur
- `add_players.html` - Ajout de joueurs
- `add_children.html` - Ajout d'enfants

### Pages Principales de Jeu
- `home.html` - Page d'accueil principale
- `home_main.html` - Page d'accueil alternative
- `menu.html` - Menu principal de l'application
- `fullhouse.html` - Vue complète de la maison

### Pages de Tâches
- `tasks.html` - Liste des tâches par catégorie
- `task_page_enhanced.html` - Page détaillée d'une tâche
- `add_task.html` - Ajout de tâche
- `add_custom_task.html` - Ajout de tâche personnalisée
- `completed_tasks.html` - Tâches complétées

### Pages de Récompenses
- `rewards.html` - Système de récompenses
- `rewards_grid.html` - Grille des récompenses
- `gifts.html` - Page des cadeaux
- `daily_reward.html` - Récompense quotidienne
- `sats.html` - Système de points/satisfaction

### Pages Sociales
- `comments.html` - Commentaires/messages
- `invitation_partner.html` - Page d'invitation du partenaire
- `invite_partner_new.html` - Nouvelle interface d'invitation
- `join_house.html` - Rejoindre une maison

### Pages Spécifiques
- `baby_tracking.html` - Suivi du bébé
- `stats.html` - Statistiques

### Templates de Base
- `base.html` - Template de base général
- `game_base.html` - Template de base pour le jeu
- `_game_header.html` - En-tête du jeu (fragment)

### Pages de Test et Diagnostic
- `test_audio.html` - Test audio
- `test_audio_mobile.html` - Test audio mobile
- `test_images_mobile.html` - Test images mobile
- `test_menu_simple.html` - Test menu simplifié
- `test_player_selector.html` - Test sélecteur de joueurs
- `clear_cache.html` - Vidage du cache

---

## 🔵 Backups et Essais - Archives (12+ pages)

### Anciennes Versions
- `comments_old.html` - Ancienne version des commentaires
- `join_house_old.html` - Ancienne version de join_house
- `task_page_OLD_BACKUP.html` - Ancienne page de tâche
- `task_page.html` - Version intermédiaire de task_page

### Backups de Sécurité
- `create_profile_backup.html` - Backup de create_profile
- `edit_player_backup.html` - Backup de edit_player
- `menu.html.backup` - Backup du menu
- `menu.html.bak` - Sauvegarde du menu
- `menu.html.current` - Version courante archivée
- `menu_with_bottom_nav.html.backup` - Menu avec navigation bas

### Versions de Test
- `invite_partner.html` - Ancien système d'invitation
- `invite_partner_clean.html` - Version clean de l'invitation
- `menu_clean.html` - Version clean du menu
- `menu_cleanbeat.html` - Version cleanbeat du menu
- `quick_signup.html` - Inscription rapide (non utilisée)
- `diagnostic_mobile.html` - Page de diagnostic mobile

### Autres
- `points_style.css` - Ancien fichier de styles
- `app Ménage à deux` - Ancien dossier d'application

---

## 📊 Statistiques

| Catégorie | Nombre |
|-----------|--------|
| 🟡 Pages valides | 41 |
| 🔵 Backups/Essais | 12+ |
| 📁 Total fichiers | 53+ |

---

## 🎨 Configuration Visuelle

Les fichiers sont maintenant marqués dans l'explorateur VS Code :
- **🟡 Pages valides** : Icônes actives (controller, home, lock, etc.)
- **🔵 Backups/Essais** : Icône archive

Configuration dans `.vscode/settings.json` avec Material Icon Theme.

---

## 🔄 Routes Principales

Les pages valides correspondent aux routes définies dans `app.py` :

- `/` → welcome.html
- `/home` → home.html / menu.html
- `/login` → login.html
- `/signup` → signup.html
- `/categorie/<cat>` → tasks.html
- `/task_page/<cat>/<id>` → task_page_enhanced.html
- `/rewards` → rewards.html
- `/invite_partner` → invite_partner_new.html
- `/join_house` → join_house.html
- `/profile` → profile.html
- `/manage_players` → manage_players.html
- Et bien d'autres...

---

*Document généré automatiquement le 24 janvier 2026*
*Application: CleanBeat - Gamification des Tâches Ménagères*
