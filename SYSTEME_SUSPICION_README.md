# 🔍 Système de Suspicion — Documentation

## ✅ IMPLÉMENTATION TERMINÉE

Le système de suspicion avec preuves photo a été entièrement implémenté dans l'application CleanBeat/Dust !

---

## 📋 Fonctionnalités implémentées

### 1. **Base de données**
- ✅ Table `suspicions` créée avec tous les champs nécessaires
- ✅ Statuts : pending, awaiting_validation, validated, rejected
- ✅ Stockage du chemin vers les photos de preuve

### 2. **Routes API Backend**
- ✅ `/api/emit_suspicion` - Émettre une suspicion sur une tâche
- ✅ `/api/upload_proof` - Upload d'une photo de preuve
- ✅ `/api/validate_proof` - Valider ou rejeter une preuve
- ✅ `/api/my_suspicions` - Récupérer mes suspicions (émises + contre moi)
- ✅ `/uploads/<path>` - Servir les photos uploadées

### 3. **Interface utilisateur (gameplay.html)**
- ✅ Section dédiée "🔍 Suspicions — Validation de tâches"
- ✅ Liste des suspicions en cours (émises et reçues)
- ✅ Bouton "Émettre une suspicion"
- ✅ Popup de sélection de tâche à contester
- ✅ Popup d'upload de photo (pour le soupçonné)
- ✅ Popup de validation de preuve avec visualisation photo (pour le soupçonneux)
- ✅ Indicateurs visuels (⏳ En attente, 📸 Preuve reçue, ✅ Validée, ❌ Rejetée)

### 4. **Système de points**
Les règles de points sont EXACTEMENT celles demandées :

#### **Si PREUVE VALIDÉE (photo convaincante)** :
- ✅ Soupçonneux **perd 10 points** (il avait tort)
- ✅ Soupçonné **gagne les points de sa tâche** (il était innocent)

#### **Si PREUVE REJETÉE (photo non convaincante)** :
- ✅ Soupçonneux **ne perd rien** (il avait raison)
- ✅ Soupçonné **perd 20 points** (pénalité lourde pour tricherie)

---

## 🎮 Comment tester le système

### Étape 1 : Accéder à la page Gameplay
1. Connectez-vous à l'application
2. Cliquez sur le bouton 🎮 (qui pulse) en haut à droite
3. Vous arrivez sur la page Gameplay

### Étape 2 : Émettre une suspicion
1. Scrollez jusqu'à la section "🔍 Suspicions"
2. Cliquez sur "Émettre une suspicion"
3. Choisissez une tâche récente d'un autre joueur
4. Confirmez la suspicion (risque : 10 pts)

### Étape 3 : Le joueur soupçonné fournit une preuve
1. Le joueur soupçonné voit une alerte rouge "⚠️ [Nom] te soupçonne !"
2. Il clique sur "📸 Envoyer une preuve"
3. Il sélectionne ou prend une photo
4. Il envoie la preuve

### Étape 4 : Validation de la preuve
1. Le soupçonneux voit "📸 Preuve reçue - À valider"
2. Il clique sur "⚖️ Valider ou rejeter"
3. La photo s'affiche
4. Il choisit :
   - ✅ **Valider** → Il perd 10 pts, l'autre gagne les points de la tâche
   - ❌ **Rejeter** → L'autre perd 20 pts, lui ne perd rien

---

## 🗂️ Fichiers modifiés

### Backend
- **app.py** :
  - Ligne ~2987 : Table `suspicions` créée
  - Lignes 10307-10530 : 4 nouvelles routes API
  - Ligne 10818 : Route pour servir les uploads

### Frontend
- **templates/gameplay.html** :
  - Section suspicions après malus/bonus
  - 3 popups (picker tâches, upload photo, validation)
  - JavaScript complet pour la gestion des suspicions

### Fichiers système
- **uploads/proofs/** : Dossier créé pour stocker les photos

---

## 🔮 Futures améliorations possibles

### Non implémenté (optionnel) :
- ⏰ **Notifications** : Alertes push quand on est soupçonné
- 📊 **Statistiques** : Nombre de suspicions gagnées/perdues
- ⏱️ **Délai limite** : Timer pour répondre à une suspicion
- 👁️ **Historique** : Voir toutes les suspicions passées

Ces fonctionnalités peuvent être ajoutées plus tard si nécessaire.

---

## 🎯 Prochaines étapes

Le système est **100% opérationnel** ! Vous pouvez :

1. ✅ **Tester** avec plusieurs comptes
2. ✅ **Vérifier** les calculs de points
3. 💡 **Demander des ajustements** si nécessaire

**Le gameplay est maintenant beaucoup plus rigolo et stratégique !** 🎮🔥
