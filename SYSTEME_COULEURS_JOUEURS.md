# 🎨 Système de Couleurs Personnalisées des Joueurs

## Vue d'ensemble

Chaque joueur de CleanBeat dispose maintenant d'une **couleur personnelle unique** qui l'identifie visuellement dans toute l'application. Cette couleur harmonise l'interface et facilite l'identification rapide des joueurs.

## 🎯 Objectifs

- **Cohérence visuelle** : Une même couleur par joueur dans toutes les pages
- **Identification rapide** : Repérage instantané des joueurs
- **Expérience personnalisée** : Chaque joueur a son identité visuelle
- **Harmonie** : Palette de 12 couleurs soigneusement sélectionnées

## 🌈 Palette de Couleurs

```python
PLAYER_COLOR_PALETTE = [
    '#FF6B9D',  # 1. Rose vif
    '#4ECDC4',  # 2. Turquoise
    '#FFD93D',  # 3. Jaune doré
    '#95E1D3',  # 4. Menthe
    '#C7CEEA',  # 5. Lavande
    '#FFA07A',  # 6. Saumon
    '#98D8C8',  # 7. Vert d'eau
    '#F7B7A3',  # 8. Pêche
    '#A8DADC',  # 9. Bleu ciel
    '#FFB6B9',  # 10. Rose poudré
    '#B4A7D6',  # 11. Violet pastel
    '#FFE66D',  # 12. Jaune pastel
]
```

Ces couleurs ont été choisies pour :
- Être **distinguables** les unes des autres
- Avoir un **bon contraste** avec le fond
- Être **agréables à l'œil** (tons pastel et doux)
- Fonctionner sur **mobile et desktop**

## 📊 Base de Données

### Nouvelle colonne

```sql
ALTER TABLE users ADD COLUMN player_color TEXT;
```

Chaque utilisateur a maintenant un champ `player_color` contenant sa couleur au format hexadécimal (ex: `#FF6B9D`).

### Attribution automatique

Les couleurs sont attribuées automatiquement :
1. **À la création du joueur** : Attribution d'une couleur libre dans la maison
2. **À la première récupération** : Si un joueur n'a pas de couleur, une lui est assignée
3. **Unique par maison** : Deux joueurs de la même maison ont des couleurs différentes (quand possible)

## 🔧 Fonctions Backend

### `assign_player_color(email, house_id=None)`

Attribue une couleur à un joueur.

```python
# Exemple d'utilisation
color = assign_player_color('user@example.com', house_id=1)
# Retourne: '#FF6B9D'
```

**Logique** :
1. Récupère les couleurs déjà utilisées dans la maison
2. Choisit la première couleur disponible
3. Met à jour la base de données
4. Retourne la couleur assignée

### `get_player_color(email)`

Récupère la couleur d'un joueur (ou en assigne une si nécessaire).

```python
# Exemple d'utilisation
color = get_player_color('user@example.com')
# Retourne: '#4ECDC4'
```

### `get_house_players_with_colors(house_id)`

Récupère tous les joueurs d'une maison avec leurs couleurs.

```python
# Exemple d'utilisation
players = get_house_players_with_colors(house_id=1)
# Retourne: [
#   {
#     'email': 'user1@example.com',
#     'name': 'Alice',
#     'color': '#FF6B9D',
#     'points': 150,
#     ...
#   },
#   ...
# ]
```

### `get_house_players_points(house_id)`

La fonction existante a été **mise à jour** pour inclure automatiquement le champ `color`.

## 🎨 Utilisation dans les Templates

### Bordure d'avatar colorée

```html
<div class="player-avatar" style="border: 3px solid {{ player.color }};">
    <img src="{{ player.avatar_url }}" alt="{{ player.name }}">
</div>
```

### Nom du joueur avec couleur

```html
<div class="player-name" style="color: {{ player.color }};">
    {{ player.name }}
</div>
```

### Bouton avec couleur du joueur

```html
<button style="background: {{ player.color }}; border-color: {{ player.color }};">
    ✏️ Modifier
</button>
```

### Barre de progression colorée

```html
<div class="progress-bar" style="background: {{ player.color }}; width: {{ player.points }}%;">
</div>
```

## 📄 Pages Mises à Jour

Les couleurs sont maintenant affichées dans :

### ✅ task_page_enhanced.html
- **Sélecteur de joueurs** : Bordures colorées autour des avatars

