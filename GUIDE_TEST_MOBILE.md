# 📱 Guide de Test - Sélecteur de Joueur Mobile

## 🎯 Objectif
Vérifier que les points sont bien attribués au bon joueur quand on valide une tâche depuis un téléphone.

---

## 📋 Scénario de Test

### Étape 1 : Connexion
```
✅ Connectez-vous avec votre compte principal
   Exemple : pat@hotmail.com ou votre email
```

### Étape 2 : Navigation
```
📱 Sur la page Menu (/menu)
   → Vous voyez tous les joueurs de votre maison en haut
   → pat (15 pts) + Emma (0 pts)
```

### Étape 3 : Choisir une Tâche
```
🏠 Tapez sur une catégorie (ex: "Chambre")
   → Liste des tâches apparaît
   
✨ Tapez sur une tâche (ex: "Faire le lit")
   → Page de la tâche s'ouvre
```

### Étape 4 : **SÉLECTION DU JOUEUR** (NOUVEAU !)
```
👤 ZONE : "Qui a fait cette tâche ?"

   ┌─────────────────────────────────────────┐
   │                                         │
   │   ╔═══╗  BORDURE GRISE    ╔═══╗       │
   │   ║ 😊 ║  ← Pas sélectionné║ 👶 ║       │
   │   ╚═══╝  "pat"            ╚═══╝       │
   │                           "Emma"       │
   │   ↑ Par défaut = Vous                 │
   └─────────────────────────────────────────┘

TESTEZ :
1. Tapez sur "Emma" (ou votre enfant)
   
   ┌─────────────────────────────────────────┐
   │                                         │
   │   ╔═══╗  BORDURE GRISE    ╔═══╗       │
   │   ║ 😊 ║  "pat"            ║ 👶 ║       │
   │   ╚═══╝                   ╚═══╝       │
   │                           "Emma"       │
   │                            ↑           │
   │                     BORDURE VERTE ✅   │
   │                     (SÉLECTIONNÉ)      │
   └─────────────────────────────────────────┘

2. Vérifiez :
   ✅ La bordure devient VERTE
   ✅ Légère ombre verte autour
   ✅ Légèrement plus grand (zoom)
```

### Étape 5 : Validation
```
🎯 Tapez sur le bouton noir :
   "✅ Faire le lit, c'est fait !"

   → Feu d'artifice 🎆
   → Son de célébration 🎵
   → Redirection vers /menu
```

### Étape 6 : VÉRIFICATION (IMPORTANT)
```
🏠 Sur la page Menu :

   AVANT :                  APRÈS :
   ┌──────────┐            ┌──────────┐
   │ pat      │            │ pat      │
   │ 😊       │            │ 😊       │
   │ 15 pts   │  →→→→→→   │ 15 pts   │
   └──────────┘            └──────────┘
   
   ┌──────────┐            ┌──────────┐
   │ Emma     │            │ Emma     │
   │ 👶       │            │ 👶       │
   │ 0 pts    │  →→→→→→   │ 5 pts ✅ │ ← NOUVEAU !
   └──────────┘            └──────────┘

✅ Les points d'Emma ont AUGMENTÉ
✅ Les points de pat n'ont PAS changé
```

---

## 🐛 Que Faire Si Ça Ne Marche Pas ?

### Problème 1 : La bordure ne change pas
```
❌ La bordure reste grise quand je tape sur un joueur

SOLUTIONS :
1. Vider le cache Safari :
   Réglages > Safari > Effacer historique et données

2. Fermer Safari complètement :
   Double-clic bouton Home > Balayer vers le haut

3. Recharger la page :
   Tirer vers le bas depuis le haut de la page

4. Essayer en mode privé :
   Icône Safari > + > Navigation privée
```

### Problème 2 : Les points vont au mauvais joueur
```
❌ J'ai sélectionné Emma mais les points sont allés à pat

VÉRIFIEZ :
1. La bordure était-elle bien VERTE sur Emma ?
2. Avez-vous bien tapé sur Emma (pas à côté) ?

SOLUTION :
1. Réessayez en tapant bien au centre du bouton
2. Attendez de voir la bordure verte AVANT de valider
```

### Problème 3 : Aucun joueur n'apparaît
```
❌ Je ne vois pas "Qui a fait cette tâche ?"

RAISON :
Vous êtes seul dans votre maison

SOLUTION :
Invitez des membres depuis /menu > "Inviter un partenaire"
```

---

## 📊 Vérification Technique

### Dans la console Safari (Mac) :
```javascript
// Connectez votre iPhone au Mac
// Safari > Développement > [iPhone] > [Page]

// Vous devriez voir ces logs :
🎮 [INIT] Initialisation du sélecteur de joueur...
👥 2 joueur(s) trouvé(s)
⭐ Sélection par défaut: pat@hotmail.com
✅ Sélection: test_child_1767610274@cleanbeat.local
📧 Valeur du champ: test_child_1767610274@cleanbeat.local
🚀 Soumission - Joueur sélectionné: test_child_1767610274@cleanbeat.local
```

---

## ✅ Checklist Complète

- [ ] Je suis connecté(e)
- [ ] Je vois tous les joueurs en haut de /menu
- [ ] J'ai ouvert une tâche
- [ ] Je vois "Qui a fait cette tâche ?"
- [ ] Je vois tous les joueurs avec leurs avatars
- [ ] Par défaut, MON avatar a une bordure verte
- [ ] Quand je tape sur un autre joueur, LA BORDURE SE DÉPLACE
- [ ] Je valide la tâche
- [ ] Retour à /menu : LES POINTS SONT ATTRIBUÉS AU BON JOUEUR

---

## 🎉 Résultat Attendu

```
AVANT LA TÂCHE :
┌─────────────────────────┐
│ 🏠 Ma Maison            │
├─────────────────────────┤
│ pat:  15 pts aujourdhui │
│ Emma: 0 pts aujourdhui  │
└─────────────────────────┘

JE FAIS UNE TÂCHE POUR EMMA (5 POINTS)

APRÈS LA TÂCHE :
┌─────────────────────────┐
│ 🏠 Ma Maison            │
├─────────────────────────┤
│ pat:  15 pts aujourdhui │
│ Emma: 5 pts aujourdhui ✨│ ← AUGMENTÉ !
└─────────────────────────┘
```

---

## 💡 Cas d'Usage

### Cas 1 : Valider pour moi-même
```
1. Ouvrir une tâche
2. MON nom est déjà sélectionné (bordure verte)
3. Valider directement
4. Points attribués à MOI
```

### Cas 2 : Valider pour mon enfant
```
1. Ouvrir une tâche
2. Taper sur le nom de MON ENFANT
3. Vérifier bordure verte
4. Valider
5. Points attribués à MON ENFANT
```

### Cas 3 : Plusieurs enfants
```
1. Ouvrir une tâche
2. Taper sur ENFANT 1
3. Valider → Points à ENFANT 1

4. Ouvrir une autre tâche
5. Taper sur ENFANT 2
6. Valider → Points à ENFANT 2
```

---

**Date** : 5 janvier 2026  
**Status** : ✅ Prêt pour le test  
**Serveur** : http://127.0.0.1:5000
