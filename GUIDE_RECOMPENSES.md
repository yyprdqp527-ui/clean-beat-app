# 🎁 Page Récompenses - Guide Complet

## 📋 Vue d'ensemble

La page **Récompenses** est une fonctionnalité gamifiée qui permet au gagnant de la semaine de débloquer des cadeaux surprise dans une grille de 40 cases.

## ✨ Fonctionnalités

### 🎯 Principe
- **40 cases numérotées** disposées en grille
- **Seul le gagnant de la semaine** peut cliquer sur une case
- Chaque case contient une **récompense surprise**
- Les cases ouvertes restent visibles pour tous

### 👑 Gagnant de la semaine
Le gagnant est déterminé automatiquement :
- Calcul basé sur les points accumulés **depuis le lundi**
- Le joueur avec le **plus de points** dans la maison devient le gagnant
- Mise à jour en temps réel

### 🎨 Design - Glassmorphism & Relief

#### Effet Glassmorphism
- Fond transparent avec `backdrop-filter: blur(15px)`
- Bordures semi-transparentes `rgba(255, 255, 255, 0.3)`
- Ombres douces et multiples pour la profondeur

#### Effet Relief au Clic
```css
/* Au survol - Case se soulève */
transform: translateY(-3px);

/* Au clic - Case s'enfonce */
transform: translateY(2px) scale(0.98);
box-shadow: inset 0 2px 5px rgba(0, 0, 0, 0.2);
```

#### Animation d'Ouverture
- Rotation 3D sur l'axe Y (360°)
- Scale de 1.1 au milieu de l'animation
- Durée : 0.5s avec ease-out
- Gradient rose/rouge au déverrouillage

### 🎁 Récompenses Disponibles

40 récompenses fun et variées :
- 🎬 Choisis le film ce soir
- 🍕 Pizza offerte
- ☕ Café au lit demain
- 🎮 1h de jeu vidéo
- 🛋️ Canapé pour la soirée
- 🍰 Dessert de ton choix
- 🎵 Tu choisis la musique
- 🌟 Dispense de vaisselle
- ... et 32 autres surprises !

## 🗄️ Base de Données

### Table `reward_boxes`
```sql
CREATE TABLE reward_boxes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    house_id INTEGER NOT NULL,
    box_number INTEGER NOT NULL,
    reward_text TEXT NOT NULL,
    opened_by TEXT NOT NULL,
    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(house_id, box_number),
    FOREIGN KEY (house_id) REFERENCES houses(id),
    FOREIGN KEY (opened_by) REFERENCES users(email)
)
```

## 🔌 API Endpoints

### GET `/rewards`
Affiche la page des récompenses
- Vérifie que l'utilisateur a une maison
- Calcule le gagnant de la semaine
- Récupère les cases déjà ouvertes
- Rendu du template avec contexte

**Variables du template :**
- `house_code` : Code de la maison
- `is_winner` : True si l'utilisateur est le gagnant
- `winner_name` : Nom du gagnant
- `user_name` : Nom de l'utilisateur connecté
- `opened_boxes` : Dict des cases ouvertes `{numéro: {reward, opened_by}}`

### POST `/open_reward_box`
Ouvre une case et révèle la récompense

**Request :**
```json
{
  "box_number": 15
}
```

**Response (succès) :**
```json
{
  "success": true,
  "reward": "🍕 Pizza offerte"
}
```

**Response (erreur) :**
```json
{
  "success": false,
  "message": "Seul le gagnant de la semaine peut ouvrir une case"
}
```

**Validations :**
- ✅ Utilisateur connecté
- ✅ Numéro de case valide (1-40)
- ✅ Utilisateur a une maison
- ✅ Utilisateur est le gagnant de la semaine
- ✅ Case pas encore ouverte

## 📱 Responsive Design

