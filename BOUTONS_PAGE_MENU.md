# 🎯 Boutons Cliquables - Page Menu

## 📋 Vue d'ensemble
La page menu contient plusieurs éléments interactifs avec des effets visuels et sonores intégrés.

---

## 🍔 1. BOUTON BURGER (Menu Principal)

**Élément HTML:**
```html
<button class="burger-menu" id="burgerBtn" aria-label="Menu">
    <span></span>
    <span></span>
    <span></span>
</button>
```

**Effet visuel:**
- Dégradé orange/peach avec bordure blanche semi-transparente
- Dimensionné à 40px × 40px
- 3 barres horizontales
- Position: coin supérieur gauche du header

**Effet au clic:**
- ✨ Animation halo lumineux (clickHalo 0.8s)
- 🎵 Son de clic léger (800Hz → 400Hz, 100ms)
- 📱 Activation du menu overlay burger
- 🔄 Affichage de la navigation latérale avec slide de gauche

**Comportement interactif:**
- `Clic` → Ouvre le menu en overlay (translateX 0)
- `État actif` → Scale 0.95

---

## 🗂️ 2. MENU BURGER OVERLAY

**Élément HTML:**
```html
<div class="burger-overlay" id="burgerOverlay">
    <div class="burger-nav">
        <!-- Contenu du menu -->
    </div>
</div>
```

**Effets:**
- Fond semi-transparent (rgba 0.85) avec blur backdrop
- Apparition progressive (opacity 0→1)
- Menu latéral avec gradient teal light → teal dark

### Items du menu burger:

| Icône | Texte | Lien |
|-------|-------|------|
| 🏠 | Maison | `/menu` |
| 🎁 | Récompenses | `/rewards` |
| 📊 | Stats | `/sats` |
| 💬 | Messages | `/comments` |
| 👤 | Profil | `/create_profile` |

**Effets par item:**
- Background blanc semi-transparent + blur
- Bordure blanche avec opacité 0.2
- État actif: Gradient doré avec ombre orange
- Survol: TranslateX(8px)
- 🎵 Son de clic à chaque navigation

---

## ❌ 3. BOUTON FERMER (X Burger)

**Élément HTML:**
```html
<button class="burger-close" id="burgerClose" aria-label="Fermer le menu">&times;</button>
```

**Position:** Haut droit du menu burger

**Effet au clic:**
- Fermeture du menu overlay
- Suppression du blur backdrop
- Opacity fade out (0.3s)
- 🎵 Son de clic

**Raccourci clavier:** Touche `Escape` ferme aussi le menu

---

## 🏠 4. PIÈCES DE LA MAISON (SVG Clickable Rooms)

**Sélecteur CSS:** `.room-group`

**Données:** 
```html
<g class="room-group" data-href="/task_hall">
```

**Effets au clic:**

1. **Animation Halo Lumineux:**
   - Classe `clicking` ajoutée
   - Animation: Radius ↑, opacity ↑↓, scale ↑
   - Durée: 800ms (clickHalo)
   - Couleur: White glow

2. **Effet Sonore Mobile:**
   - Fréquence: 600Hz → 1000Hz (200ms)
   - Volume: 0.4 (plus fort sur mobile)
   - Type: Sine wave

3. **Comportement:**
   - Délai de 250ms avant navigation
   - Permet de voir l'effet visuel
   - Prévient les doubles-clics

4. **Accessibilité:**
   - Clavier: `Enter` ou `Espace` pour activer
   - Touch: Durée < 500ms pour valider

---

## 🎯 5. BOUTON TOGGLE DASHBOARD

**Élément HTML:**
```html
<button class="dashboard-toggle">
    <div class="dashboard-toggle-handle"></div>
    <div class="dashboard-toggle-text"></div>
</button>
```

