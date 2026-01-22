# 🔍 Guide de Test - Points en Temps Réel

## ✅ Le Serveur est Lancé

Le serveur tourne sur :
- Local : `http://127.0.0.1:8000`
- Réseau : `http://192.168.1.156:8000`

## 🧪 Comment Tester

### Étape 1 : Ouvrir la Console du Navigateur

1. **Sur Chrome/Edge** : Appuyez sur `F12` ou clic droit → "Inspecter"
2. **Sur Safari** : Développement → "Afficher la console web"
3. Allez dans l'onglet **Console**

### Étape 2 : Connexion

1. Connectez-vous sur `http://192.168.1.156:8000/menu` (sur mobile ou autre appareil)
2. Utilisez un compte de joueur

### Étape 3 : Observer les Logs

Dans la console, vous devriez voir :

```
✅ Polling démarré: toutes les 10 secondes
🚀 Première mise à jour des points...
🔄 Mise à jour points: {players: Array(2), house_health: 75}
👤 Joueur: Anne Points: 25
👤 Joueur: Jean Points: 30
```

### Étape 4 : Tester la Mise à Jour

**Option A : Sur 2 appareils différents**
1. Appareil 1 : Connecté comme Joueur 1
2. Appareil 2 : Connecté comme Joueur 2
3. Joueur 2 valide une tâche
4. Sur Appareil 1, attendez 10 secondes max
5. Regardez la console et l'affichage

**Option B : Sur 2 onglets du même navigateur**
1. Onglet 1 : `http://192.168.1.156:8000/menu` (Joueur 1)
2. Onglet 2 : `http://192.168.1.156:8000/menu` (Joueur 2 - en navigation privée)
3. Validez une tâche dans l'onglet 2
4. Revenez à l'onglet 1 et attendez

## 📊 Ce Que Vous Devriez Voir

### Dans la Console

**Quand tout fonctionne :**
```
🔄 Mise à jour points: {players: [...], house_health: 75}
👤 Joueur: Anne Points: 25
👤 Joueur: Jean Points: 35
📊 Comparaison: Jean ancien: 30 nouveau: 35
✨ Mise à jour points pour Jean : 30 → 35
🎈 Animation +5 pour Jean
```

**Si problème :**
```
⚠️ Élément joueur non trouvé pour: user@email.com
⚠️ Élément points non trouvé dans: <div...>
❌ Erreur mise à jour points: NetworkError
```

### Dans l'Interface

1. **Points qui grossissent** et deviennent verts
2. **Bulle "+X"** qui monte au-dessus du joueur
3. **Barre de progression** qui s'ajuste
4. **Santé de la maison** qui change

## 🐛 Dépannage

### Problème : Aucun log dans la console

**Solution :**
- Rafraîchissez la page (F5)
- Vérifiez que vous êtes bien connecté
- Vérifiez l'URL : doit contenir `/menu` ou `/categorie/...`

### Problème : "Aucun joueur dans la réponse"

**Solution :**
- Vous n'êtes pas connecté → Connectez-vous
- Vous n'êtes pas dans une maison → Rejoignez/créez une maison

### Problème : Points ne changent pas

**Causes possibles :**
1. **Les points n'ont pas changé côté serveur** → Validez une nouvelle tâche
2. **L'élément DOM n'est pas trouvé** → Vérifiez les logs pour voir les warnings
3. **Mauvais attribut data-email** → Vérifiez que le HTML contient `data-email="..."`

### Problème : Erreur réseau

**Solution :**
```bash
# Vérifier que le serveur tourne
curl http://127.0.0.1:8000/ping

# Tester l'API
curl http://127.0.0.1:8000/api/players_points
```

## 🔍 Vérifications Techniques

### 1. Vérifier l'API manuellement

```bash
# Depuis un terminal
curl -s "http://127.0.0.1:8000/api/players_points" | python3 -m json.tool
```

Devrait retourner :
```json
{
  "players": [
    {
      "email": "user@example.com",
      "name": "Joueur",
      "points": 150,
      "daily_points": 25,
      "daily_tasks": 3
    }
  ],
  "house_health": 75
}
```

### 2. Vérifier les éléments HTML

Dans la console du navigateur :
```javascript
// Vérifier les éléments joueurs
document.querySelectorAll('.player-header').forEach(el => {
    console.log('Joueur:', el.getAttribute('data-email'));
});

// Vérifier les éléments de points
document.querySelectorAll('.player-points-header').forEach(el => {
    console.log('Points:', el.textContent);
});
```

### 3. Forcer une mise à jour manuelle

Dans la console :
```javascript
// Appeler la fonction manuellement
updatePlayersPoints();

// ou pour le menu
updatePlayersPointsMenu();
```

## 📝 Logs Attendus (Séquence Normale)

```
[Chargement de la page]
✅ Polling démarré: toutes les 10 secondes

[Après 2 secondes]
🚀 Première mise à jour des points...
🔄 Mise à jour points: {players: Array(2), house_health: 75}
👤 Joueur: Anne Points: 25
📊 Comparaison: Anne ancien: 25 nouveau: 25
👤 Joueur: Jean Points: 30
📊 Comparaison: Jean ancien: 30 nouveau: 30
🏠 Mise à jour santé: 75 % - 2 éléments

[Après 12 secondes - 1er polling]
🔄 Mise à jour points: {players: Array(2), house_health: 75}
👤 Joueur: Anne Points: 25
📊 Comparaison: Anne ancien: 25 nouveau: 25
👤 Joueur: Jean Points: 30
📊 Comparaison: Jean ancien: 30 nouveau: 30

[Jean valide une tâche de 5 points]

[Après 22 secondes - 2e polling]
🔄 Mise à jour points: {players: Array(2), house_health: 80}
👤 Joueur: Anne Points: 25
📊 Comparaison: Anne ancien: 25 nouveau: 25
👤 Joueur: Jean Points: 35
📊 Comparaison: Jean ancien: 30 nouveau: 35
✨ Mise à jour points pour Jean : 30 → 35
🎈 Animation +5 pour Jean
🏠 Mise à jour santé: 80 % - 2 éléments
```

## ✅ Critères de Succès

Le système fonctionne si :
- [x] Les logs apparaissent dans la console
- [x] Le polling se fait toutes les 10 secondes
- [x] Les points changent automatiquement après validation d'une tâche
- [x] L'animation visuelle apparaît
- [x] La santé de la maison se met à jour

## 🎯 Points Clés

1. **Délai de 10 secondes** : Normal, c'est l'intervalle de polling
2. **Logs détaillés** : Permettent de voir exactement ce qui se passe
3. **Console ouverte** : Essentiel pour le débogage
4. **Deux appareils** : Meilleure façon de tester

## 📞 Support

Si ça ne fonctionne toujours pas :
1. Copiez tous les logs de la console
2. Notez ce que vous voyez/ne voyez pas
3. Indiquez sur quelle page vous êtes (`/menu`, `/categorie/...`, etc.)
4. Précisez si vous êtes connecté et dans une maison

---

**Rappel** : Le serveur tourne sur `http://192.168.1.156:8000`