### Desktop (> 480px)
- Grille avec `minmax(70px, 1fr)`
- Gap de 12px entre les cases
- Numéros en 18px
- Icônes cadeaux 24px

### Mobile (≤ 480px)
- Grille avec `minmax(60px, 1fr)`
- Gap réduit à 10px
- Numéros en 16px
- Icônes cadeaux 20px
- Bouton retour plus petit (50px)

## 🎯 États des Cases

### 1. Non ouverte (joueur normal)
```css
.reward-box.disabled {
    opacity: 0.6;
    cursor: not-allowed;
    background: rgba(255, 255, 255, 0.08);
}
```

### 2. Non ouverte (gagnant)
- Effet hover avec élévation
- Cursor pointer
- Glassmorphism actif
- Animation au clic

### 3. Ouverte
```css
.reward-box.opened {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    animation: openBox 0.5s ease-out;
}
```

## 🔔 Notifications Toast

Système de notifications temporaires :
- **Succès** : Fond blanc, texte noir
- **Erreur** : Gradient rouge, texte blanc
- Durée : 3 secondes
- Position : Top center
- Animation : Slide down

## 🎮 Interactions JavaScript

### Fonction `openBox(boxNumber)`
1. Vérifie l'état de la case (ouverte/désactivée)
2. Appel API POST `/open_reward_box`
3. Animation d'ouverture si succès
4. Affichage de la récompense après 250ms
5. Toast de confirmation

### Fonction `showToast(message, isError)`
1. Mise à jour du contenu
2. Ajout de la classe `show`
3. Ajout de `error` si nécessaire
4. Suppression automatique après 3s

## 🎨 Éléments Visuels

### Bannière Gagnant (Gagnant actuel)
```css
background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
animation: pulse 2s ease-in-out infinite;
```
- Effet pulse constant
- Icônes couronne et étoiles
- Message personnalisé

### Bannière Gagnant (Autre joueur)
```css
background: rgba(255, 255, 255, 0.2);
animation: none;
```
- Pas d'animation
- Affiche le nom du gagnant
- Style neutre

### Info Box
- Glassmorphism
- Bordure semi-transparente
- Texte explicatif centré
- Icône 💡

## 🚀 Accès à la Page

Depuis le menu burger :
1. Cliquer sur le bouton ☰ (menu)
2. Sélectionner "🎁 Récompenses"
3. Redirection vers `/rewards`

## 🔄 Réinitialisation Hebdomadaire

Le gagnant change **automatiquement** :
- Calcul basé sur la semaine en cours
- Début de semaine : Lundi 00:00
- Nouveau décompte chaque semaine
- Les cases ouvertes restent ouvertes (pas de reset)

## 💡 Tips Développement

### Ajouter de nouvelles récompenses
Modifier la liste `rewards` dans `/open_reward_box` (app.py ligne ~3010)

### Changer le nombre de cases
1. Modifier la boucle `{% for i in range(1, 41) %}` → `range(1, N+1)`
2. Adapter la validation `box_number > 40` → `> N`

### Personnaliser l'animation
Modifier les keyframes `@keyframes openBox` dans le CSS

## 🐛 Dépannage

### Cases ne répondent pas
- Vérifier que l'utilisateur est connecté
- Vérifier qu'il a une maison
- Vérifier qu'il est le gagnant de la semaine

### Animation saccadée
- Ajouter `will-change: transform` sur `.reward-box`
- Réduire le `backdrop-filter` blur

### API ne répond pas
- Vérifier la connexion à la BDD
- Vérifier les logs Flask
- Tester avec `curl -X POST http://localhost:8000/open_reward_box`

## 📊 Métriques

- **40 cases** au total
- **1 case par victoire** de semaine
- **40 récompenses uniques** aléatoires
- **Temps moyen d'ouverture** : ~1 seconde (animation incluse)

---

**Créé le** : 8 janvier 2026  
**Version** : 1.0  
**Design** : Glassmorphism avec effets 3D