### ✅ manage_players.html
- **Cartes de joueurs** : Avatar avec bordure colorée
- **Nom du joueur** : Texte de couleur assortie
- **Bouton modifier** : Fond de couleur assortie

### 🔄 À venir
- **menu.html** : Avatars des joueurs dans le header
- **comments.html** : Messages avec couleur de l'auteur
- **leaderboard** : Classement avec couleurs
- **dashboard** : Statistiques par joueur avec couleurs

## 🚀 Script d'Attribution Initiale

Le script `assign_player_colors.py` a été créé pour attribuer des couleurs à tous les joueurs existants :

```bash
python3 assign_player_colors.py
```

Ce script :
1. Vérifie que la colonne `player_color` existe
2. Parcourt toutes les maisons
3. Attribue des couleurs uniques aux joueurs de chaque maison
4. Affiche un rapport détaillé

**Résultat** : 169 joueurs mis à jour dans 150 maisons

## 🎯 Bonnes Pratiques

### 1. Toujours vérifier la présence de la couleur

```python
color = player.get('color') or '#FF6B9D'  # Couleur par défaut
```

### 2. Utiliser les fonctions helper

Au lieu de requêter directement la base de données, utiliser :
- `get_player_color(email)` pour un joueur
- `get_house_players_with_colors(house_id)` pour une maison

### 3. Ne pas dupliquer les couleurs

Le système évite automatiquement les doublons dans une même maison (jusqu'à 12 joueurs).

### 4. Fallback gracieux

Si la couleur n'est pas disponible dans le template :
```html
style="border-color: {{ player.color or '#FF6B9D' }};"
```

## 🔄 Maintenance

### Ajouter des couleurs à la palette

Éditer `PLAYER_COLOR_PALETTE` dans `app.py` et relancer l'application.

### Réattribuer les couleurs d'une maison

```python
conn = sqlite3.connect('users.db')
c = conn.cursor()
c.execute("UPDATE users SET player_color = NULL WHERE house_id = ?", (house_id,))
conn.commit()
conn.close()
```

Puis recharger la page - les couleurs seront automatiquement réassignées.

### Changer la couleur d'un joueur manuellement

```sql
UPDATE users SET player_color = '#4ECDC4' WHERE email = 'user@example.com';
```

## 📈 Évolution Future

### Idées d'amélioration :

1. **Choix de couleur par l'utilisateur**
   - Interface de sélection dans le profil
   - Palette personnalisée par maison

2. **Thèmes de couleurs**
   - Mode sombre avec couleurs adaptées
   - Palettes saisonnières

3. **Accessibilité**
   - Vérification du contraste WCAG
   - Mode daltonien

4. **Analytics**
   - Statistiques sur les couleurs les plus populaires
   - Préférences par région/démographie

## 🐛 Dépannage

### Les couleurs ne s'affichent pas

1. Vérifier que la colonne existe :
   ```sql
   PRAGMA table_info(users);
   ```

2. Vérifier qu'une couleur est assignée :
   ```sql
   SELECT email, player_color FROM users WHERE email = 'user@example.com';
   ```

3. Relancer le script d'attribution :
   ```bash
   python3 assign_player_colors.py
   ```

### Couleurs identiques pour plusieurs joueurs

C'est normal si la maison a plus de 12 joueurs. Les couleurs se répètent après les 12 premières.

### Couleur par défaut partout

Vérifier que `get_house_players_points()` retourne bien le champ `color`.

## ✅ Checklist de Déploiement

- [x] Colonne `player_color` ajoutée à la table `users`
- [x] Fonctions d'attribution créées
- [x] Script d'attribution initiale exécuté
- [x] `get_house_players_points()` mis à jour
- [x] Template `task_page_enhanced.html` mis à jour
- [x] Template `manage_players.html` mis à jour
- [x] Route `manage_players` mise à jour
- [ ] Template `menu.html` à mettre à jour
- [ ] Template `comments.html` à mettre à jour
- [ ] Tests d'intégration sur mobile
- [ ] Tests d'accessibilité (contraste)

## 📝 Conclusion

Le système de couleurs personnalisées améliore significativement l'expérience utilisateur en :
- Facilitant l'identification des joueurs
- Créant une identité visuelle unique
- Harmonisant l'interface
- Rendant l'application plus ludique et engageante

Le système est **automatique**, **robuste** et **facilement extensible** pour les futures fonctionnalités.