**Position:** Haut du dashboard flottant (bas de l'écran)

**Effets:**
- Barre de handle: 48px × 5px (color teal-light)
- État actif: Width ↑ (48→64px), color gold
- 🎵 Son de clic

**Comportement:**
- Minimise/maximise le dashboard (translateY)
- Texte change: "▼ Classement" ↔ "▲ Classement"
- Smooth transition: 0.4s cubic-bezier

---

## 🎵 6. AVATARS (Cliquables)

**Éléments:**
- `.avatar-square` - Carré principal
- `.avatar-col` - Colonne du joueur
- `.current-player-avatar-wrapper` - Wrapper du joueur actuel

**Effets au clic:**
- 🎵 Son de clic
- Animation possible si paramètre `?ts=` présent (célébration)

**Animation Célébration (après validation de tâche):**
- Classe: `avatar-celebrating`
- Couleur du halo: Dépend du joueur (bleu, violet, rouge, etc.)
- Particules/confettis (si `createWinnerEffects` activé)

---

## 🔊 7. SONS GÉNÉRAUX

### Types de sons:

**A. Son de Clic (Popup):**
- Fréquence: 800Hz → 400Hz
- Durée: 100ms
- Volume: 0.15
- Éléments: Buttons, burger, navs

**B. Son de Succès (Ding Positif):**
- Notes: Do (523Hz) → Mi (659Hz) → Sol (784Hz)
- Durée: 300ms
- Volume: 0.2

**C. Son de Navigation (Woosh):**
- Fréquence: 300Hz → 600Hz
- Durée: 80ms
- Volume: 0.1
- Éléments: Pièces SVG, rooms

**D. Son de Progression:**
- Généré dynamiquement selon la hauteur de la barre (% de points)
- Multi-tones selon la valeur

---

## ⚡ 8. FLASH MESSAGE (Notification Temporaire)

**Élément HTML:**
```html
<div id="flashOverlay" class="flash-overlay">
    <div class="flash-popup">
        <!-- Contenu -->
    </div>
</div>
```

**Bouton de fermeture:**
```html
<button class="flash-close" onclick="closeFlashMessage()">&times;</button>
```

**Effets:**
- Apparition avec scale (0.8→1.0)
- Fond avec blur backdrop
- Fermeture: Opacity fade (0.3s)

**Fermeture par:**
- Clic sur le bouton `×`
- Clic sur l'overlay
- Touche `Escape`
- **Auto-fermeture:** 5 secondes

---

## 📊 9. BARRES DE PROGRESSION (vbar)

**Classe CSS:** `.vbar-fill`

**Effets au chargement:**
- Animation height: 0 → valeur finale (0.6s ease)
- 🎵 Son de progression joué (décalé par barre)
- Ombre temporaire: Box-shadow gold glow (300ms)

**Effectif minimum visible:**
- Si points > 0 mais height < 4%, force 4% de hauteur minimale
- Évite les barres invisibles

---

## 🎨 RÉCAPITULATIF DES EFFETS

| Élément | Effet Visuel | Effet Sonore | Action |
|---------|-------------|-------------|--------|
| Burger menu | Scale 0.95 | Pop click | Ouvre overlay |
| Menu items | TranslateX(8px) | Click | Navigation |
| Bouton X | Scale 0.9 | Click | Ferme menu |
| Pièces SVG | Halo lumineux | Woosh nav | Navigation room |
| Avatar clic | Pulse/glow | Click | Possible action |
| Avatar victory | Celebrating animation | Success ding | Après tâche |
| Dashboard toggle | Width ↑ | Click | Min/max dashboard |
| Flash message | Fade in/out | Aucun | Notification |
| vbar remplissage | Height animation | Progress tone | Au chargement |

---

## 🔧 CONTRÔLES CLAVIER

| Touche | Action |
|--------|--------|
| `Enter` | Active une pièce SVG |
| `Space` | Active une pièce SVG |
| `Escape` | Ferme menu burger ou notification |

---

## 📱 RESPONSIVE

- **Mobile (< 400px):** Ajustements de taille et padding
- **Touch vs Mouse:** Détection automatique
- **Audio Mobile:** Context.resume() si suspendu (iOS)

---

## 🎯 NAVIGATION APRÈS TÂCHE

**URL avec paramètres:**
```
/menu?pts=100&ts=1234567890
```

**Effets:**
- ✨ Animation de célébration de l'avatar
- 🎵 Son de victoire
- 📢 Notification toast en haut-droit (4s)
- 🔄 Suppression des paramètres après animation

