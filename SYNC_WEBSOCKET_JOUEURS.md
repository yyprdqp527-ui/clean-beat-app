# 🔌 Synchronisation WebSocket des joueurs

## Résumé des modifications

L'ajout de joueurs (enfants et partenaires) est maintenant synchronisé en temps réel sur tous les écrans connectés via WebSocket, comme pour les points.

## 🎯 Événement WebSocket : `players_list_update`

### Quand est-il émis ?

1. **Ajout d'un enfant** (`/add_child`) - action: `child_added`
2. **Joueur rejoignant une maison** (connexion) - action: `player_joined`  
3. **Nouvel utilisateur s'inscrivant** (inscription) - action: `player_registered`

### Données envoyées

```javascript
{
  players: [
    {
      email: string,
      name: string,
      avatar_url: string,
      points: number,
      color: string
    },
    ...
  ],
  new_player: string,  // Nom du nouveau joueur
  action: 'child_added' | 'player_joined' | 'player_registered'
}
```

## 📋 Pages mises à jour

### 1. **manage_players.html**
- ✅ Écoute `players_list_update`
- ✅ Recharge la page automatiquement quand un nouveau joueur est ajouté
- 🎯 Permet de voir instantanément les nouveaux joueurs

### 2. **menu.html**
- ✅ Écoute `players_list_update`
- ✅ Appelle `updatePlayersPointsMenu()` pour rafraîchir l'affichage
- 🎯 Les avatars des nouveaux joueurs apparaissent dans le header

### 3. **add_players.html**
- ✅ Écoute `players_list_update`
- ✅ Redirige vers `/manage_players` quand un joueur est ajouté
- 🎯 Permet une synchronisation fluide entre les écrans

## 🚀 Comment ça fonctionne ?

1. **Utilisateur A** ajoute un enfant via `/add_children`
2. Le serveur crée l'enfant dans la base de données
3. Le serveur émet l'événement WebSocket `players_list_update` à tous les clients de la room `house_{house_id}`
4. **Utilisateur B** (sur un autre appareil) reçoit l'événement
5. Sa page se met automatiquement à jour pour afficher le nouveau joueur

## 🧪 Test

1. Ouvrir la page `/menu` sur deux appareils différents
2. Sur l'appareil 1 : Aller dans "Gérer les joueurs" → "Ajouter un enfant"
3. Ajouter un enfant avec un nom et un avatar
4. Sur l'appareil 2 : Observer l'avatar du nouvel enfant apparaître automatiquement dans le header

## 📝 Notes techniques

- Les enfants ont des emails internes au format `child_{house_id}_{timestamp}@cleanbeat.internal`
- Ils sont exclus des requêtes WebSocket qui filtrent par `email NOT LIKE '%@cleanbeat.internal'` sauf dans add_child où on les inclut volontairement
- Les avatars sont correctement récupérés avec leur URL DiceBear complète
